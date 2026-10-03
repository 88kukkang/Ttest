"""검색 페이지(web/search.html)가 읽는 데이터 파일 docs.b64.txt 를 만든다.

data/mois.sqlite3 의 분석용 텍스트(doc_text)를 JSON → gzip → base64 로 적는다.
(아티팩트 호스팅이 .gz 파일을 내주지 않아 base64 텍스트로 싣는다.)

    python ci/build_search_data.py [출력폴더]   # 기본: web/
"""

import base64
import gzip
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "web")
out_dir.mkdir(parents=True, exist_ok=True)
conn = sqlite3.connect("data/mois.sqlite3")
rows = conn.execute(
    """SELECT r.source_id, r.published_date, coalesce(r.department, ''), coalesce(r.title, ''), d.text
       FROM releases r JOIN doc_text d ON d.release_id = r.id
       WHERE r.source = 'mois'
       ORDER BY r.published_date DESC, cast(r.source_id AS integer) DESC"""
).fetchall()
payload = {"v": 1, "built": date.today().isoformat(), "docs": [list(r) for r in rows]}
raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
packed = base64.b64encode(gzip.compress(raw, compresslevel=9))
(out_dir / "docs.b64.txt").write_bytes(packed)
print(f"{len(rows)}건 → {out_dir / 'docs.b64.txt'} ({len(packed) / 1e6:.1f} MB)")
