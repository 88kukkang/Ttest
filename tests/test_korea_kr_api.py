from datetime import date

import pytest

from moisdb import db
from moisdb.sources import korea_kr_api

# 합성 응답: 필드명은 명세 확인 전 가정치
XML = """<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header><resultCode>0</resultCode><resultMsg>NORMAL SERVICE</resultMsg></header>
  <body>
    <NewsItem>
      <NewsItemId>156700001</NewsItemId>
      <Title>민생회복 소비쿠폰 2차 지급 개시</Title>
      <MinisterCode>행정안전부</MinisterCode>
      <ApproveDate>09/22/2025 06:00:00</ApproveDate>
      <OriginalUrl>https://www.korea.kr/briefing/pressReleaseView.do?newsId=156700001</OriginalUrl>
      <DataContents><![CDATA[<p>행정안전부는 소비쿠폰 2차 지급을 시작한다.</p>]]></DataContents>
    </NewsItem>
    <NewsItem>
      <NewsItemId>156700002</NewsItemId>
      <Title>다른 부처 보도자료</Title>
      <MinisterCode>보건복지부</MinisterCode>
      <ApproveDate>09/22/2025 09:00:00</ApproveDate>
    </NewsItem>
  </body>
</response>""".encode("utf-8")


class _Resp:
    def __init__(self, content):
        self.content = content
        self.headers = {}


class _Http:
    def __init__(self):
        self.params = []

    def get(self, url, params=None, **_):
        self.params.append(params)
        return _Resp(XML)


def test_iter_windows_covers_range_without_gaps():
    windows = list(korea_kr_api.iter_windows(date(2025, 6, 4), date(2025, 6, 10)))
    assert windows == [
        (date(2025, 6, 4), date(2025, 6, 6)),
        (date(2025, 6, 7), date(2025, 6, 9)),
        (date(2025, 6, 10), date(2025, 6, 10)),
    ]


def test_parse_response_and_error_code():
    items = korea_kr_api.parse_response(XML)
    assert [it["NewsItemId"] for it in items] == ["156700001", "156700002"]
    with pytest.raises(RuntimeError):
        korea_kr_api.parse_response(b"<response><header><resultCode>30</resultCode>"
                                    b"<resultMsg>SERVICE KEY IS NOT REGISTERED</resultMsg></header></response>")


def test_collect_filters_ministry():
    conn = db.connect(":memory:")
    http = _Http()
    n = korea_kr_api.collect(conn, http, "KEY", date(2025, 9, 22), date(2025, 9, 22))
    assert n == 1
    row = conn.execute("SELECT * FROM releases").fetchone()
    assert (row["source"], row["published_date"], row["status"]) == ("korea_kr", "2025-09-22", "fetched")
    assert row["body_text"] == "행정안전부는 소비쿠폰 2차 지급을 시작한다."
    assert http.params[0]["startDate"] == "20250922"
