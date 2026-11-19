"""Fetch KOSPI data from Naver Securities' public mobile JSON (a redistribution of KRX quotes; secondary source).
Writes into the folder given as argv[1]: list_p*.json (all KOSPI listings, latest session), index_p*.json (KOSPI daily),
hist_<code>.json (daily prices for the largest stocks), ind_<code>.json (industry info)."""
import json, os, sys, time, urllib.request
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
def get(url, fn, tries=4):
    p = os.path.join(out, fn)
    if os.path.exists(p) and os.path.getsize(p) > 50: return json.load(open(p))
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=30).read()
            open(p, "wb").write(data); time.sleep(.15); return json.loads(data)
        except Exception as e:
            time.sleep(2 * (i + 1)); err = e
    print("FAIL", url, err); return None
stocks = []
for pg in range(1, 30):
    d = get(f"https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page={pg}&pageSize=100", f"list_p{pg}.json")
    if not d or not d["stocks"]: break
    stocks += d["stocks"]
eq = [s for s in stocks if s.get("stockEndType") == "stock"]
print("listings", len(stocks), "stocks", len(eq))
for pg in range(1, 15):
    d = get(f"https://m.stock.naver.com/api/index/KOSPI/price?pageSize=60&page={pg}", f"index_p{pg}.json")
    if not d: break
    if d[-1]["localTradedAt"] < "2023-12-01": break
eq.sort(key=lambda s: -float(s["marketValueRaw"]) if s.get("marketValueRaw") else 0)
for s in eq[:60]:
    c = s["itemCode"]
    for pg in range(1, 7):
        d = get(f"https://m.stock.naver.com/api/stock/{c}/price?pageSize=60&page={pg}", f"hist_{c}_p{pg}.json")
        if not d or d[-1]["localTradedAt"] < "2025-12-01": break
for s in eq:
    get(f"https://m.stock.naver.com/api/stock/{s['itemCode']}/integration", f"ind_{s['itemCode']}.json")
print("done")
