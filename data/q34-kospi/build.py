"""Build q34_data.json from the Naver Securities JSON files (secondary source; KRX quotes) in the folder argv[1].
Outputs: stocks (KOSPI common/preferred shares on 2026-11-06: name, code, market cap, daily change, industry), KOSPI daily closes,
and for the 60 largest stocks the closing price on 2025-12-30 and 2026-06-22 (peak)."""
import json, glob, os, sys
R = sys.argv[1]; H = os.path.dirname(os.path.abspath(__file__))
num = lambda x: float(str(x).replace(",", ""))
S = []
for f in sorted(glob.glob(f"{R}/list_p*.json"), key=lambda x: int(os.path.basename(x)[6:-5])): S += json.load(open(f))["stocks"]
eq = [s for s in S if s["stockEndType"] == "stock"]
ind = {g["no"]: g["name"] for g in json.load(open(f"{R}/industries.json"))["groups"]}
I = []
for f in glob.glob(f"{R}/index_p*.json"): I += json.load(open(f))
I = sorted({x["localTradedAt"]: (num(x["closePrice"]), num(x["lowPrice"]), num(x["highPrice"])) for x in I}.items())
hist = {}
for f in glob.glob(f"{R}/hist_*_p*.json"):
    c = os.path.basename(f).split("_")[1]
    for x in json.load(open(f)): hist.setdefault(c, {})[x["localTradedAt"]] = num(x["closePrice"])
stocks = []
for s in eq:
    c = s["itemCode"]; fn = f"{R}/ind_{c}.json"; ic = None
    if os.path.exists(fn):
        try: ic = json.load(open(fn)).get("industryCode")
        except Exception: pass
    h = hist.get(c, {})
    stocks.append([s["stockName"], c, round(num(s["marketValueRaw"]) / 1e8), num(s["fluctuationsRatio"]), ind.get(int(ic)) if ic else None, num(s["closePrice"]), h.get("2025-12-30"), h.get("2026-06-22")])
out = {"asof": eq[0]["localTradedAt"][:10], "stocks": stocks, "idx": {"d": [d for d, _ in I], "c": [v[0] for _, v in I]}, "last": {"d": I[-1][0], "low": I[-1][1][1], "high": I[-1][1][2]}}
json.dump(out, open(os.path.join(H, "q34_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", len(stocks), sum(1 for s in stocks if s[4]), os.path.getsize(os.path.join(H, "q34_data.json")))
