"""공유 페이지에 올릴 데이터 파일(docs.b64.txt, cloud.b64.txt)을 풀어서 내용을 요약·점검한다.

    python3 ci/check_web_data.py build/latest/web

데이터는 base64(gzip(JSON)) 라 그대로는 읽을 수 없으므로, 올리기 전에 이 요약으로
건수·기간·최근 제목·이상 여부를 확인한다. 문제가 있으면 종료 코드 1.
"""
import base64
import gzip
import json
import re
import sys
from pathlib import Path

SUSPICIOUS = re.compile(r"<\s*(script|iframe|object|embed)\b|javascript:", re.I)


def load(path: Path):
    return json.loads(gzip.decompress(base64.b64decode(path.read_text())))


def main(web_dir: str) -> int:
    web = Path(web_dir)
    docs = load(web / "docs.b64.txt")
    cloud = load(web / "cloud.b64.txt")
    problems = []

    rows = docs["docs"]
    dates = sorted(r[1] for r in rows)
    print(f"docs.b64.txt  : {len(rows)}건, {dates[0]} ~ {dates[-1]}, 생성 {docs['built']}")
    print(f"cloud.b64.txt : 문서 {len(cloud['docs'])}건, 단어 {len(cloud['terms'])}개, 부서 {len(cloud['depts'])}개")

    ids = [r[0] for r in rows]
    if len(set(ids)) != len(ids):
        problems.append("docs 에 중복 id")
    if set(ids) != {r[0] for r in cloud["docs"]}:
        problems.append("docs 와 cloud 의 문서 목록이 다름")
    empty = [r[0] for r in rows if not r[3] or not r[4].strip()]
    if empty:
        problems.append(f"제목/본문 빈 문서 {len(empty)}건: {empty[:5]}")
    bad = [r[0] for r in rows if any(SUSPICIOUS.search(x) for x in r[2:] if isinstance(x, str))]
    if bad:
        problems.append(f"스크립트로 보이는 문자열이 든 문서 {len(bad)}건: {bad[:5]}")

    print("\n최근 보도자료:")
    for r in sorted(rows, key=lambda r: (r[1], r[0]), reverse=True)[:10]:
        print(f"  {r[1]}  {r[2]:<12}  {r[3][:60]}  (본문 {len(r[4]):,}자)")

    repo_page = Path(__file__).resolve().parent.parent / "web" / "index.html"
    built_page = web / "index.html"
    if built_page.exists() and built_page.read_bytes() != repo_page.read_bytes():
        problems.append("Actions 가 만든 index.html 이 저장소 web/index.html 과 다름 (저장소 쪽을 올릴 것)")

    print()
    if problems:
        print("점검 결과: 문제 있음")
        for p in problems:
            print(" -", p)
        return 1
    print("점검 결과: 이상 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "build/latest/web"))
