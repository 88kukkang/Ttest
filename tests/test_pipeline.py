"""가짜 HTTP 로 목록 → 상세 → 첨부 → 텍스트 → 형태소 → 분석까지 한 번에 돌려 본다."""

from pathlib import Path

import pytest

from moisdb import db
from moisdb.cli import main
from moisdb.config import GOV_START, Settings
from moisdb.corpus import build_doc_text, extract_attachments
from moisdb.sources import mois_board


@pytest.fixture
def env(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    conn = db.connect(settings.db_path)
    yield settings, conn
    conn.close()


def test_discover_stops_at_start_date(env, fake_http):
    settings, conn = env
    assert mois_board.discover(conn, fake_http, settings, start=GOV_START) == 3
    pages = [p["pageIndex"] for _, p in fake_http.calls]
    assert pages == [1, 2]  # 2쪽이 모두 출범일 이전이라 3쪽은 요청하지 않음
    ids = {r["source_id"] for r in conn.execute("SELECT source_id FROM releases")}
    assert ids == {"120105", "120101", "120090"}  # 고정 공지(2024)와 출범 전 글은 제외
    # 다시 돌려도 중복 없이, until_known 이면 첫 쪽에서 멈춘다
    fake_http.calls.clear()
    assert mois_board.discover(conn, fake_http, settings, start=GOV_START, until_known=True) == 0
    assert len(fake_http.calls) == 1


def test_full_pipeline(env, fake_http):
    pytest.importorskip("kiwipiepy")
    settings, conn = env
    mois_board.discover(conn, fake_http, settings, start=GOV_START)
    ok, fail = mois_board.fetch_details(conn, fake_http, settings, limit=1)
    assert (ok, fail) == (1, 0)

    rel = conn.execute("SELECT * FROM releases WHERE status = 'fetched'").fetchone()
    assert rel["source_id"] == "120105"
    assert (settings.raw_dir / "mois" / "press" / "120105.html").exists()

    atts = conn.execute("SELECT seq, file_type, status FROM attachments ORDER BY seq").fetchall()
    # 같은 문서의 PDF 는 HWPX 가 있으므로 보류, 사진은 받지 않음, 세 번째는 서버가 HTML 오류 페이지를 줌
    assert [tuple(a) for a in atts] == [
        (1, "hwpx", "downloaded"), (2, None, "deferred"), (3, "html", "error"), (4, None, "skipped"),
    ]
    assert not any("fileSn=1" in url for url, _ in fake_http.calls)

    assert extract_attachments(conn) == (1, 0, 0)
    # 추출 재시도가 다운로드 실패(HTML 응답)를 '건너뜀'으로 덮어쓰면 안 된다
    assert extract_attachments(conn, retry_errors=True) == (0, 0, 0)
    assert conn.execute("SELECT status FROM attachments WHERE seq = 3").fetchone()[0] == "error"
    assert build_doc_text(conn) == 1
    doc = conn.execute("SELECT text_source, text FROM doc_text").fetchone()
    assert doc["text_source"] == "attachments"  # HWPX 가 본문을 포함하므로 첨부만 사용
    assert "홍길동" not in doc["text"]  # 담당자 줄 제거
    assert doc["text"].count("평가위원회") == 1  # 본문·HWPX 중복 없음

    from moisdb.analysis.keywords import load_corpus, top_terms
    from moisdb.analysis.tokenizer import NounTokenizer, tokenize_corpus

    tok = NounTokenizer()
    assert tokenize_corpus(conn, tok) == 1
    assert tokenize_corpus(conn, tok) == 0  # 바뀐 게 없으면 재분석하지 않음
    terms = {r["term"] for r in top_terms(load_corpus(conn))}
    assert {"지방소멸대응기금", "인구감소지역", "생활인구"} <= terms


def test_cli_search_and_stats(env, fake_http, capsys):
    settings, conn = env
    mois_board.discover(conn, fake_http, settings, start=GOV_START)
    mois_board.fetch_details(conn, fake_http, settings, limit=1)
    extract_attachments(conn)
    build_doc_text(conn)

    main(["--data-dir", str(settings.data_dir), "search", "평가위원회"])
    assert "지방소멸대응기금 2026년 배분 결과 발표" in capsys.readouterr().out
    main(["--data-dir", str(settings.data_dir), "search", "평가"])  # 3글자 미만은 LIKE 검색
    assert "지방소멸대응기금 2026년 배분 결과 발표" in capsys.readouterr().out
    main(["--data-dir", str(settings.data_dir), "stats"])
    out = capsys.readouterr().out
    assert "fetched" in out and "2025-06" in out


def test_fallback_to_other_format_when_extraction_fails(env, fake_http):
    settings, conn = env
    mois_board.discover(conn, fake_http, settings, start=GOV_START)
    mois_board.fetch_details(conn, fake_http, settings, limit=1)
    # 받은 HWPX 가 깨져 있다고 가정 → 추출 실패 → 같은 이름의 PDF 를 대신 받는다
    hwpx = conn.execute("SELECT local_path FROM attachments WHERE seq = 1").fetchone()[0]
    Path(hwpx).write_bytes(b"PK\x03\x04 broken")
    assert extract_attachments(conn) == (0, 0, 1)
    assert conn.execute("SELECT status FROM attachments WHERE seq = 2").fetchone()[0] == "pending"

    assert mois_board.download_pending(conn, fake_http, settings) == 1
    assert extract_attachments(conn) == (1, 0, 0)
    build_doc_text(conn)
    assert conn.execute("SELECT text_source FROM doc_text").fetchone()[0] == "body+attachments"


class _DownHttp:
    """상세 페이지 요청이 모두 타임아웃 나는 상황."""

    def __init__(self, inner):
        self.inner = inner
        self.article_calls = 0

    def get(self, url, params=None, **kw):
        if "commonSelectBoardArticle" in url:
            self.article_calls += 1
            import requests

            raise requests.ConnectTimeout("timed out")
        return self.inner.get(url, params, **kw)


def test_fetch_stops_when_site_unreachable_and_keeps_status(env, fake_http):
    settings, conn = env
    mois_board.discover(conn, fake_http, settings, start=GOV_START)
    down = _DownHttp(fake_http)
    ok, fail = mois_board.fetch_details(conn, down, settings, max_consecutive_failures=2)
    assert (ok, fail, down.article_calls) == (0, 2, 2)  # 3건 중 2번 연속 실패 후 중단
    statuses = {r[0] for r in conn.execute("SELECT status FROM releases")}
    assert statuses == {"listed"}  # 접속 오류는 '실패'로 표시하지 않아 다음 실행에서 다시 시도
