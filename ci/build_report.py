"""분석 보고서 데이터(reports/report_data.json)를 DB 에서 만든다. 웹 페이지 '분석 보고서' 탭이 이 파일을 쓴다.

    python ci/build_report.py [DB 경로]          # 기본 data/mois.sqlite3
    python ci/build_hub.py                       # 페이지에 넣기

수집한 전체 기간을 다루고, 이재명 정부 출범일(GOV_START) 앞뒤를 견준다.
보고서의 요약 문장(web/src/2_body.html 의 분석 보고서 부분)은 이 결과를 보고 사람이 쓴다.
주제(TOPICS)도 사람이 고른 목록이다. 기간을 넓히면 새로 두드러진 이슈를 보고 손본다.
"""

import collections
import json
import sys
from pathlib import Path

from moisdb import db
from moisdb.analysis.keywords import Doc, distinctive_by_period, distinctive_terms, load_corpus, period_of, top_terms
from moisdb.config import GOV_START

OUT = Path("reports/report_data.json")
SHIFT = ["지방정부", "지방자치단체", "지자체"]  # 표기 변화: 보도자료에 한 번이라도 나온 비율
TOPICS = [  # (이름, 이 가운데 하나라도 나오면 그 주제로 센다). 2024-01~2026-10 의 월별 특징어를 보고 고름
    ("디지털플랫폼정부", ["디지털플랫폼정부"]),
    ("인공지능·AI", ["인공지능", "AI"]),
    ("지역사랑상품권", ["지역사랑상품권"]),
    ("민생회복 소비쿠폰", ["소비쿠폰"]),
    ("유가·피해지원금", ["유가", "피해지원금"]),
    ("의료 공백·비상진료", ["비상진료", "비상진료체계", "전공의"]),
    ("제주항공 여객기 사고", ["제주항공", "여객기"]),
    ("국가정보자원관리원", ["국가정보자원관리원", "국정자원"]),
    ("산불", ["산불"]),
    ("호우", ["호우"]),
    ("폭염", ["폭염"]),
    ("한파·대설", ["한파", "대설"]),
    ("선거", ["지방선거", "국회의원선거", "총선", "대통령선거", "대선"]),
    ("통합특별시", ["통합특별시", "전남광주통합특별시"]),
    ("주민자치", ["주민자치", "주민자치회"]),
]
# 보고서 단어 비교에서 뺄 말. 사람 이름은 누가 그 자리에 있었는지를 보여줄 뿐 정책 변화가 아니고,
# 2024년 보도자료 서식의 머리말(개요·주요내용 등)은 내용이 아니라 서식이 바뀐 흔적이다.
# 이름은 '이름 + 직함' 꼴로 자주 나오는 말을 뽑아 사람이 확인했다 (형태소 분석기가 자른 조각 포함: 이한·김광·병권·박형)
PEOPLE = {
    "이상민", "고기동", "이한경", "이한", "한순기", "김광용", "김광", "김민재", "윤호중", "최병관", "이용석",
    "오병권", "병권", "황규철", "진명기", "이병철", "임상규", "여중협", "안채명", "임철언", "박형배", "박형",
    "최상목", "한덕수", "이주호",
    "이재명", "윤석열", "문재인", "박근혜", "이명박", "노무현", "김대중", "김영삼", "노태우", "전두환", "박정희",
}
FORMAT_WORDS = {"개요", "주요내용", "추진배경", "배경", "향후계획", "참석대상"}
EXCLUDE = PEOPLE | FORMAT_WORDS


def build(path: str) -> dict:
    conn = db.connect(path)
    docs = [Doc(d.id, d.date, d.department, d.title, [t for t in d.tokens if t not in EXCLUDE]) for d in load_corpus(conn)]
    gov = GOV_START.isoformat()
    months = sorted({period_of(d.date) for d in docs})
    by_m = collections.defaultdict(list)
    for d in docs:
        by_m[period_of(d.date)].append(d)

    def share(group):
        out = []
        for m in months:
            g = by_m[m]
            k = sum(1 for d in g if any(t in d.vocab for t in group))
            out.append({"m": m, "k": k, "n": len(g), "s": round(k / len(g), 4)})
        return out

    dist_by = collections.defaultdict(list)
    for r in distinctive_by_period(docs, "month", n=10, min_df=3):
        dist_by[r["period"]].append({"t": r["term"], "df": r["df"], "z": r["z"]})
    pre = [d for d in docs if d.date < gov]
    post = [d for d in docs if d.date >= gov]
    dept_rows = conn.execute(
        "SELECT department, count(*) FROM releases WHERE source = 'mois' AND status = 'fetched' GROUP BY department ORDER BY 2 DESC LIMIT 15"
    ).fetchall()
    return {
        "n_docs": len(docs),
        "first": docs[0].date,
        "last": docs[-1].date,
        "gov_start": gov,
        "n_depts": conn.execute("SELECT count(DISTINCT department) FROM releases WHERE source = 'mois' AND status = 'fetched'").fetchone()[0],
        "attachments": {r[0]: r[1] for r in conn.execute("SELECT file_type, count(*) FROM attachments WHERE status = 'extracted' GROUP BY file_type")},
        "pre_n": len(pre),
        "post_n": len(post),
        "monthly_counts": [{"m": m, "n": len(by_m[m])} for m in months],
        "distinctive": dist_by,
        "term_shift": {t: share([t]) for t in SHIFT},
        "topics": [{"name": n, "terms": g, "series": share(g), "total": sum(1 for d in docs if any(t in d.vocab for t in g))} for n, g in TOPICS],
        "top": top_terms(docs, n=30),
        "rising": distinctive_terms(post, pre, n=15, min_df=8),   # 출범 뒤에 늘어난 말 (df=출범 후, ref_df=출범 전)
        "falling": distinctive_terms(pre, post, n=15, min_df=8),  # 출범 전에 많았던 말 (df=출범 전, ref_df=출범 후)
        "departments": [{"d": d or "부서 미상", "n": n} for d, n in dept_rows],
    }


if __name__ == "__main__":
    data = build(sys.argv[1] if len(sys.argv) > 1 else "data/mois.sqlite3")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print(f"{OUT}: {data['n_docs']}건 ({data['first']} ~ {data['last']}), 출범 전 {data['pre_n']} / 후 {data['post_n']}")
