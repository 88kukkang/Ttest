"""요청 간격·재시도를 지키는 HTTP 세션과 HTML 디코딩 도우미."""

from __future__ import annotations

import re
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import Settings

_META_CHARSET_RE = re.compile(rb"""charset\s*=\s*["']?([\w-]+)""", re.I)


class PoliteSession:
    """모든 GET 사이에 최소 간격을 두고, 일시 오류는 지수 백오프로 재시도한다."""

    def __init__(self, interval: float, timeout: float, user_agent: str, retries: int = 4):
        self.interval = interval
        self.timeout = timeout
        self._last = 0.0
        self.session = requests.Session()
        retry = Retry(
            total=retries,
            backoff_factor=2,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update(
            {"User-Agent": user_agent, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.5"}
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "PoliteSession":
        return cls(settings.request_interval, settings.timeout, settings.user_agent)

    def get(self, url: str, params: dict | None = None, **kwargs) -> requests.Response:
        wait = self.interval - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout, **kwargs)
        finally:
            self._last = time.monotonic()
        resp.raise_for_status()
        return resp


def decode_html(data: bytes, content_type: str = "") -> str:
    """응답 헤더 → <meta charset> → UTF-8 → CP949 순서로 인코딩을 판단해 디코딩한다."""
    candidates = []
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    if m:
        candidates.append(m.group(1))
    m = _META_CHARSET_RE.search(data[:4096])
    if m:
        candidates.append(m.group(1).decode("ascii", "ignore"))
    candidates += ["utf-8", "cp949"]
    for enc in candidates:
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")
