"""Build q35_data.json (cosmetics exports).
kosis_145_cosmetics.json  KOSIS 145 (MFDS) DT_145011_A006 exports/imports 2000-2025 and DT_145011_A008 top-10 destinations 2016-2025 (thousand USD)
kcs_15119569.csv          exports by country 2018-2022 (USD), 15119569 · dutyfree_15142237.xlsx duty-free sales by nationality, cosmetics share
geo.json                  Equal Earth world outlines and destination points (made by the scratch geo build from world-atlas 110m)"""
import json, os, csv, openpyxl
H = os.path.dirname(os.path.abspath(__file__))
K = json.load(open(os.path.join(H, "kosis_145_cosmetics.json"), encoding="utf-8"))
Y = list(range(2000, 2026))
out = {"tot": {"y": Y, "exp": [K["tot"][str(y)]["exp"] for y in Y], "imp": [K["tot"][str(y)]["imp"] for y in Y]}}
TY = list(range(2016, 2026)); out["top"] = {"y": TY, "rows": [K["top"][str(y)] for y in TY]}
R = list(csv.reader(open(os.path.join(H, "kcs_15119569.csv"), encoding="utf-8")))
geo = json.load(open(os.path.join(H, "geo.json"), encoding="utf-8"))
alias = {"싱가폴": "싱가포르", "말레이지아": "말레이시아"}
cs = []
for r in R[1:]:
    v = [round(float(x or 0) / 1000) for x in r[1:6]]
    if max(v) <= 0: continue
    cs.append([r[0], v, geo["pts"].get(r[0])])
cs.sort(key=lambda c: -c[1][-1])
out["cty"] = {"y": [2018, 2019, 2020, 2021, 2022], "rows": cs, "n": [sum(1 for c in cs if c[1][i] > 0) for i in range(5)]}
wb = openpyxl.load_workbook(os.path.join(H, "dutyfree_15142237.xlsx"), read_only=True); ws = wb.worksheets
nat = [r for r in ws[0].iter_rows(values_only=True)]; sh = [r for r in ws[1].iter_rows(values_only=True)]
out["duty"] = {"cols": list(nat[0][1:]), "rows": [[r[0], *r[1:]] for r in nat[1:] if r[0]], "cos": [[r[0], r[1]] for r in sh[1:] if r[0]]}
out["geo"] = geo
json.dump(out, open(os.path.join(H, "q35_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", os.path.getsize(os.path.join(H, "q35_data.json")), len(cs), out["cty"]["n"], sum(1 for c in cs if c[2] is None and c[1][-1] > 1000))
