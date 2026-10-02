"""실제 누리집 페이지 사본(tests/fixtures/real)으로 파서를 점검한다."""

from datetime import date
from pathlib import Path

from moisdb.corpus import clean_text, compose_text
from moisdb.extract import extract_text, sniff_type
from moisdb.http import decode_html
from moisdb.sources import mois_board

REAL = Path(__file__).parent / "fixtures" / "real"
BOARD_ID = "BBSMSTR_000000000008"


def _html(name: str) -> str:
    return decode_html((REAL / name).read_bytes())


def test_real_list_page():
    items = mois_board.parse_list(_html("list_page1.html"), BOARD_ID)
    assert len(items) == 10
    # 상단 메뉴의 다른 게시판 글(예산현황)과 '마지막페이지' 링크는 제외
    assert all(it.ntt_id not in ("123335", "1609") for it in items)
    assert all(it.date and it.department and not it.pinned for it in items)
    first = items[0]
    assert (first.ntt_id, first.date, first.department) == ("129962", date(2026, 10, 2), "재난대응훈련과")
    assert first.title.startswith("‘강풍 타고 확산하는 대형산불’")


def test_real_article_page():
    art = mois_board.parse_article(_html("article_129962.html"))
    assert art.title == "‘강풍 타고 확산하는 대형산불’한 총리, “가을철 산불조심기간 철저히 대비”"
    assert (art.date, art.department, art.body_selector) == (date(2026, 10, 2), "재난대응훈련과", "div#desc_pc")
    assert art.body_text.startswith("- 한 총리, 가을철 산불조심기간 앞두고")
    # 본문에 숨어 있는 한글 편집기 JSON 주석은 버린다
    assert "documentPr" not in art.body_html and "documentPr" not in art.body_text
    assert [a.filename.rsplit(".", 1)[1] for a in art.attachments] == ["hwpx", "pdf"]
    assert art.attachments[0].url.endswith("atchFileId=FILE_00149494U-RIvK5&fileSn=0")


def test_real_hwpx_covers_body():
    path = REAL / "article_129962.hwpx"
    assert sniff_type(path) == "hwpx"
    att = extract_text(path, "hwpx")
    assert "레디 코리아" in att
    body = mois_board.parse_article(_html("article_129962.html")).body_text
    text, label = compose_text(body, [att])
    assert label == "attachments"
    cleaned = clean_text(text)
    assert "보도시점" not in cleaned and cleaned.count("레디 코리아(READY Korea)") == 1
