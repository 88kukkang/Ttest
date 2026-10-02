"""수집 결과(data/mois.sqlite3)를 저장소에 올릴 수 있는 크기로 내보낸다.

dataset/mois_press.sqlite3.xz  분석용 DB (본문 HTML·검색 색인 제외 — `moisdb build-text` 로 색인 재생성)
dataset/mois_press.csv         보도자료 1건 = 1행 (엑셀용, 45MB 넘으면 .csv.gz)
dataset/attachments.csv        첨부파일 목록과 처리 상태
"""

import csv
import gzip
import sqlite3
import subprocess
from pathlib import Path

SRC = Path("data/mois.sqlite3")
OUT = Path("dataset")
OUT.mkdir(exist_ok=True)

slim = OUT / "mois_press.sqlite3"
for old in (slim, OUT / "mois_press.sqlite3.xz"):
    old.unlink(missing_ok=True)
src = sqlite3.connect(SRC)
src.execute("VACUUM INTO ?", (str(slim),))
src.close()
db = sqlite3.connect(slim)
db.execute("DROP TABLE IF EXISTS doc_fts")
db.execute("UPDATE releases SET body_html = NULL")
db.commit()
db.execute("VACUUM")
db.close()
subprocess.run(["xz", "-T0", "-9", "-f", str(slim)], check=True)

db = sqlite3.connect(SRC)
rows = db.execute(
    """SELECT r.id, r.source_id AS ntt_id, r.published_date, r.department, r.title, r.url,
              d.text_source, d.char_len, d.text
       FROM releases r LEFT JOIN doc_text d ON d.release_id = r.id
       WHERE r.source = 'mois' ORDER BY r.published_date, r.id"""
)
header = [c[0] for c in rows.description]
csv_path = OUT / "mois_press.csv"
with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(header)
    w.writerows(rows)
if csv_path.stat().st_size > 45 * 1024 * 1024:
    with csv_path.open("rb") as f, gzip.open(OUT / "mois_press.csv.gz", "wb") as g:
        g.write(f.read())
    csv_path.unlink()

att = db.execute(
    """SELECT a.release_id, r.source_id AS ntt_id, a.seq, a.filename, a.file_type, a.size, a.status, a.error, a.url,
              length(a.text) AS text_len
       FROM attachments a JOIN releases r ON r.id = a.release_id ORDER BY a.release_id, a.seq"""
)
with (OUT / "attachments.csv").open("w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow([c[0] for c in att.description])
    w.writerows(att)

left = db.execute("SELECT count(*) FROM releases WHERE source = 'mois' AND status != 'fetched'").fetchone()[0]
print(f"내보내기 완료. 상세 미수집(listed/error) {left}건")
for p in sorted(OUT.iterdir()):
    print(f"  {p}  {p.stat().st_size / 1024 / 1024:.1f} MB")
