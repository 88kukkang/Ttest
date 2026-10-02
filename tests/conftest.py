"""테스트 공용 도구: 합성 픽스처, 가짜 HTTP 세션, 테스트용 HWPX/PDF 생성기."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def make_hwpx(paragraphs: list[str], table_cells: list[str] = ()) -> bytes:
    """본문 문단 + (선택) 표 하나를 가진 최소 HWPX."""
    ns = 'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
    body = "".join(f"<hp:p><hp:run><hp:t>{p}</hp:t></hp:run></hp:p>" for p in paragraphs)
    if table_cells:
        cells = "".join(
            f"<hp:tc><hp:subList><hp:p><hp:run><hp:t>{c}</hp:t></hp:run></hp:p></hp:subList></hp:tc>"
            for c in table_cells
        )
        body += f"<hp:p><hp:run><hp:tbl><hp:tr>{cells}</hp:tr></hp:tbl></hp:run></hp:p>"
    xml = f'<?xml version="1.0" encoding="UTF-8"?><hs:sec {ns}>{body}</hs:sec>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("Contents/section0.xml", xml)
    return buf.getvalue()


def make_pdf(lines: list[str]) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    for i, line in enumerate(lines):
        page.insert_text((72, 72 + 20 * i), line, fontname="korea")
    return doc.tobytes()


ARTICLE_PARAGRAPHS = [
    "□ 행정안전부는 인구감소지역의 활력을 높이기 위해 2026년도 지방소멸대응기금 1조 원의 배분 결과를 발표했다.",
    "○ 이번 배분은 기초자치단체 89곳과 관심지역 18곳을 대상으로 투자계획 평가 결과를 반영하였다.",
    "○ 평가는 외부 전문가로 구성된 평가위원회가 진행하였으며, 생활인구 유입 효과를 중점적으로 살폈다.",
    "□ 행정안전부 장관은 “지방소멸대응기금이 지역 맞춤형 사업에 쓰이도록 지원하겠다”고 밝혔다.",
    "담당 부서 지역균형발전과",
    "과장 홍길동",
]


class FakeResponse:
    def __init__(self, content: bytes, headers: dict | None = None):
        self.content = content
        self.headers = headers or {"Content-Type": "text/html;charset=UTF-8"}
        self.status_code = 200


class FakeHttp:
    """URL 패턴별로 픽스처를 돌려주는 가짜 세션. 요청 기록을 calls 에 남긴다."""

    def __init__(self):
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url: str, params: dict | None = None, **_):
        self.calls.append((url, params))
        if "commonSelectBoardList.do" in url:
            page = (params or {}).get("pageIndex", 1)
            name = {1: "mois_list_page1.html", 2: "mois_list_page2.html"}.get(page)
            html = fixture_html(name) if name else "<html><body><table></table></body></html>"
            return FakeResponse(html.encode("utf-8"))
        if "commonSelectBoardArticle.do" in url:
            return FakeResponse(fixture_html("mois_article.html").encode("utf-8"))
        if "FileDown.do" in url:
            if url.endswith("fileSn=0"):
                return FakeResponse(make_hwpx(ARTICLE_PARAGRAPHS), {"Content-Type": "application/octet-stream"})
            if url.endswith("fileSn=1"):
                return FakeResponse(make_pdf(ARTICLE_PARAGRAPHS[:2]), {"Content-Type": "application/pdf"})
            # 세 번째 첨부는 서버가 오류 페이지를 돌려준 상황을 흉내 낸다
            return FakeResponse(b"<!DOCTYPE html><html><body>error</body></html>")
        raise AssertionError(f"예상치 못한 URL: {url}")


@pytest.fixture
def fake_http() -> FakeHttp:
    return FakeHttp()
