"""Build q32_data.json for the marriage page from the parsed KOSIS files in this folder.
Inputs (made by parse_sg.py, parse_age.py and the inline parsers noted below):
  long.json  DT_1B8000F national marriages/divorces 1970-2025
  mon.json   DT_1B8000G national monthly marriages 2015.01-2026.08 (2026 provisional)
  age.json   DT_1B83A02 husband age x wife age marriages 1990-2025
  pop5.json  DT_1B04005N resident population by 5-year age and sex, December 2012-2025
  sg.json    DT_1B8000I sigungu marriages 2000-2025
  ../q19-closures/q19_data.json  map places (sigungu with 일반구 merged), centroids and province outlines
"""
import json, re, os
H = os.path.dirname(os.path.abspath(__file__))
J = lambda f: json.load(open(os.path.join(H, f), encoding="utf-8"))
long, mon, age, pop, sg = J("long.json"), J("mon.json"), J("age.json"), J("pop5.json"), J("sg.json")
out = {}
Y = list(range(1970, 2026))
out["long"] = {"y": Y, "m": [long["m"][str(y)] for y in Y], "d": [long["d"][str(y)] for y in Y], "mr": [long["mr"][str(y)] for y in Y]}
ja = lambda y: sum(mon[f"{y}.{m:02d}"] for m in range(1, 9))
out["mon"] = {"y2025": [mon[f"2025.{m:02d}"] for m in range(1, 9)], "y2026": [mon[f"2026.{m:02d}"] for m in range(1, 9)], "ja": {y: ja(y) for y in range(2015, 2027)}}

# husband x wife single-year grid
HA, WA = list(range(22, 45)), list(range(20, 40))
def cell(y, h, w): return age[str(y)].get(f"{h}세", {}).get(f"{w}세", 0)
AY = list(range(1990, 2026))
out["grid"] = {"y": AY, "h": HA, "w": WA, "v": [[[int(cell(y, h, w)) for w in WA] for h in HA] for y in AY],
               "tot": [age[str(y)]["계"]["계"] for y in AY]}
# share of the grid in all marriages (for the caption)
out["grid"]["share"] = [round(sum(sum(r) for r in out["grid"]["v"][i]) / out["grid"]["tot"][i] * 100, 1) for i in range(len(AY))]

# age-specific rates per 1,000 (mid-year population = mean of two Decembers)
def hc(y, lo): return sum(r.get("계", 0) for h, r in age[str(y)].items() if re.match(r"^\d+세$", h) and lo <= int(h[:-1]) <= lo + 4)
def wc(y, lo): return sum(v for w, v in age[str(y)]["계"].items() if re.match(r"^\d+세$", w) and lo <= int(w[:-1]) <= lo + 4)
def P(y, sex, g): return (pop[f"{y}.12"][sex][g] + pop[f"{y-1}.12"][sex][g]) / 2
RY = list(range(2013, 2026)); G = [25, 30, 35]
gl = lambda lo: f"{lo} - {lo+4}세"
out["rate"] = {"y": RY, "g": G,
    "m": {lo: [round(hc(y, lo) / P(y, "남자인구수 (명)", gl(lo)) * 1000, 1) for y in RY] for lo in G},
    "f": {lo: [round(wc(y, lo) / P(y, "여자인구수 (명)", gl(lo)) * 1000, 1) for y in RY] for lo in G},
    "pm": {lo: [round(P(y, "남자인구수 (명)", gl(lo))) for y in RY] for lo in G}}
# population effect, men 20-49
GG = [20, 25, 30, 35, 40, 45]
a22 = sum(hc(2022, lo) for lo in GG); a25 = sum(hc(2025, lo) for lo in GG)
cf = sum(hc(2022, lo) / P(2022, "남자인구수 (명)", gl(lo)) * P(2025, "남자인구수 (명)", gl(lo)) for lo in GG)
out["decomp"] = {"a22": a22, "a25": a25, "cf": round(cf), "all22": age["2022"]["계"]["계"], "all25": age["2025"]["계"]["계"]}
# increase by husband age group
def hg(y):
    b = {"25세 미만": 0, "25–29세": 0, "30–34세": 0, "35–39세": 0, "40–44세": 0, "45세 이상": 0}
    for h, r in age[str(y)].items():
        if h in ("계", "미상"): continue
        m = re.match(r"(\d+)", h); a = int(m.group(1)) if m else 0
        k = "25세 미만" if a < 25 else "25–29세" if a < 30 else "30–34세" if a < 35 else "35–39세" if a < 40 else "40–44세" if a < 45 else "45세 이상"
        b[k] += r.get("계", 0)
    return b
out["hgrp"] = {y: hg(y) for y in (2019, 2022, 2025)}

# map places
q = json.load(open(os.path.join(H, "../q19-closures/q19_data.json"), encoding="utf-8"))
F = {'서울':'서울특별시','부산':'부산광역시','대구':'대구광역시','인천':'인천광역시','광주':'광주광역시','대전':'대전광역시','울산':'울산광역시','세종':'세종특별자치시','경기':'경기도','강원':'강원특별자치도','충북':'충청북도','충남':'충청남도','전북':'전북특별자치도','전남':'전라남도','경북':'경상북도','경남':'경상남도','제주':'제주특별자치도'}
ALIAS = {('대구','군위군'):[('경상북도','군위군(변동전)')], ('인천','미추홀구'):[('인천광역시','남구(변동전)')], ('세종','세종시'):[('충청남도','연기군(변동전)')]}
def get(y, sd, c):
    d = sg[str(y)]; k = f"{F[sd]}|{c}"
    if k in d and d[k]["m"] is not None: return d[k]
    for a, b in ALIAS.get((sd, c), []):
        if f"{a}|{b}" in d: return d[f"{a}|{b}"]
    raise KeyError((y, sd, c))
MET = ('서울','부산','대구','인천','광주','대전','울산')
pl = []
for p in q["P"]:
    a, b, c = get(2019, p[0], p[1]), get(2022, p[0], p[1]), get(2025, p[0], p[1])
    t = "g" if p[1].endswith("군") else ("k" if p[0] in MET else "s")
    pl.append([p[0], p[1], p[2], p[3], int(a["m"]), int(b["m"]), int(c["m"]), c["mr"], t])
out["places"] = pl
out["sidoPaths"] = q["sidoPaths"]
nat = {y: sg[str(y)]["전국"]["m"] for y in (2019, 2022, 2025)}
out["abroad"] = {y: int(nat[y] - sum(p[4 + i] for p in pl)) for i, y in enumerate((2019, 2022, 2025))}
json.dump(out, open(os.path.join(H, "q32_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", os.path.getsize(os.path.join(H, "q32_data.json")), out["decomp"], out["abroad"])
print({k: v for k, v in out["rate"].items() if k in ("m", "f")})
print(out["hgrp"]); print(out["grid"]["share"][-4:], out["mon"]["ja"][2025], out["mon"]["ja"][2026])
