"""행정안전부 누리집(www.mois.go.kr) 보도자료 게시판 수집기.

전자정부프레임워크 게시판(commonSelectBoardList.do / commonSelectBoardArticle.do,
bbsId·nttId·pageIndex 파라미터, /cmm/fms/FileDown.do 첨부 다운로드) 구조를 전제로 한다.

사이트 마크업이 바뀌어도 버틸 수 있도록 CSS 선택자에 전적으로 의존하지 않고
- 목록: nttId 가 들어간 링크를 찾아 그 행(tr/li)에서 날짜·부서를 읽고
- 상세: 알려진 선택자 → 실패 시 '본문 블록 추정' 휴리스틱
순서로 파싱한다. 처음 돌리기 전에 `moisdb recon` 으로 파싱 결과를 반드시 확인할 것.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from .. import db
from ..config import ARTICLE_PATH, BOARDS, FILE_DOWN_PATH, LIST_PATH, MOIS_BASE, START_DATE, Settings
from ..corpus import plan_downloads, release_deferred
from ..extract import html_to_text, sniff_type
from ..http import decode_html

log = logging.getLogger(__name__)

SOURCE = "mois"

DATE_RE = re.compile(r"(20\d{2})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})")
NTT_RE = re.compile(r"nttId=(\d+)")
BBS_RE = re.compile(r"bbsId=(\w+)")
JS_ID_RE = re.compile(r"\(\s*['\"]?(\d{4,})['\"]?\s*[,)]")
ARTICLE_LINK_RE = re.compile(r"commonSelectBoardArticle|inqire|Article", re.I)
JS_FILE_RE = re.compile(r"\(\s*['\"](FILE_[\w]+)['\"]\s*,\s*['\"]?(\d+)['\"]?")
EXT_RE = re.compile(r"\.(hwpx?|pdf|docx?|xlsx?|pptx?|zip|jpe?g|png|gif|txt|csv)\b", re.I)
SIZE_SUFFIX_RE = re.compile(r"\s*[\[(]\s*\d[\d.,]*\s*[KMG]?B\s*[\])]\s*$", re.I)
PREVIEW_RE = re.compile(r"바로보기|미리보기|preview|viewer|synap", re.I)
NOISE_RE = re.compile(
    r"gnb|lnb|snb|header|footer|nav|menu|quick|sitemap|location|breadcrumb|skip|banner"
    r"|share|sns|util|satisfaction|survey|paging|pagination|prev|next|btn|file|attach",
    re.I,
)

# 상세 페이지에서 먼저 시도할 선택자. 맨 앞은 2026-10 실제 사이트에서 확인한 것, 나머지는 개편 대비 후보.
TITLE_SELECTORS = [
    "h4.subject", "div.view_title", "div.bbs_view h3", "div.view_head h3", "div.board_view h3",
    "div.title_area h3", "th.title", "h3.title", "h4.title",
]
BODY_SELECTORS = [
    "div#desc_pc", "div.desc", "div.view_cont", "div.view_con", "div.view_content", "div.bbs_view_cont",
    "div.board_view_cont", "div.cont_view", "div.viewContents", "td.view_cont", "td.cont",
]


@dataclass
class ListItem:
    ntt_id: str
    title: str
    date: date | None
    department: str | None
    url: str
    pinned: bool = False


@dataclass
class AttachmentLink:
    filename: str
    url: str


@dataclass
class Article:
    title: str | None
    date: date | None
    department: str | None
    body_html: str
    body_text: str
    attachments: list[AttachmentLink] = field(default_factory=list)
    body_selector: str | None = None  # 어떤 방법으로 본문을 찾았는지 (진단용)


# ---------------------------------------------------------------- URL


def list_url(base: str = MOIS_BASE) -> str:
    return f"{base}{LIST_PATH}"


def article_url(board_id: str, ntt_id: str, base: str = MOIS_BASE) -> str:
    return f"{base}{ARTICLE_PATH}?bbsId={board_id}&nttId={ntt_id}"


# ---------------------------------------------------------------- 파싱: 공통


def parse_date(text: str | None) -> date | None:
    m = DATE_RE.search(text or "")
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# ---------------------------------------------------------------- 파싱: 목록


def _article_id(a: Tag, board_id: str) -> str | None:
    """이 게시판 글로 가는 링크면 nttId. 메뉴의 다른 게시판 글, 페이지 이동 링크는 제외한다."""
    ref = f"{a.get('href') or ''} {a.get('onclick') or ''}"
    if not ARTICLE_LINK_RE.search(ref):
        return None
    bbs = BBS_RE.search(ref)
    if bbs and bbs.group(1) != board_id:
        return None
    m = NTT_RE.search(ref) or JS_ID_RE.search(ref)
    return m.group(1) if m else None


def _column_index(table: Tag | None, keywords: tuple[str, ...]) -> int | None:
    if table is None:
        return None
    head = table.select("thead th")
    if not head:
        first_row = table.find("tr")
        head = first_row.find_all("th") if first_row else []
    for i, th in enumerate(head):
        label = th.get_text(strip=True)
        if any(k in label for k in keywords):
            return i
    return None


def parse_list(html: str, board_id: str, base: str = MOIS_BASE) -> list[ListItem]:
    soup = BeautifulSoup(html, "lxml")
    items: list[ListItem] = []
    seen: set[str] = set()
    for a in soup.find_all("a"):
        ntt_id = _article_id(a, board_id)
        if not ntt_id or ntt_id in seen:
            continue
        seen.add(ntt_id)
        title = _clean(a.get_text(" ", strip=True)) or _clean(a.get("title"))
        row = a.find_parent("tr") or a.find_parent("li") or a.parent

        department = None
        pinned = "notice" in " ".join(row.get("class", [])).lower()
        if row.name == "tr":
            cells = row.find_all(["td", "th"], recursive=False)
            title_cell = a.find_parent(["td", "th"])
            other_text = " ".join(c.get_text(" ", strip=True) for c in cells if c is not title_cell)
            idx = _column_index(row.find_parent("table"), ("부서", "담당", "작성자"))
            if idx is not None and idx < len(cells) and cells[idx] is not title_cell:
                department = _clean(cells[idx].get_text(" ", strip=True)) or None
            if cells and cells[0] is not title_cell and not cells[0].get_text(strip=True).isdigit():
                pinned = True  # 번호 칸에 '공지' 등이 있으면 상단 고정 글
        else:
            other_text = row.get_text(" ", strip=True).replace(a.get_text(" ", strip=True), " ")

        items.append(
            ListItem(
                ntt_id=ntt_id,
                title=title,
                date=parse_date(other_text),
                department=department,
                url=article_url(board_id, ntt_id, base),
                pinned=pinned,
            )
        )
    return items


# ---------------------------------------------------------------- 파싱: 상세


def _next_value(el: Tag) -> str | None:
    nxt = el.next_sibling
    while isinstance(nxt, NavigableString) and not nxt.strip():
        nxt = nxt.next_sibling
    if nxt is None:
        return None
    value = nxt.get_text(" ", strip=True) if isinstance(nxt, Tag) else str(nxt)
    return _clean(value).strip(" :：|") or None


def _labeled_value(soup: BeautifulSoup, labels: tuple[str, ...]) -> str | None:
    """'등록일 2025.06.05' 처럼 라벨 옆에 붙은 값을 찾는다 (th/td, dt/dd, strong+텍스트 등)."""
    for el in soup.find_all(["th", "dt", "strong", "span", "em", "label", "li", "b"]):
        own = _clean(el.get_text(" ", strip=True))
        if not own or len(own) > 30:
            continue
        for label in labels:
            # '담당 부서'처럼 라벨 글자 사이에 공백이 있어도 매칭
            m = re.match(r"\s*".join(map(re.escape, label)) + r"\s*[:：|]?\s*(.*)$", own)
            if not m:
                continue
            rest = m.group(1).strip()
            if rest:
                return rest
            value = _next_value(el)
            if value:
                return value
    return None


def _strip_noise(soup: BeautifulSoup) -> None:
    for t in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "iframe"]):
        t.decompose()
    for t in soup.find_all(True):
        if t.decomposed or t.name in ("html", "body"):
            continue
        ident = " ".join([t.get("id") or "", *t.get("class", [])])
        if ident.strip() and NOISE_RE.search(ident):
            t.decompose()


def _text_len(el: Tag) -> int:
    return len(el.get_text("", strip=True))


def _main_block(soup: BeautifulSoup) -> Tag:
    """텍스트의 80% 이상을 가진 자식으로 계속 내려가, 본문이 갈라지는 지점을 본문 블록으로 본다."""
    node: Tag = soup.body or soup
    while True:
        total = _text_len(node)
        kids = [c for c in node.find_all(True, recursive=False)]
        if not kids or total == 0:
            return node
        best = max(kids, key=_text_len)
        if _text_len(best) >= 0.8 * total:
            node = best
        else:
            return node


def _pick_filename(a: Tag) -> str:
    candidates = [a.get_text(" ", strip=True), a.get("title") or "", a.get("download") or ""]
    for c in candidates:
        if EXT_RE.search(c):
            return _clean_filename(c)
    return _clean_filename(candidates[0] or candidates[1]) or "attachment"


def _clean_filename(name: str) -> str:
    name = SIZE_SUFFIX_RE.sub("", _clean(name))
    name = re.sub(r"\s*(다운로드|내려받기)\s*$", "", name)
    return name.strip()


def parse_attachments(soup: BeautifulSoup, base: str = MOIS_BASE) -> list[AttachmentLink]:
    out: list[AttachmentLink] = []
    seen: set[str] = set()
    for a in soup.find_all("a"):
        href = a.get("href") or ""
        onclick = a.get("onclick") or ""
        text = a.get_text(" ", strip=True)
        if PREVIEW_RE.search(f"{text} {href} {onclick} {a.get('title') or ''}"):
            continue
        url = None
        if not href.lower().startswith("javascript") and re.search(r"FileDown|fileDown|download", href):
            url = urljoin(base + "/", href)
        else:
            m = JS_FILE_RE.search(f"{href} {onclick}")
            if m:
                url = f"{base}{FILE_DOWN_PATH}?atchFileId={m.group(1)}&fileSn={m.group(2)}"
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(AttachmentLink(filename=_pick_filename(a), url=url))
    return out


def parse_article(html: str, base: str = MOIS_BASE) -> Article:
    soup = BeautifulSoup(html, "lxml")
    attachments = parse_attachments(soup, base)

    title = None
    for sel in TITLE_SELECTORS:
        el = soup.select_one(sel)
        if el and _clean(el.get_text(" ", strip=True)):
            title = _clean(el.get_text(" ", strip=True))
            break
    if not title:
        og = soup.find("meta", attrs={"property": "og:title"})
        title = _clean(og.get("content")) if og else None

    published = parse_date(_labeled_value(soup, ("등록일", "작성일", "게시일", "배포일")))
    department = _labeled_value(soup, ("담당부서", "부서명", "부서", "작성자"))

    body, how = None, None
    for sel in BODY_SELECTORS:
        el = soup.select_one(sel)
        if el and _text_len(el) >= 50:
            body, how = el, sel
            break
    if body is None:
        stripped = BeautifulSoup(html, "lxml")
        _strip_noise(stripped)
        body, how = _main_block(stripped), "heuristic"

    # 본문 안 HTML 주석(한글 편집기 JSON 등 수십 KB)은 저장할 필요가 없다
    for c in body.find_all(string=lambda t: isinstance(t, Comment)):
        c.extract()

    return Article(
        title=title,
        date=published,
        department=department,
        body_html=str(body),
        body_text=html_to_text(body),
        attachments=attachments,
        body_selector=how,
    )


# ---------------------------------------------------------------- 수집: 목록


def discover(
    conn: sqlite3.Connection,
    http,
    settings: Settings,
    board: str = "press",
    start: date = START_DATE,
    end: date | None = None,
    max_pages: int = 1000,
    until_known: bool = False,
    base: str = MOIS_BASE,
) -> int:
    """목록을 1페이지부터 넘기며 기간 내 글을 releases 에 등록한다. 새로 찾은 건수를 돌려준다.

    목록은 최신순이므로, 한 페이지의 (고정글 제외) 글이 모두 start 이전이면 멈춘다.
    until_known=True 면 새 글이 하나도 없는 페이지에서 멈춘다(일일 갱신용).
    """
    board_id = BOARDS[board]
    list_dir = settings.raw_dir / SOURCE / board / "list"
    list_dir.mkdir(parents=True, exist_ok=True)
    total_new = 0
    for page in range(1, max_pages + 1):
        resp = http.get(list_url(base), params={"bbsId": board_id, "pageIndex": page})
        (list_dir / f"page_{page:04d}.html").write_bytes(resp.content)
        items = parse_list(decode_html(resp.content, resp.headers.get("Content-Type", "")), board_id, base)
        if not items:
            log.warning("목록 %d쪽에서 글을 찾지 못함 — 마지막 쪽이거나 파서 점검 필요(moisdb recon list)", page)
            break

        page_new = 0
        for it in items:
            if it.date and (it.date < start or (end and it.date > end)):
                continue
            if it.date is None:
                log.warning("날짜를 읽지 못한 글: nttId=%s %s", it.ntt_id, it.title)
            is_new = db.upsert_listing(
                conn,
                source=SOURCE,
                source_id=it.ntt_id,
                board=board,
                url=it.url,
                title=it.title or None,
                published_date=it.date.isoformat() if it.date else None,
                department=it.department,
            )
            page_new += is_new
        conn.commit()
        total_new += page_new

        # 고정글 판별이 빗나가 모든 행이 고정글로 잡혀도 멈출 수 있도록 전체 날짜로 대체
        dated = [it.date for it in items if it.date and not it.pinned] or [it.date for it in items if it.date]
        log.info("[discover] %d쪽: %d건 중 신규 %d건 (가장 최근 %s, 가장 오래된 %s)",
                 page, len(items), page_new, max(dated, default=None), min(dated, default=None))
        if dated and max(dated) < start:
            break
        if until_known and page_new == 0:
            break
    return total_new


# ---------------------------------------------------------------- 수집: 상세 + 첨부


def _safe_filename(name: str, limit: int = 120) -> str:
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .") or "file"
    if len(name) > limit:
        stem, dot, ext = name.rpartition(".")
        name = (stem[: limit - len(ext) - 1] + "." + ext) if dot and len(ext) <= 5 else name[:limit]
    return name


def _content_disposition_name(headers) -> str | None:
    cd = headers.get("Content-Disposition", "") or ""
    m = re.search(r"filename\*\s*=\s*(?:UTF-8'')?([^;]+)", cd, re.I)
    if m:
        return unquote(m.group(1).strip('"'))
    m = re.search(r'filename\s*=\s*"?([^";]+)"?', cd, re.I)
    if not m:
        return None
    raw = m.group(1)
    try:
        raw_bytes = raw.encode("latin-1")  # requests 는 헤더를 latin-1 로 디코딩해 둔다
    except UnicodeEncodeError:
        return unquote(raw)
    for enc in ("utf-8", "cp949"):
        try:
            return unquote(raw_bytes.decode(enc))
        except UnicodeDecodeError:
            continue
    return None


def store_article(conn: sqlite3.Connection, release_id: int, art: Article, raw_path: Path | None) -> None:
    conn.execute(
        """
        UPDATE releases SET
            title = COALESCE(title, ?),
            published_date = COALESCE(published_date, ?),
            department = COALESCE(department, ?),
            body_html = ?, body_text = ?,
            meta_json = ?, raw_path = COALESCE(?, raw_path),
            fetched_at = COALESCE(fetched_at, ?),
            status = 'fetched', error = NULL
        WHERE id = ?
        """,
        (
            art.title,
            art.date.isoformat() if art.date else None,
            art.department,
            art.body_html,
            art.body_text,
            json.dumps({"body_selector": art.body_selector}, ensure_ascii=False),
            str(raw_path) if raw_path else None,
            db.now(),
            release_id,
        ),
    )
    for seq, att in enumerate(art.attachments, start=1):
        conn.execute(
            """
            INSERT INTO attachments (release_id, seq, filename, url) VALUES (?, ?, ?, ?)
            ON CONFLICT (release_id, url) DO UPDATE SET seq = excluded.seq, filename = excluded.filename
            """,
            (release_id, seq, att.filename, att.url),
        )


def download_attachment(conn: sqlite3.Connection, http, settings: Settings, att: sqlite3.Row, ntt_id: str) -> None:
    try:
        resp = http.get(att["url"])
        name = att["filename"] or _content_disposition_name(resp.headers) or f"file{att['seq']}"
        if not EXT_RE.search(name):
            name = _content_disposition_name(resp.headers) or name
        dest = settings.files_dir / SOURCE / ntt_id / f"{att['seq']:02d}_{_safe_filename(name)}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        ftype = sniff_type(dest)
        status, error = ("error", "파일 대신 HTML 응답을 받음") if ftype == "html" else ("downloaded", None)
        conn.execute(
            "UPDATE attachments SET local_path=?, sha256=?, size=?, file_type=?, status=?, error=? WHERE id=?",
            (str(dest), hashlib.sha256(resp.content).hexdigest(), len(resp.content), ftype, status, error, att["id"]),
        )
        if status == "error":
            release_deferred(conn, att["release_id"], att["filename"])
    except Exception as e:  # noqa: BLE001 — 한 파일 실패가 전체 수집을 멈추지 않도록
        log.warning("첨부 다운로드 실패 nttId=%s %s: %s", ntt_id, att["filename"], e)
        conn.execute("UPDATE attachments SET status='error', error=? WHERE id=?", (str(e), att["id"]))
        release_deferred(conn, att["release_id"], att["filename"])


def fetch_details(
    conn: sqlite3.Connection,
    http,
    settings: Settings,
    limit: int | None = None,
    download: bool = True,
    retry_errors: bool = False,
    base: str = MOIS_BASE,
) -> tuple[int, int]:
    """status='listed' 인 글의 상세 페이지를 받아 원본 저장 → 파싱 → 첨부 다운로드. (성공, 실패) 건수."""
    statuses = ("listed", "error") if retry_errors else ("listed",)
    rows = conn.execute(
        f"""SELECT id, source_id, board, url, title FROM releases
            WHERE source = ? AND status IN ({",".join("?" * len(statuses))})
            ORDER BY published_date DESC, id DESC {"LIMIT ?" if limit else ""}""",
        (SOURCE, *statuses, *([limit] if limit else [])),
    ).fetchall()
    ok = fail = 0
    for i, row in enumerate(rows, start=1):
        ntt_id = row["source_id"]
        try:
            resp = http.get(row["url"])
            raw_path = settings.raw_dir / SOURCE / (row["board"] or "press") / f"{ntt_id}.html"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(resp.content)
            art = parse_article(decode_html(resp.content, resp.headers.get("Content-Type", "")), base)
            store_article(conn, row["id"], art, raw_path)
            conn.commit()
            if download:
                for att in plan_downloads(conn, row["id"], retry_errors=True):
                    download_attachment(conn, http, settings, att, ntt_id)
                conn.commit()
            ok += 1
            log.info("[fetch] %d/%d nttId=%s 첨부 %d개 · %s", i, len(rows), ntt_id, len(art.attachments), row["title"])
        except Exception as e:  # noqa: BLE001
            conn.execute("UPDATE releases SET status='error', error=? WHERE id=?", (str(e), row["id"]))
            conn.commit()
            fail += 1
            log.warning("[fetch] 실패 nttId=%s: %s", ntt_id, e)
    return ok, fail


def download_pending(conn: sqlite3.Connection, http, settings: Settings, retry_errors: bool = False) -> int:
    """아직 받지 않은 첨부를 받는다 (fetch --no-download 후, 또는 다른 형식으로 대체할 때)."""
    statuses = ("pending", "error") if retry_errors else ("pending",)
    releases = conn.execute(
        f"""SELECT DISTINCT r.id, r.source_id FROM releases r JOIN attachments a ON a.release_id = r.id
            WHERE r.source = ? AND a.status IN ({",".join("?" * len(statuses))}) ORDER BY r.id""",
        (SOURCE, *statuses),
    ).fetchall()
    n = 0
    for rel in releases:
        for att in plan_downloads(conn, rel["id"], retry_errors=retry_errors):
            download_attachment(conn, http, settings, att, rel["source_id"])
            n += 1
        conn.commit()
    return n


def reparse_raw(conn: sqlite3.Connection, base: str = MOIS_BASE) -> int:
    """저장해 둔 원본 HTML 을 다시 파싱한다 (네트워크 없이 파서 개선 반영)."""
    rows = conn.execute(
        "SELECT id, raw_path FROM releases WHERE source = ? AND raw_path IS NOT NULL", (SOURCE,)
    ).fetchall()
    n = 0
    for row in rows:
        path = Path(row["raw_path"])
        if not path.exists():
            continue
        art = parse_article(decode_html(path.read_bytes()), base)
        store_article(conn, row["id"], art, None)
        n += 1
    conn.commit()
    return n


def describe_list(items: list[ListItem]) -> list[dict]:
    return [{**asdict(it), "date": it.date.isoformat() if it.date else None} for it in items]
