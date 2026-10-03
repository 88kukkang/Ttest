"""웹 페이지(web/search.html, web/cloud.html)가 읽는 데이터 파일을 만든다.

    python ci/build_web_data.py [출력폴더]   # 기본: web/

docs.b64.txt   검색용: 보도자료별 등록일·부서·제목·분석용 텍스트
cloud.b64.txt  클라우드용: 단어 목록(2건 이상 나온 단어)과 보도자료별 단어 번호

둘 다 JSON → gzip → base64. 아티팩트 호스팅이 .gz 파일을 내주지 않아 base64 텍스트로 싣는다.
"""

import base64
import gzip
import json
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "web")
out_dir.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect("data/mois.sqlite3")
ORDER = "ORDER BY r.published_date DESC, cast(r.source_id AS integer) DESC"


def write(name: str, payload: dict) -> None:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    packed = base64.b64encode(gzip.compress(raw, compresslevel=9, mtime=0))
    (out_dir / name).write_bytes(packed)
    print(f"{out_dir / name} ({len(packed) / 1e6:.1f} MB)")


rows = conn.execute(
    f"""SELECT r.source_id, r.published_date, coalesce(r.department, ''), coalesce(r.title, ''), d.text
        FROM releases r JOIN doc_text d ON d.release_id = r.id WHERE r.source = 'mois' {ORDER}"""
).fetchall()
write("docs.b64.txt", {"v": 1, "built": date.today().isoformat(), "docs": [list(r) for r in rows]})

rows = conn.execute(
    f"""SELECT r.source_id, r.published_date, coalesce(r.department, ''), coalesce(r.title, ''), t.tokens
        FROM releases r JOIN doc_tokens t ON t.release_id = r.id WHERE r.source = 'mois' {ORDER}"""
).fetchall()
sets = [set(r[4].split()) for r in rows]
df = Counter(t for s in sets for t in s)
terms = [t for t, n in sorted(df.items(), key=lambda x: (-x[1], x[0])) if n >= 2]  # 동률은 가나다순 (실행마다 같은 결과)
term_idx = {t: i for i, t in enumerate(terms)}
dept_n = Counter(r[2] for r in rows)
depts = [d for d, _ in sorted(dept_n.items(), key=lambda x: (-x[1], x[0]))]
dept_idx = {d: i for i, d in enumerate(depts)}
docs = [[r[0], r[1], dept_idx[r[2]], r[3], sorted(term_idx[t] for t in s if t in term_idx)] for r, s in zip(rows, sets)]
write("cloud.b64.txt", {"v": 1, "built": date.today().isoformat(), "terms": terms, "depts": depts, "docs": docs})
