"""Build q33_data.json (infertility care) from the CSVs and the KOSIS births file in this folder.
nhis_15125614 assisted reproduction patients & claims 2018-2022 (NHIS) · nhis_15127567 infertility (F021) patients by age/region 2018-2022
nhis_15142614 2023 procedures by type x age x cause · nhis_15142615 2023 procedures by facility type
births_mother_age.json KOSIS DT_1B81A08 (all births) / DT_1B81A09 (multiple births) by mother's age, 2005-2025."""
import csv, json, os, collections
H = os.path.dirname(os.path.abspath(__file__))
rd = lambda f: list(csv.DictReader(open(os.path.join(H, f), encoding="utf-8")))
out = {}
T = rd("nhis_15125614.csv")
out["trend"] = {"y": [int(x["진료년도"][:4]) for x in T], "p": [int(x["진료인원(명)"]) for x in T], "c": [int(x["진료건수(건)"]) for x in T]}
F = rd("nhis_15127567.csv")
dx = {}
for code, key in (("N46 N97", "dx"), ("Z311 Z312 Z313", "art")):
    for y in range(2018, 2023):
        rows = [x for x in F if x["주상병코드"] == code and x["진료연도"] == f"{y}년"]
        ages = collections.Counter()
        for x in rows: ages[int(x["연령"][:-1])] += int(x["진료인원(명)"])
        dx.setdefault(key, {})[y] = {"p": sum(ages.values()), "ages": {a: ages[a] for a in range(20, 56)}}
out["f021"] = dx
P = rd("nhis_15142614.csv"); causes = [k.replace("난임원인건수_", "") for k in P[0] if k.startswith("난임원인건수_")]
out["cause"] = {"causes": causes, "rows": [{"type": x["시술유형별"], "age": x["연령구분"], "n": int(x["전체 난임시술건수"]), "c": [int(x["난임원인건수_" + c]) for c in causes]} for x in P]}
K = rd("nhis_15142615.csv")
out["fac"] = [{"t": x["요양기관종별"], "k": int(x["기관수"]), "n": int(x["전체 난임시술건수"]), "iui": int(x["인공수정시술건수"]), "ivf": int(x["체외수정시술건수"])} for x in K]
B = json.load(open(os.path.join(H, "births_mother_age.json"), encoding="utf-8"))
AG = ["20 - 24세", "25 - 29세", "30 - 34세", "35 - 39세", "40 - 44세", "45 - 49세", "50세 이상"]
BY = list(range(2005, 2026))
out["births"] = {"y": BY, "ages": AG, "all": [[B["all"][str(y)].get(a, {}).get("계", 0) for a in AG] for y in BY], "twin": [[B["twin"][str(y)].get(a, {}).get("계", 0) for a in AG] for y in BY],
                 "tot": [B["all"][str(y)]["계"]["계"] for y in BY], "twinTot": [B["twin"][str(y)]["계"]["계"] for y in BY],
                 "long5": [sum(B["all"][str(y)]["계"].get(k, 0) for k in ("5년", "6년", "7년", "8년", "9년", "10~14년", "15~19년", "20년이상")) for y in BY]}
json.dump(out, open(os.path.join(H, "q33_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", os.path.getsize(os.path.join(H, "q33_data.json")))
print({k: (v[2018]["p"], v[2022]["p"]) for k, v in dx.items()})
print("long5 share", [(y, round(l / t * 100, 1)) for y, l, t in zip(BY, out["births"]["long5"], out["births"]["tot"]) if y in (2005, 2015, 2023, 2025)])
