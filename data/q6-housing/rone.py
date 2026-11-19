"""Fetch a whole R-ONE monthly table through the keyless OpenAPI (5 rows per call), month by month.
usage: python3 rone.py STATBL_ID START(YYYYMM) END(YYYYMM) OUT.json [cycle]"""
import json, subprocess, sys, time, os
from concurrent.futures import ThreadPoolExecutor

tbl, start, end, out = sys.argv[1:5]
cyc = sys.argv[5] if len(sys.argv) > 5 else "MM"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def months(a, b):
    y, m = int(a[:4]), int(a[4:])
    while f"{y}{m:02d}" <= b:
        yield f"{y}{m:02d}"
        m += 1
        if m > 12:
            y, m = y + 1, 1


def call(t, page):
    url = f"https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do?Type=json&pIndex={page}&pSize=5&STATBL_ID={tbl}&DTACYCLE_CD={cyc}&WRTTIME_IDTFR_ID={t}"
    for i in range(8):
        r = subprocess.run(["curl", "-sS", "--max-time", "40", "-A", UA, url], capture_output=True, text=True)
        try:
            d = json.loads(r.stdout)["SttsApiTblData"]
            return d[0]["head"][0]["list_total_count"], d[1]["row"]
        except Exception:
            if '"INFO-200"' in r.stdout:  # no data
                return 0, []
            time.sleep(1 + i)
    raise SystemExit(f"failed {t} {page}: {r.stdout[:200]} {r.stderr[:200]}")


def month(t):
    total, rows = call(t, 1)
    for pg in range(2, (total + 4) // 5 + 1):
        rows += call(t, pg)[1]
    return t, rows


res = {}
with ThreadPoolExecutor(8) as ex:
    for t, rows in ex.map(month, list(months(start, end))):
        res[t] = rows
        print(t, len(rows), flush=True) if t.endswith("01") else None
json.dump(res, open(out, "w"), ensure_ascii=False)
print("done", sum(len(v) for v in res.values()))
