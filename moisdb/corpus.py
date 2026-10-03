"""첨부 텍스트 추출 → 분석용 최종 텍스트(doc_text) 구성 → 전문검색 색인.

보도자료는 같은 내용이 '게시판 본문(HTML)'과 '첨부 HWP/PDF'에 중복으로 들어 있는 경우가 많다.
둘 다 넣으면 키워드 빈도가 두 배로 부풀므로, 문서마다 하나의 텍스트만 고른다.
  1) 같은 이름의 첨부가 형식만 다르면(.hwpx/.hwp/.pdf) 하나만 남긴다 (hwpx > hwp > docx > pdf)
  2) 첨부가 본문 내용을 대부분 포함하면 첨부만, 본문이 '첨부 참조' 수준이면 첨부만,
     그 외(본문과 첨부가 서로 다른 내용)면 둘을 이어 붙인다.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

from . import db
from .extract import TEXT_TYPES, extract_text

log = logging.getLogger(__name__)

TYPE_PRIORITY = {t: i for i, t in enumerate(TEXT_TYPES)}  # hwpx > hwp > docx > pdf

# 보도자료 서식에서 반복되는 머리말·꼬리말 줄 (분석 노이즈)
BOILERPLATE_LINE_RES = [
    re.compile(p)
    for p in (
        r"^보\s*도\s*자\s*료$",
        r"^보\s*도\s*시\s*점",
        r"^배\s*포(\s*일\s*시|\s*시\s*점)?\s*[:：]?",
        r"^\(?\s*(온\s*라\s*인|지\s*면|방\s*송)",
        r"즉시\s*보도",
        r"^\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.?\s*\(.\)\s*(\d{1,2}:\d{2})?\s*$",  # '2026. 10. 2.(금) 15:00'
        r"^[*※\s]*(담\s*당\s*부\s*서|책\s*임\s*자|담\s*당\s*자)",
        r"보도자료와 관련하여 보다 자세한 내용이나 취재를 원하시면",
        r"^(과|팀|국|실|단|센터)\s*장\s*\S{2,4}\s*$",
        r"^(사무관|주무관|서기관|연구관|연구사|행정관)\s*\S{2,4}\s*$",
        r"^[<〈(]?\s*끝\s*[>〉)]?\.?$",
        r"^[※]?\s*(사진|붙임|참고)\s*\d*\s*[:：]?\s*$",
        r"^\d+\s*/\s*\d+$",  # PDF 쪽번호 '3 / 10'
        r"^-\s*\d+\s*-$",  # 쪽번호 '- 3 -'
    )
]
# 본문 끝의 연락처 표('담당 부서 / 책임자 과장 홍길동 (044-…) / 담당자 …')는 칸마다 한 줄이 되어
# 부서명·직급·이름이 짧은 줄로 이어진다. '담당 부서'에서 시작해 '붙임' 또는 긴 문장이 나올 때까지 버린다.
CONTACT_START_RE = re.compile(r"^담\s*당\s*부\s*서")
APPENDIX_RE = re.compile(r"^(붙\s*임|참\s*고)(\s*\d+)?(\s|[.:：]|$)")
CONTACT_LINE_MAX = 40
PHONE_RE = re.compile(r"\(?0\d{1,2}\)?[-.\s]?\d{3,4}[-.\s]\d{4}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
URL_RE = re.compile(r"https?://\S+|www\.\S+")


def clean_text(text: str) -> str:
    lines = []
    in_contact = False
    for line in (text or "").splitlines():
        line = line.strip()
        if CONTACT_START_RE.match(line):
            in_contact = True
            continue
        if in_contact:
            if APPENDIX_RE.match(line) or len(line) > CONTACT_LINE_MAX:
                in_contact = False
            else:
                continue
        if not line or any(r.search(line) for r in BOILERPLATE_LINE_RES):
            continue
        line = URL_RE.sub(" ", EMAIL_RE.sub(" ", PHONE_RE.sub(" ", line)))
        line = re.sub(r"\(\s*\)", " ", line)  # 전화번호를 지우고 남은 빈 괄호
        line = re.sub(r"\s+", " ", line).strip(" ,")
        if line:
            lines.append(line)
    return "\n".join(lines)


# 텍스트를 뽑을 수 없는 형식 — 내려받지 않는다
NON_TEXT_EXTS = {
    "jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "svg", "webp",
    "mp4", "avi", "mov", "wmv", "mp3", "wav", "zip", "alz", "7z",
    "xls", "xlsx", "ppt", "pptx", "doc",
}


def file_ext(filename: str | None) -> str:
    m = re.search(r"\.([A-Za-z0-9]{2,5})\s*$", filename or "")
    return m.group(1).lower() if m else ""


def _stem_key(filename: str | None) -> str:
    stem = Path(filename or "").stem
    return re.sub(r"[\s_\-()\[\]【】]+", "", stem).lower()


def select_attachment_texts(attachments: list[sqlite3.Row | dict]) -> list[str]:
    """형식만 다른 같은 문서는 하나만 남기고, 게시 순서대로 텍스트를 돌려준다."""
    chosen: dict[str, sqlite3.Row | dict] = {}
    for a in attachments:
        if not a["text"] or a["file_type"] not in TYPE_PRIORITY:
            continue
        key = _stem_key(a["filename"] or a["local_path"])
        prev = chosen.get(key)
        if prev is None or TYPE_PRIORITY[a["file_type"]] < TYPE_PRIORITY[prev["file_type"]]:
            chosen[key] = a
    return [a["text"] for a in sorted(chosen.values(), key=lambda a: a["seq"])]


def plan_downloads(conn: sqlite3.Connection, release_id: int, retry_errors: bool = False) -> list[sqlite3.Row]:
    """이 글의 첨부 중 지금 내려받을 것을 고른다.

    - 사진·영상·압축 등 텍스트를 뽑을 수 없는 형식은 'skipped'
    - 같은 문서의 다른 형식(…hwpx / …pdf)은 우선순위가 가장 높은 하나만 받고 나머지는 'deferred'.
      받은 파일이 다운로드·추출에 실패하면 release_deferred() 가 나머지를 'pending' 으로 되돌린다.
    """
    want = ("pending", "error") if retry_errors else ("pending",)
    groups: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for a in conn.execute("SELECT * FROM attachments WHERE release_id = ? ORDER BY seq", (release_id,)):
        if a["status"] in want and file_ext(a["filename"]) in NON_TEXT_EXTS:
            conn.execute("UPDATE attachments SET status = 'skipped', error = '텍스트 추출 대상 형식 아님' WHERE id = ?",
                         (a["id"],))
            continue
        groups[_stem_key(a["filename"])].append(a)

    plan: list[sqlite3.Row] = []
    for members in groups.values():
        waiting = [m for m in members if m["status"] in want]
        if not waiting:
            continue
        if any(m["status"] in ("downloaded", "extracted") for m in members):
            best, rest = None, waiting
        else:
            waiting.sort(key=lambda m: TYPE_PRIORITY.get(file_ext(m["filename"]), len(TYPE_PRIORITY)))
            best, rest = waiting[0], waiting[1:]
            plan.append(best)
        for m in rest:
            conn.execute("UPDATE attachments SET status = 'deferred' WHERE id = ?", (m["id"],))
    return sorted(plan, key=lambda a: a["seq"])


def release_deferred(conn: sqlite3.Connection, release_id: int, filename: str | None) -> int:
    """실패한 첨부와 같은 문서의 다른 형식을 다시 받을 대상으로 되돌린다."""
    key = _stem_key(filename)
    ids = [a["id"] for a in conn.execute(
        "SELECT id, filename FROM attachments WHERE release_id = ? AND status = 'deferred'", (release_id,)
    ) if _stem_key(a["filename"]) == key]
    for att_id in ids:
        conn.execute("UPDATE attachments SET status = 'pending' WHERE id = ?", (att_id,))
    return len(ids)


def _squash(text: str) -> str:
    """비교용: 공백·문장부호를 모두 지운다 (따옴표 ' 와 ‘ 처럼 표기만 다른 경우도 같게 본다)."""
    return re.sub(r"[\W_]+", "", text)


# 게시판 본문이 '요약 + 첨부 참조' 형태임을 알려 주는 문구
SEE_ATTACHMENT_RE = re.compile(r"(자세한|상세한|세부)\s*내용은\s*(붙임|첨부)|(첨부|붙임)\s*(파일|자료)?[을를]?\s*참(고|조)")


def compose_text(body: str, attachment_texts: list[str], mode: str = "best") -> tuple[str, str]:
    """(텍스트, 출처 라벨). mode: best | body | attachments"""
    body = (body or "").strip()
    att = "\n\n".join(t for t in attachment_texts if t.strip())
    if mode == "body" or not att:
        return body, "body"
    squashed_body, squashed_att = _squash(body), _squash(att)
    # 본문이 비었거나, '자세한 내용은 첨부 참고' 식의 요약이거나, 첨부보다 훨씬 짧으면 첨부만 쓴다
    if (
        mode == "attachments"
        or len(squashed_body) < 100
        or SEE_ATTACHMENT_RE.search(body)
        or len(squashed_body) * 3 < len(squashed_att)
    ):
        return att, "attachments"
    # 본문 줄 대부분이 첨부에 그대로 들어 있으면 첨부가 본문을 포함하는 것으로 본다
    lines = [_squash(l) for l in body.splitlines() if len(_squash(l)) >= 15]
    covered = sum(1 for l in lines if l in squashed_att)
    if lines and covered / len(lines) >= 0.5:
        return att, "attachments"
    return f"{body}\n\n{att}", "body+attachments"


def extract_attachments(conn: sqlite3.Connection, retry_errors: bool = False) -> tuple[int, int, int]:
    """내려받은 첨부에서 텍스트를 뽑는다. (추출, 건너뜀, 실패) 건수.

    retry_errors 는 '추출' 실패만 다시 시도한다. 다운로드 실패(HTML 응답 등)는 download 명령의 몫이다.
    """
    types = ",".join("?" * len(TEXT_TYPES))
    rows = conn.execute(
        f"""SELECT id, release_id, local_path, file_type, filename FROM attachments
            WHERE local_path IS NOT NULL
              AND (status = 'downloaded' OR (? AND status = 'error' AND file_type IN ({types})))""",
        (int(retry_errors), *TEXT_TYPES),
    ).fetchall()
    ok = skipped = failed = 0
    for row in rows:
        if row["file_type"] not in TYPE_PRIORITY:
            conn.execute("UPDATE attachments SET status='skipped' WHERE id=?", (row["id"],))
            release_deferred(conn, row["release_id"], row["filename"])
            skipped += 1
            continue
        try:
            text = extract_text(row["local_path"], row["file_type"])
            conn.execute("UPDATE attachments SET text=?, status='extracted', error=NULL WHERE id=?", (text, row["id"]))
            ok += 1
        except Exception as e:  # noqa: BLE001
            conn.execute("UPDATE attachments SET status='error', error=? WHERE id=?", (str(e), row["id"]))
            if release_deferred(conn, row["release_id"], row["filename"]):
                log.info("[extract] %s 실패 → 같은 문서의 다른 형식을 내려받도록 표시", row["filename"])
            failed += 1
            log.warning("[extract] 실패 %s: %s", row["filename"], e)
    conn.commit()
    return ok, skipped, failed


def build_doc_text(conn: sqlite3.Connection, mode: str = "best") -> int:
    """수집 완료된 모든 글의 분석용 텍스트를 다시 만들고 전문검색 색인을 갱신한다."""
    releases = conn.execute(
        "SELECT id, title, body_text FROM releases WHERE status = 'fetched'"
    ).fetchall()
    for r in releases:
        atts = conn.execute(
            "SELECT seq, filename, local_path, file_type, text FROM attachments WHERE release_id = ? ORDER BY seq",
            (r["id"],),
        ).fetchall()
        text, label = compose_text(r["body_text"] or "", select_attachment_texts(atts), mode)
        text = clean_text(text)
        conn.execute(
            """INSERT INTO doc_text (release_id, text_source, text, text_hash, char_len, built_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT (release_id) DO UPDATE SET text_source = excluded.text_source, text = excluded.text,
                   text_hash = excluded.text_hash, char_len = excluded.char_len, built_at = excluded.built_at""",
            (r["id"], label, text, db.text_hash(text), len(text), db.now()),
        )
        conn.execute("DELETE FROM doc_fts WHERE rowid = ?", (r["id"],))
        conn.execute("INSERT INTO doc_fts (rowid, title, text) VALUES (?, ?, ?)", (r["id"], r["title"] or "", text))
    conn.commit()
    return len(releases)
