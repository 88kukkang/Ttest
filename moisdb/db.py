"""SQLite 스키마와 공통 DB 도우미.

단계별 테이블:
  releases     보도자료 1건 = 1행 (목록 발견 → 상세 수집 상태를 status로 관리)
  attachments  첨부파일 (다운로드 → 텍스트 추출 상태를 status로 관리)
  doc_text     분석용 최종 텍스트 (본문/첨부 중 선택 + 정제)
  doc_tokens   형태소 분석 결과 (명사 토큰)
  doc_fts      전문 검색 인덱스 (FTS5 trigram)
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS releases (
    id              INTEGER PRIMARY KEY,
    source          TEXT NOT NULL,              -- 'mois'(행안부 누리집) | 'korea_kr'(정책브리핑 API)
    source_id       TEXT NOT NULL,              -- nttId / NewsItemId
    board           TEXT,                       -- 'press' 등 config.BOARDS 키
    url             TEXT,
    title           TEXT,
    published_date  TEXT,                       -- YYYY-MM-DD (게시판 등록일)
    department      TEXT,                       -- 담당 부서
    listed_at       TEXT,                       -- 목록에서 처음 발견한 시각
    fetched_at      TEXT,                       -- 상세 페이지 수집 시각
    raw_path        TEXT,                       -- 원본 HTML 저장 경로 (재파싱용)
    body_html       TEXT,
    body_text       TEXT,
    meta_json       TEXT,                       -- 원천별 부가 정보 (JSON)
    status          TEXT NOT NULL DEFAULT 'listed',  -- listed → fetched | error
    error           TEXT,
    UNIQUE (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_releases_date ON releases (published_date);
CREATE INDEX IF NOT EXISTS idx_releases_status ON releases (source, status);

CREATE TABLE IF NOT EXISTS attachments (
    id          INTEGER PRIMARY KEY,
    release_id  INTEGER NOT NULL REFERENCES releases (id) ON DELETE CASCADE,
    seq         INTEGER NOT NULL,
    filename    TEXT,
    url         TEXT NOT NULL,
    file_type   TEXT,                           -- hwp | hwpx | pdf | docx | image | ...
    local_path  TEXT,
    sha256      TEXT,
    size        INTEGER,
    text        TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending → downloaded → extracted | skipped | error
    error       TEXT,
    UNIQUE (release_id, url)
);

CREATE TABLE IF NOT EXISTS doc_text (
    release_id   INTEGER PRIMARY KEY REFERENCES releases (id) ON DELETE CASCADE,
    text_source  TEXT NOT NULL,                 -- body | attachments | body+attachments
    text         TEXT NOT NULL,
    text_hash    TEXT NOT NULL,
    char_len     INTEGER NOT NULL,
    built_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS doc_tokens (
    release_id  INTEGER PRIMARY KEY REFERENCES releases (id) ON DELETE CASCADE,
    tokenizer   TEXT NOT NULL,                  -- 토크나이저 버전 (설정이 바뀌면 재분석)
    text_hash   TEXT NOT NULL,                  -- doc_text.text_hash 와 다르면 재분석
    tokens      TEXT NOT NULL,                  -- 공백으로 구분한 명사 토큰
    built_at    TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5 (title, text, tokenize = 'trigram');

CREATE VIEW IF NOT EXISTS v_releases AS
SELECT r.id, r.source, r.source_id, r.published_date,
       substr(r.published_date, 1, 7) AS month,
       r.department, r.title, r.url, r.status,
       d.text_source, d.char_len,
       (SELECT count(*) FROM attachments a WHERE a.release_id = r.id) AS n_attachments
FROM releases r
LEFT JOIN doc_text d ON d.release_id = r.id;
"""


def connect(path: Path | str) -> sqlite3.Connection:
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def upsert_listing(
    conn: sqlite3.Connection,
    *,
    source: str,
    source_id: str,
    board: str | None,
    url: str | None,
    title: str | None,
    published_date: str | None,
    department: str | None,
) -> bool:
    """목록에서 발견한 항목을 저장한다. 새로 추가되었으면 True."""
    exists = conn.execute(
        "SELECT 1 FROM releases WHERE source = ? AND source_id = ?", (source, source_id)
    ).fetchone()
    conn.execute(
        """
        INSERT INTO releases (source, source_id, board, url, title, published_date, department, listed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (source, source_id) DO UPDATE SET
            title = COALESCE(excluded.title, releases.title),
            published_date = COALESCE(excluded.published_date, releases.published_date),
            department = COALESCE(excluded.department, releases.department)
        """,
        (source, source_id, board, url, title, published_date, department, now()),
    )
    return exists is None
