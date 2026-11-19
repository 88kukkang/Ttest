"""KEPCO household average electricity use by sido, monthly 2013-2026, fetched half a year at a time (the endpoint returns 10 rows)."""
import json, subprocess, time
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
subprocess.run(["curl", "-sS", "--max-time", "30", "-A", UA, "-c", "kj.txt", "-b", "kj.txt", "https://bigdata.kepco.co.kr/cmsmain.do?scode=S01&pcode=000171&pstate=L&redirect=Y", "-o", "/dev/null"])


def q(code, y, m0, m1):
    data = f"scode=S01&pcode=000171&pstate=X3&searchLglSiDo={code}&searchGuGun=%EC%A0%84%EC%B2%B4&sdateYear={y}&sdateMonth={m0:02d}&edateYear={y}&edateMonth={m1:02d}"
    for i in range(6):
        r = subprocess.run(["curl", "-sS", "--max-time", "40", "-A", UA, "-b", "kj.txt", "-H", "X-Requested-With: XMLHttpRequest", "--data", data, "https://bigdata.kepco.co.kr/cmsajax.do"], capture_output=True, text=True)
        try:
            return json.loads(r.stdout).get("rows") or []
        except Exception:
            time.sleep(1 + i)
    return None


# find the sido codes that answer
cands = [11, 12, 26, 27, 28, 29, 30, 31, 36, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52]
with ThreadPoolExecutor(6) as ex:
    probe = dict(zip(cands, ex.map(lambda c: q(c, 2024, 1, 2), cands)))
codes = {c: r[0]["sido"] for c, r in probe.items() if r}
print(codes, flush=True)
jobs = [(c, y, a, b) for c in codes for y in range(2013, 2027) for a, b in ((1, 6), (7, 12))]
out = {}
with ThreadPoolExecutor(6) as ex:
    for (c, y, a, b), rows in zip(jobs, ex.map(lambda j: q(*j), jobs)):
        if rows is None: print("fail", c, y, a)
        for r in rows or []:
            out.setdefault(codes[c], {})[r["yyyymm"]] = [r["hosu"], r["kwh"], r["amt"]]
json.dump(out, open("kepco_sido.json", "w"), ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
