"""정책브리핑(korea.kr) 보도자료 OpenAPI 수집기 — 보조 원천 / 누락 교차검증용.

공공데이터포털(data.go.kr)에서 '문화체육관광부_정책브리핑_보도자료' OpenAPI 활용신청 후
받은 인증키(serviceKey)가 필요하다. 전 부처 보도자료가 나오므로 부처명으로 거른다.

※ 엔드포인트·파라미터·응답 필드명은 활용신청 화면의 명세와 반드시 대조할 것.
   응답의 모든 하위 태그를 dict 로 통째로 저장(meta_json)하므로 필드명이 달라도 원자료는 남는다.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, datetime, timedelta
from typing import Iterator

from lxml import etree

from .. import db
from ..extract import html_to_text

log = logging.getLogger(__name__)

SOURCE = "korea_kr"
ENDPOINT = "https://apis.data.go.kr/1371000/pressReleaseService/pressReleaseList"
MAX_WINDOW_DAYS = 3  # 한 번에 조회할 수 있는 최대 기간(명세 확인 필요)

_DATE_FORMATS = ("%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y%m%d%H%M%S", "%Y-%m-%d", "%Y%m%d")


def iter_windows(start: date, end: date, days: int = MAX_WINDOW_DAYS) -> Iterator[tuple[date, date]]:
    cur = start
    while cur <= end:
        stop = min(cur + timedelta(days=days - 1), end)
        yield cur, stop
        cur = stop + timedelta(days=1)


def parse_api_date(value: str | None) -> str | None:
    value = (value or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_response(xml: bytes) -> list[dict]:
    root = etree.fromstring(xml)
    code = root.findtext(".//resultCode")
    if code and code.strip() not in ("0", "00", "INFO-000"):
        raise RuntimeError(f"API 오류 {code}: {root.findtext('.//resultMsg')}")
    items = []
    for node in root.iter("NewsItem", "item"):
        items.append({etree.QName(c).localname: (c.text or "").strip() for c in node if isinstance(c.tag, str)})
    return items


def collect(
    conn: sqlite3.Connection,
    http,
    service_key: str,
    start: date,
    end: date,
    ministry: str = "행정안전부",
) -> int:
    saved = 0
    for s, e in iter_windows(start, end):
        resp = http.get(
            ENDPOINT,
            params={"serviceKey": service_key, "startDate": s.strftime("%Y%m%d"), "endDate": e.strftime("%Y%m%d")},
        )
        items = parse_response(resp.content)
        mine = [it for it in items if ministry in (it.get("MinisterCode") or "")]
        for it in mine:
            source_id = it.get("NewsItemId") or it.get("OriginalUrl") or it.get("Title")
            if not source_id:
                continue
            body_html = it.get("DataContents") or ""
            db.upsert_listing(
                conn,
                source=SOURCE,
                source_id=source_id,
                board="press",
                url=it.get("OriginalUrl"),
                title=it.get("Title"),
                published_date=parse_api_date(it.get("ApproveDate")),
                department=None,
            )
            conn.execute(
                """UPDATE releases SET body_html = ?, body_text = ?, meta_json = ?,
                       fetched_at = ?, status = 'fetched', error = NULL
                   WHERE source = ? AND source_id = ?""",
                (body_html, html_to_text(body_html), json.dumps(it, ensure_ascii=False), db.now(), SOURCE, source_id),
            )
            saved += 1
        conn.commit()
        log.info("[korea_kr] %s~%s: 전체 %d건 중 %s %d건", s, e, len(items), ministry, len(mine))
    return saved
