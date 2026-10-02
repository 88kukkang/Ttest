"""명령줄 진입점: `moisdb <명령>` (또는 `python -m moisdb <명령>`).

수집      init · discover · fetch · download · reparse · extract · build-text · tokenize · collect · update
점검      recon · stats · crosscheck · kr-api
분석      search · top · trend · distinctive · cooccur · export
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

from . import db
from .config import BOARDS, START_DATE, Settings

log = logging.getLogger("moisdb")


# ---------------------------------------------------------------- 출력 도우미


def _width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def _fit(s: str, w: int) -> str:
    out, cur = "", 0
    for c in s:
        cw = _width(c)
        if cur + cw > w:
            return out[:-1] + "…" if out else ""
        out += c
        cur += cw
    return out


def print_table(rows: list[dict], columns: list[str] | None = None, max_col: int = 60) -> None:
    if not rows:
        print("(결과 없음)")
        return
    columns = columns or list(rows[0].keys())
    cells = [[_fit(str(r.get(c, "")), max_col) for c in columns] for r in rows]
    widths = [max(_width(c), *(_width(row[i]) for row in cells)) for i, c in enumerate(columns)]
    line = lambda vals: "  ".join(v + " " * (w - _width(v)) for v, w in zip(vals, widths))  # noqa: E731
    print(line(columns))
    print("  ".join("-" * w for w in widths))
    for row in cells:
        print(line(row))


def write_csv(rows: list[dict], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: 엑셀에서 한글이 안 깨지게
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"CSV 저장: {path} ({len(rows)}행)")


def output(rows: list[dict], args) -> None:
    if getattr(args, "csv", None):
        write_csv(rows, args.csv)
    else:
        print_table(rows)


def _date(s: str) -> date:
    return date.fromisoformat(s)


# ---------------------------------------------------------------- 공용 객체


def _settings(args) -> Settings:
    s = Settings()
    if args.data_dir:
        s.data_dir = Path(args.data_dir)
    if getattr(args, "interval", None) is not None:
        s.request_interval = args.interval
    return s


def _http(settings: Settings):
    from .http import PoliteSession

    return PoliteSession.from_settings(settings)


def _tokenizer(args):
    from .analysis.tokenizer import NounTokenizer

    return NounTokenizer(
        userdict=Path(args.userdict) if getattr(args, "userdict", None) else None,
        stopwords=Path(args.stopwords) if getattr(args, "stopwords", None) else None,
    )


# ---------------------------------------------------------------- 수집 명령


def cmd_init(args, conn, settings):
    print(f"DB 준비 완료: {settings.db_path}")


def cmd_discover(args, conn, settings):
    from .sources import mois_board

    n = mois_board.discover(conn, _http(settings), settings, board=args.board, start=args.start,
                            end=args.end, max_pages=args.max_pages, until_known=args.until_known)
    print(f"신규 발견 {n}건")


def cmd_fetch(args, conn, settings):
    from .sources import mois_board

    ok, fail = mois_board.fetch_details(conn, _http(settings), settings, limit=args.limit,
                                        download=not args.no_download, retry_errors=args.retry_errors)
    print(f"상세 수집 성공 {ok}건, 실패 {fail}건")


def cmd_download(args, conn, settings):
    from .sources import mois_board

    n = mois_board.download_pending(conn, _http(settings), settings, retry_errors=args.retry_errors)
    print(f"첨부 다운로드 시도 {n}건")


def cmd_reparse(args, conn, settings):
    from .sources import mois_board

    print(f"원본 HTML 재파싱 {mois_board.reparse_raw(conn)}건")


def cmd_extract(args, conn, settings):
    from .corpus import extract_attachments

    ok, skipped, failed = extract_attachments(conn, retry_errors=args.retry_errors)
    print(f"첨부 텍스트 추출 {ok}건, 건너뜀(이미지 등) {skipped}건, 실패 {failed}건")


def cmd_build_text(args, conn, settings):
    from .corpus import build_doc_text

    print(f"분석용 텍스트 구성 {build_doc_text(conn, mode=args.mode)}건 (mode={args.mode})")


def cmd_tokenize(args, conn, settings):
    from .analysis.tokenizer import tokenize_corpus

    tok = _tokenizer(args)
    print(f"형태소 분석 {tokenize_corpus(conn, tok, rebuild=args.rebuild)}건 ({tok.version})")


def _try_tokenize(args, conn, settings):
    try:
        import kiwipiepy  # noqa: F401
    except ImportError:
        print("kiwipiepy 미설치 — 형태소 분석은 건너뜀 (pip install -e '.[analysis]')")
        return
    args.rebuild = False
    cmd_tokenize(args, conn, settings)


def cmd_collect(args, conn, settings):
    """처음 한 번: 기간 전체를 목록→상세→첨부→텍스트→형태소까지."""
    args.until_known = False
    args.retry_errors = False
    args.no_download = False
    args.mode = "best"
    cmd_discover(args, conn, settings)
    cmd_fetch(args, conn, settings)
    cmd_extract(args, conn, settings)
    cmd_build_text(args, conn, settings)
    _try_tokenize(args, conn, settings)


def cmd_update(args, conn, settings):
    """매일/매주: 새 글만 받아서 이어 붙인다."""
    args.until_known = True
    args.retry_errors = True
    args.no_download = False
    args.limit = None
    args.mode = "best"
    cmd_discover(args, conn, settings)
    cmd_fetch(args, conn, settings)
    cmd_download(args, conn, settings)  # 지난번에 실패한 첨부 재시도
    cmd_extract(args, conn, settings)
    cmd_build_text(args, conn, settings)
    _try_tokenize(args, conn, settings)


def cmd_kr_api(args, conn, settings):
    from .sources import korea_kr_api

    n = korea_kr_api.collect(conn, _http(settings), args.key, args.start, args.end or date.today(),
                             ministry=args.ministry)
    print(f"정책브리핑 API {args.ministry} 보도자료 {n}건 저장")


# ---------------------------------------------------------------- 점검 명령


def cmd_recon(args, conn, settings):
    """실제 사이트(또는 브라우저로 저장한 HTML 파일)를 파싱해 결과를 보여준다. 파서 검증용."""
    from .http import decode_html
    from .sources import mois_board

    board_id = BOARDS[args.board]
    if args.file:
        html = decode_html(Path(args.file).read_bytes())
    else:
        http = _http(settings)
        if args.what == "list":
            resp = http.get(mois_board.list_url(), params={"bbsId": board_id, "pageIndex": args.page})
        else:
            if not args.ntt_id:
                sys.exit("article 은 nttId 가 필요합니다: moisdb recon article 123456")
            resp = http.get(mois_board.article_url(board_id, args.ntt_id))
        recon_dir = settings.data_dir / "recon"
        recon_dir.mkdir(parents=True, exist_ok=True)
        saved = recon_dir / f"{args.what}_{args.ntt_id or args.page}.html"
        saved.write_bytes(resp.content)
        print(f"원본 저장: {saved}")
        html = decode_html(resp.content, resp.headers.get("Content-Type", ""))

    if args.what == "list":
        items = mois_board.parse_list(html, board_id)
        print_table(mois_board.describe_list(items), ["ntt_id", "date", "department", "pinned", "title"])
        print(f"\n{len(items)}건 파싱. 날짜/부서가 비어 있으면 parse_list() 를 사이트 구조에 맞게 고칠 것.")
    else:
        art = mois_board.parse_article(html)
        print(f"제목      : {art.title}")
        print(f"등록일    : {art.date}")
        print(f"담당부서  : {art.department}")
        print(f"본문 탐지 : {art.body_selector}  ({len(art.body_text)}자)")
        print(f"첨부      : {len(art.attachments)}개")
        for a in art.attachments:
            print(f"  - {a.filename}  <{a.url}>")
        print("\n----- 본문 앞부분 -----")
        print(art.body_text[: args.chars])


def cmd_stats(args, conn, settings):
    print(f"DB: {settings.db_path}\n")
    print("[보도자료 상태]")
    print_table([dict(r) for r in conn.execute(
        "SELECT source, status, count(*) AS n, min(published_date) AS first, max(published_date) AS last "
        "FROM releases GROUP BY source, status ORDER BY source, status")])
    print("\n[첨부 상태·형식]")
    print_table([dict(r) for r in conn.execute(
        "SELECT status, coalesce(file_type, '-') AS file_type, count(*) AS n FROM attachments "
        "GROUP BY status, file_type ORDER BY n DESC")])
    print("\n[분석 텍스트 출처]")
    print_table([dict(r) for r in conn.execute(
        "SELECT text_source, count(*) AS n, cast(avg(char_len) AS int) AS avg_chars FROM doc_text GROUP BY text_source")])
    print("\n[월별 건수 (행안부 누리집)]")
    print_table([dict(r) for r in conn.execute(
        "SELECT substr(published_date, 1, 7) AS month, count(*) AS n FROM releases "
        "WHERE source = 'mois' GROUP BY month ORDER BY month")])


def _norm_title(t: str | None) -> str:
    return re.sub(r"[\W_]+", "", t or "")


def cmd_crosscheck(args, conn, settings):
    """누리집 수집분과 정책브리핑 API 수집분을 (날짜, 제목)으로 맞춰 보고 한쪽에만 있는 글을 보여준다."""
    def keyed(source):
        return {(r["published_date"], _norm_title(r["title"])): r for r in conn.execute(
            "SELECT id, published_date, title FROM releases WHERE source = ?", (source,))}

    mois, kr = keyed("mois"), keyed("korea_kr")
    only_mois = [dict(mois[k]) for k in sorted(mois.keys() - kr.keys(), key=lambda k: k[0] or "")]
    only_kr = [dict(kr[k]) for k in sorted(kr.keys() - mois.keys(), key=lambda k: k[0] or "")]
    print(f"일치 {len(mois.keys() & kr.keys())}건 · 누리집에만 {len(only_mois)}건 · 정책브리핑에만 {len(only_kr)}건\n")
    print("[정책브리핑에만 있는 글 = 누리집 수집 누락 후보]")
    print_table(only_kr[: args.n])


# ---------------------------------------------------------------- 분석 명령


def _corpus(args, conn):
    from .analysis.keywords import load_corpus

    docs = load_corpus(conn, start=args.start and args.start.isoformat(), end=args.end and args.end.isoformat(),
                       department=args.dept)
    if not docs:
        sys.exit("분석할 문서가 없습니다. collect → tokenize 를 먼저 실행하세요.")
    print(f"(대상 보도자료 {len(docs)}건: {docs[0].date} ~ {docs[-1].date})\n", file=sys.stderr)
    return docs


def cmd_search(args, conn, settings):
    q = args.query
    if len(q) >= 3:
        # trigram 색인은 3글자 이상에서만 동작한다
        sql = """SELECT r.id, r.published_date AS date, r.department AS dept, r.title,
                        snippet(doc_fts, 1, '[', ']', '…', 12) AS snippet
                 FROM doc_fts JOIN releases r ON r.id = doc_fts.rowid
                 WHERE doc_fts MATCH ? ORDER BY r.published_date DESC LIMIT ?"""
        params = ('"' + q.replace('"', '""') + '"', args.limit)
    else:
        sql = """SELECT r.id, r.published_date AS date, r.department AS dept, r.title,
                        substr(d.text, max(instr(d.text, ?) - 30, 1), 80) AS snippet
                 FROM doc_text d JOIN releases r ON r.id = d.release_id
                 WHERE d.text LIKE ? ORDER BY r.published_date DESC LIMIT ?"""
        params = (q, f"%{q}%", args.limit)
    rows = [dict(r) for r in conn.execute(sql, params)]
    for r in rows:
        r["snippet"] = re.sub(r"\s+", " ", r["snippet"] or "")
    output(rows, args)


def cmd_top(args, conn, settings):
    from .analysis.keywords import top_terms

    output(top_terms(_corpus(args, conn), n=args.n), args)


def cmd_trend(args, conn, settings):
    from .analysis.keywords import term_trend

    output(term_trend(_corpus(args, conn), args.terms, freq=args.freq), args)


def cmd_distinctive(args, conn, settings):
    from .analysis.keywords import distinctive_by_period

    output(distinctive_by_period(_corpus(args, conn), freq=args.freq, n=args.n, min_df=args.min_df), args)


def cmd_cooccur(args, conn, settings):
    from .analysis.keywords import cooccurring

    output(cooccurring(_corpus(args, conn), args.term, n=args.n), args)


def cmd_export(args, conn, settings):
    sql = """SELECT r.id, r.source, r.source_id, r.published_date, r.department, r.title, r.url,
                    d.text_source, d.text, t.tokens
             FROM releases r JOIN doc_text d ON d.release_id = r.id
             LEFT JOIN doc_tokens t ON t.release_id = r.id
             WHERE r.source = ? AND (? IS NULL OR r.published_date >= ?) AND (? IS NULL OR r.published_date <= ?)
             ORDER BY r.published_date, r.id"""
    s = args.start.isoformat() if args.start else None
    e = args.end.isoformat() if args.end else None
    rows = [dict(r) for r in conn.execute(sql, (args.source, s, s, e, e))]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "jsonl":
        with out.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"JSONL 저장: {out} ({len(rows)}건)")
    else:
        write_csv(rows, str(out))


# ---------------------------------------------------------------- 인자 정의


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="moisdb", description="행정안전부 보도자료 수집·DB화·키워드 분석")
    p.add_argument("--data-dir", help="데이터 폴더 (기본: ./data 또는 MOISDB_DATA_DIR)")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, func, help_):
        sp = sub.add_parser(name, help=help_, description=help_)
        sp.set_defaults(func=func)
        return sp

    def period(sp, default_start=None):
        sp.add_argument("--start", type=_date, default=default_start, help="시작일 YYYY-MM-DD")
        sp.add_argument("--end", type=_date, default=None, help="종료일 YYYY-MM-DD")

    def crawl(sp):
        sp.add_argument("--interval", type=float, help="요청 간격(초), 기본 1.5")

    def tok(sp):
        sp.add_argument("--userdict", help="사용자 사전 파일 (기본: 내장 resources/userdict.txt)")
        sp.add_argument("--stopwords", help="불용어 파일 (기본: 내장 resources/stopwords.txt)")

    def analysis(sp):
        period(sp)
        sp.add_argument("--dept", help="담당부서 이름 일부로 필터")
        sp.add_argument("--csv", help="결과를 CSV 로 저장할 경로")

    add("init", cmd_init, "DB 파일 생성")

    for name, func, help_ in (
        ("discover", cmd_discover, "목록 페이지를 넘기며 기간 내 보도자료를 등록"),
        ("collect", cmd_collect, "최초 전체 수집: discover → fetch → extract → build-text → tokenize"),
        ("update", cmd_update, "증분 수집: 새 글만 받아 전 단계 실행 (정기 실행용)"),
    ):
        sp = add(name, func, help_)
        period(sp, START_DATE)
        crawl(sp)
        sp.add_argument("--board", default="press", choices=list(BOARDS))
        sp.add_argument("--max-pages", type=int, default=1000)
        if name == "discover":
            sp.add_argument("--until-known", action="store_true", help="새 글이 없는 페이지에서 멈춤")
        if name == "collect":
            sp.add_argument("--limit", type=int, help="상세 수집 최대 건수 (시험용)")
        if name != "discover":
            tok(sp)

    sp = add("fetch", cmd_fetch, "등록된 글의 상세 페이지·첨부파일 수집")
    crawl(sp)
    sp.add_argument("--limit", type=int, help="최대 건수 (시험용)")
    sp.add_argument("--no-download", action="store_true", help="첨부파일은 받지 않음")
    sp.add_argument("--retry-errors", action="store_true", help="실패했던 글도 다시 시도")

    sp = add("download", cmd_download, "아직 받지 않은 첨부파일 다운로드")
    crawl(sp)
    sp.add_argument("--retry-errors", action="store_true")

    add("reparse", cmd_reparse, "저장된 원본 HTML 을 다시 파싱 (네트워크 사용 안 함)")

    sp = add("extract", cmd_extract, "첨부파일(HWP/HWPX/PDF/DOCX)에서 텍스트 추출")
    sp.add_argument("--retry-errors", action="store_true")

    sp = add("build-text", cmd_build_text, "본문·첨부 중 분석용 텍스트를 골라 정제하고 검색 색인 갱신")
    sp.add_argument("--mode", choices=["best", "body", "attachments"], default="best")

    sp = add("tokenize", cmd_tokenize, "형태소 분석(명사 추출)")
    tok(sp)
    sp.add_argument("--rebuild", action="store_true", help="전체 재분석")

    sp = add("recon", cmd_recon, "파서 점검: 실제 페이지(또는 저장한 HTML)를 파싱한 결과 출력")
    sp.add_argument("what", choices=["list", "article"])
    sp.add_argument("ntt_id", nargs="?", help="article 일 때 nttId")
    sp.add_argument("--page", type=int, default=1)
    sp.add_argument("--file", help="브라우저에서 저장한 HTML 파일을 파싱 (네트워크 사용 안 함)")
    sp.add_argument("--board", default="press", choices=list(BOARDS))
    sp.add_argument("--chars", type=int, default=800, help="본문 미리보기 글자 수")
    crawl(sp)

    add("stats", cmd_stats, "수집 현황")

    sp = add("crosscheck", cmd_crosscheck, "누리집 vs 정책브리핑 API 수집분 비교 (누락 점검)")
    sp.add_argument("-n", type=int, default=50)

    sp = add("kr-api", cmd_kr_api, "정책브리핑 보도자료 OpenAPI 로 수집 (보조·교차검증)")
    sp.add_argument("--key", required=True, help="data.go.kr 인증키 (Decoding 키)")
    sp.add_argument("--ministry", default="행정안전부")
    period(sp, START_DATE)
    crawl(sp)

    sp = add("search", cmd_search, "전문 검색")
    sp.add_argument("query")
    sp.add_argument("--limit", type=int, default=30)
    sp.add_argument("--csv")

    sp = add("top", cmd_top, "상위 키워드 (문서 빈도 기준)")
    analysis(sp)
    sp.add_argument("-n", type=int, default=50)

    sp = add("trend", cmd_trend, "키워드별 기간 추이 (그 기간 보도자료 중 언급 비율)")
    sp.add_argument("terms", nargs="+")
    sp.add_argument("--freq", choices=["week", "month", "quarter"], default="month")
    analysis(sp)

    sp = add("distinctive", cmd_distinctive, "기간별 특징어 (그 기간에 유독 많이 나온 단어)")
    sp.add_argument("--freq", choices=["week", "month", "quarter"], default="month")
    sp.add_argument("-n", type=int, default=15)
    sp.add_argument("--min-df", type=int, default=2)
    analysis(sp)

    sp = add("cooccur", cmd_cooccur, "연관어 (같은 보도자료에 함께 나온 단어)")
    sp.add_argument("term")
    sp.add_argument("-n", type=int, default=30)
    analysis(sp)

    sp = add("export", cmd_export, "보도자료+정제 텍스트+토큰 내보내기 (CSV/JSONL)")
    sp.add_argument("--format", choices=["csv", "jsonl"], default="csv")
    sp.add_argument("--out", default="data/export/mois_press.csv")
    sp.add_argument("--source", default="mois")
    period(sp)

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    settings = _settings(args)
    conn = db.connect(settings.db_path)
    try:
        args.func(args, conn, settings)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
