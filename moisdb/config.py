"""수집 대상 URL, 기간, 저장 경로, 요청 간격 등 기본 설정."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# 이재명 정부 출범일. 이 날짜(포함) 이후 등록된 보도자료만 수집한다.
START_DATE = date(2025, 6, 4)

MOIS_BASE = "https://www.mois.go.kr"
LIST_PATH = "/frt/bbs/type010/commonSelectBoardList.do"
ARTICLE_PATH = "/frt/bbs/type010/commonSelectBoardArticle.do"
FILE_DOWN_PATH = "/cmm/fms/FileDown.do"

# 수집할 게시판. 설명자료 등 다른 게시판을 추가하려면 bbsId를 확인해 여기에 등록한다.
BOARDS = {
    "press": "BBSMSTR_000000000008",  # 뉴스·소식 > 보도자료
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


@dataclass
class Settings:
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("MOISDB_DATA_DIR", "data"))
    )
    request_interval: float = 1.5  # 요청 사이 최소 간격(초). 서버 부담을 줄이기 위해 1초 이상 권장
    timeout: float = 30.0
    user_agent: str = field(
        default_factory=lambda: os.environ.get("MOISDB_USER_AGENT", DEFAULT_USER_AGENT)
    )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "mois.sqlite3"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def files_dir(self) -> Path:
        return self.data_dir / "files"
