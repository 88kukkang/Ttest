"""Build q51_data.json (nationality loss and acquisition, 2011-2025) from the Ministry of Justice CSVs in this folder.
moj_15100048 loss by type, moj_15100049 loss by type x new nationality, moj_15100046 acquisition by type (applied/granted),
moj_15100047 acquisition by type x former nationality, moj_3045189 all nationality decisions by year (to 2024).
The CSVs were converted from CP949 to UTF-8."""
import csv, json, os, collections
H = os.path.dirname(os.path.abspath(__file__))
rd = lambda f: list(csv.DictReader(open(os.path.join(H, f), encoding="utf-8")))
n = lambda s: int(s.replace(",", ""))
L, LC, G, GC, T = rd("moj_15100048.csv"), rd("moj_15100049.csv"), rd("moj_15100046.csv"), rd("moj_15100047.csv"), rd("moj_3045189.csv")
Y = list(range(2011, 2026))
out = {"y": Y}
lo = {(x["년"], x["유형"]): n(x["건수"]) for x in L}
ga = {(x["년"], x["귀화국적회복"], x["신청허가"]): n(x["건수"]) for x in G}
out["loss"] = [lo[(str(y), "상실")] for y in Y]; out["renounce"] = [lo[(str(y), "이탈")] for y in Y]
out["nat"] = [ga[(str(y), "귀화", "허가")] for y in Y]; out["rest"] = [ga[(str(y), "국적회복", "허가")] for y in Y]
out["natApp"] = [ga[(str(y), "귀화", "신청")] for y in Y]; out["restApp"] = [ga[(str(y), "국적회복", "신청")] for y in Y]
tt = {x["연도"]: x for x in T}
out["choose"] = [n(tt[str(y)]["국적선택"]) if str(y) in tt else None for y in Y]
# loss by new nationality (상실+이탈)
lc = collections.defaultdict(collections.Counter); lct = collections.defaultdict(collections.Counter)
for x in LC: lc[int(x["년"])][x["국적지역"]] += n(x["건수"]); lct[(int(x["년"]), x["유형"])][x["국적지역"]] += n(x["건수"])
tot15 = collections.Counter(); [tot15.update(lc[y]) for y in Y]
TOPC = [c for c, _ in tot15.most_common(10)]
out["dest"] = {"c": TOPC, "v": [[lc[y][c] for c in TOPC] + [sum(lc[y].values()) - sum(lc[y][c] for c in TOPC)] for y in Y],
               "loss": [[lct[(y, "상실")][c] for c in TOPC] for y in Y], "ren": [[lct[(y, "이탈")][c] for c in TOPC] for y in Y],
               "tot": [sum(lc[y].values()) for y in Y], "n": [len(lc[y]) for y in Y]}
out["dest15"] = {c: tot15[c] for c in TOPC}; out["dest15"]["합계"] = sum(tot15.values())
# restoration and naturalization by former nationality
gc = collections.defaultdict(collections.Counter)
for x in GC: gc[(int(x["년"]), x["유형"])][x["국적"]] += n(x["건수"])
rtot = collections.Counter(); [rtot.update(gc[(y, "국적회복")]) for y in Y]
RC = [c for c, _ in rtot.most_common(6)]
out["restBy"] = {"c": RC, "v": [[gc[(y, "국적회복")][c] for c in RC] for y in Y], "tot": [sum(gc[(y, "국적회복")].values()) for y in Y]}
ntot = collections.Counter(); [ntot.update(gc[(y, "귀화")]) for y in Y]
NC = [c for c, _ in ntot.most_common(6)]
out["natBy"] = {"c": NC, "v": [[gc[(y, "귀화")][c] for c in NC] for y in Y], "tot": [sum(gc[(y, "귀화")].values()) for y in Y]}
out["usLost15"] = tot15["미국"]; out["usBack15"] = rtot["미국"]
json.dump(out, open(os.path.join(H, "q51_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
tl = sum(out["loss"]) + sum(out["renounce"]); tg = sum(out["nat"]) + sum(out["rest"])
print("cum out", tl, "in", tg, "| dest15", out["dest15"], "| US lost/back", out["usLost15"], out["usBack15"], round(out["usBack15"] / out["usLost15"] * 100, 1))
print("JP by year", [v[TOPC.index("일본")] for v in out["dest"]["v"]]); print("restBy", RC, "natBy", NC)
print("in", [a + b for a, b in zip(out["nat"], out["rest"])]); print("out", [a + b for a, b in zip(out["loss"], out["renounce"])])
