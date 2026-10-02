"""GitHub Actions 에서 실제 사이트 구조를 확인하는 정찰 스크립트.

목록 1·2쪽, 상세 몇 건, 첨부 몇 개를 받아 samples/ 에 원본과 파싱 결과를 남긴다.
"""

import sys
import traceback
from pathlib import Path

from moisdb.config import BOARDS, Settings
from moisdb.extract import TEXT_TYPES, extract_text, sniff_type
from moisdb.http import PoliteSession, decode_html
from moisdb.sources import mois_board

OUT = Path("samples")
(OUT / "files").mkdir(parents=True, exist_ok=True)
http = PoliteSession.from_settings(Settings())
board_id = BOARDS["press"]


def save(name: str, data: bytes) -> None:
    (OUT / name).write_bytes(data)


def show_resp(resp) -> None:
    print(f"  status={resp.status_code} url={resp.url} bytes={len(resp.content)} type={resp.headers.get('Content-Type')}")


articles = []
for page in (1, 2):
    print(f"\n===== 목록 {page}쪽 =====")
    try:
        resp = http.get(mois_board.list_url(), params={"bbsId": board_id, "pageIndex": page})
        show_resp(resp)
        save(f"list_p{page}.html", resp.content)
        items = mois_board.parse_list(decode_html(resp.content, resp.headers.get("Content-Type", "")), board_id)
        for it in items:
            print(f"  {it.ntt_id} | {it.date} | {it.department} | pinned={it.pinned} | {it.title}")
        if page == 1:
            articles = [it.ntt_id for it in items if not it.pinned][:3]
    except Exception:
        traceback.print_exc(file=sys.stdout)

downloaded = 0
for ntt in articles:
    print(f"\n===== 상세 nttId={ntt} =====")
    try:
        resp = http.get(mois_board.article_url(board_id, ntt))
        show_resp(resp)
        save(f"article_{ntt}.html", resp.content)
        art = mois_board.parse_article(decode_html(resp.content, resp.headers.get("Content-Type", "")))
        print(f"  제목={art.title} | 등록일={art.date} | 부서={art.department} | 본문탐지={art.body_selector} ({len(art.body_text)}자)")
        for a in art.attachments:
            print(f"  첨부: {a.filename} <{a.url}>")
        print("  --- 본문 앞부분 ---")
        print("  " + art.body_text[:600].replace("\n", "\n  "))
        for a in art.attachments:
            if downloaded >= 4:
                break
            r = http.get(a.url)
            downloaded += 1
            dest = OUT / "files" / f"{ntt}_{downloaded}"
            dest.write_bytes(r.content)
            ftype = sniff_type(dest)
            print(f"  [다운로드] {a.filename}: {len(r.content)} bytes, 판별={ftype}, CD={r.headers.get('Content-Disposition')}")
            if ftype in TEXT_TYPES:
                try:
                    text = extract_text(dest, ftype)
                    print(f"    추출 {len(text)}자: " + text[:300].replace("\n", " / "))
                except Exception as e:  # noqa: BLE001
                    print(f"    추출 실패: {e}")
    except Exception:
        traceback.print_exc(file=sys.stdout)
