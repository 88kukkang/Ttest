from datetime import date

from conftest import fixture_html

from moisdb.sources import mois_board

BOARD_ID = "BBSMSTR_000000000008"


def test_parse_list_reads_ids_dates_departments():
    items = mois_board.parse_list(fixture_html("mois_list_page1.html"), BOARD_ID)
    by_id = {it.ntt_id: it for it in items}

    assert list(by_id) == ["110001", "120105", "120101", "120090"]
    assert by_id["120105"].title == "지방소멸대응기금 2026년 배분 결과 발표"
    assert by_id["120105"].date == date(2025, 6, 10)
    assert by_id["120105"].department == "지역균형발전과"
    # onclick 의 자바스크립트 호출에서도 nttId 를 뽑는다
    assert by_id["120101"].date == date(2025, 6, 5)
    # 세션 ID 가 붙은 href 대신 정규화된 URL 을 쓴다
    assert by_id["120105"].url.endswith(f"commonSelectBoardArticle.do?bbsId={BOARD_ID}&nttId=120105")
    assert ";jsessionid" not in by_id["110001"].url


def test_parse_list_flags_pinned_rows():
    items = {it.ntt_id: it for it in mois_board.parse_list(fixture_html("mois_list_page1.html"), BOARD_ID)}
    assert items["110001"].pinned
    assert not items["120105"].pinned


def test_parse_list_ignores_paging_links():
    items = mois_board.parse_list(fixture_html("mois_list_page1.html"), BOARD_ID)
    assert all(len(it.ntt_id) >= 4 for it in items)


def test_parse_article_metadata_body_and_attachments():
    art = mois_board.parse_article(fixture_html("mois_article.html"))

    assert art.title == "지방소멸대응기금 2026년 배분 결과 발표"
    assert art.date == date(2025, 6, 10)
    assert art.department == "지역균형발전과"
    assert art.body_selector == "heuristic"
    assert art.body_text.startswith("□ 행정안전부는 인구감소지역의 활력을")
    # 메뉴·푸터·첨부목록·이전글은 본문에 섞이지 않아야 한다
    for noise in ("기관소개", "정부세종청사", "이전글", "바로보기", ".hwpx"):
        assert noise not in art.body_text

    assert [a.filename for a in art.attachments] == [
        "250610 (보도자료) 지방소멸대응기금 배분.hwpx",
        "250610 (보도자료) 지방소멸대응기금 배분.pdf",
        "(붙임) 시군구별 배분액.hwp",
        "현장 사진.jpg",
    ]
    assert art.attachments[1].url == (
        "https://www.mois.go.kr/cmm/fms/FileDown.do?atchFileId=FILE_000000000123456&fileSn=1"
    )


def test_parse_article_prefers_known_selector():
    html = """<html><body><div class="view_cont"><p>본문 첫 문단입니다. 충분히 긴 본문이 들어 있어야
    선택자가 채택됩니다. 행정안전부 보도자료 본문 예시 문장.</p></div><div class="other">기타</div></body></html>"""
    art = mois_board.parse_article(html)
    assert art.body_selector == "div.view_cont"
    assert "기타" not in art.body_text


def test_parse_date_variants():
    assert mois_board.parse_date("등록일 2025.06.04") == date(2025, 6, 4)
    assert mois_board.parse_date("2025-6-4") == date(2025, 6, 4)
    assert mois_board.parse_date("2025년 6월 4일") == date(2025, 6, 4)
    assert mois_board.parse_date("2025.13.40") is None
    assert mois_board.parse_date(None) is None


def test_content_disposition_korean_filename():
    raw = "보도자료.hwp".encode("utf-8").decode("latin-1")
    assert mois_board._content_disposition_name({"Content-Disposition": f'attachment; filename="{raw}"'}) == "보도자료.hwp"
    cp949 = "붙임.pdf".encode("cp949").decode("latin-1")
    assert mois_board._content_disposition_name({"Content-Disposition": f"attachment; filename={cp949}"}) == "붙임.pdf"
    assert mois_board._content_disposition_name(
        {"Content-Disposition": "attachment; filename*=UTF-8''%EB%B6%99%EC%9E%84.hwpx"}
    ) == "붙임.hwpx"
