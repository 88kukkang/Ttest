"""Current pump prices of every filling station, sigungu by sigungu, from Opinet's 지역별 주유소 page."""
import json, re, subprocess, time, sys
from concurrent.futures import ThreadPoolExecutor
from parse import parse

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
SIDO = ["서울특별시", "부산광역시", "대구광역시", "인천광역시", "전남광주통합특별시", "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도", "충청북도", "충청남도", "전북특별자치도", "경상북도", "경상남도", "제주특별자치도"]


def post(sido, sgg=""):
    args = ["curl", "-sS", "--max-time", "60", "-A", UA, "-c", "cj.txt", "-b", "cj.txt", "-e", "https://www.opinet.co.kr/searRgSelect.do",
            "--data-urlencode", f"SIDO_NM={sido}", "--data-urlencode", f"SIGUNGU_NM={sgg}", "--data-urlencode", f"SIDO_NM0={sido}", "--data-urlencode", f"SIGUNGU_NM0={sgg}",
            "--data", "BTN_DIV=os_btn&POLL_ALL=all", "https://www.opinet.co.kr/searRgSelect.do"]
    for i in range(6):
        r = subprocess.run(args, capture_output=True)
        t = r.stdout.decode("utf-8", "ignore")
        if len(t) > 50000: return t
        time.sleep(2 + i * 2)
    raise SystemExit(f"fail {sido} {sgg}")


def sggs(sido):
    t = post(sido)
    m = re.search(r'<select[^>]*id="SIGUNGU_NM0".*?</select>', t, re.S)
    return sido, [v for v in re.findall(r'value="([^"]+)"', m.group(0))]


with ThreadPoolExecutor(4) as ex:
    S = dict(ex.map(sggs, SIDO))
print({k: len(v) for k, v in S.items()}, flush=True)
jobs = [(a, b) for a, L in S.items() for b in L]
rows = {}
def one(j):
    a, b = j
    return a, b, parse(post(a, b))
with ThreadPoolExecutor(4) as ex:
    for a, b, R in ex.map(one, jobs):
        for r in R:
            r["sido"], r["sgg"] = a, b
            rows[r["id"]] = r
json.dump({"fetched": time.strftime("%Y-%m-%d %H:%M"), "sgg": S, "rows": list(rows.values())}, open("stations.json", "w"), ensure_ascii=False)
print("stations", len(rows))
