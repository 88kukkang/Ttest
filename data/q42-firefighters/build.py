"""#42 계산: 소방공무원 순직·공상자(활동별, 2016–2025)와 활동량(화재 건수, 구조·구급 출동 건수)으로 '1만 건당 공상'을 낸다.
입력: raw/firefighter_casualties.zip (parse_hwp.py), raw/ems.json·rescue.json (fetch.py), ../q23-fire/q23_data.json 의 연도별 화재 건수.
출력: q42_data.json"""
import os, sys, json
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "..", "kosis")); sys.path.insert(0, os.path.join(H, "..")); sys.path.insert(0, H)
import kosis_curl as k, parse_hwp
n = lambda s: int(s.replace(",", "")) if s and s != "-" else 0
D = parse_hwp.docs(); ACT = ["화재", "구조", "구급", "생활안전", "기타"]
ycs = next(v for kk, v in D.items() if "연도별" in kk); i = ycs.index("2016"); Y = []
while ycs[i][:4].isdigit() and len(ycs[i]) == 4:
    r = ycs[i:i + 14]; y = int(r[0]); last = r[13].split("※")[0]
    row = {"y": y, "tot": n(r[1]), "dead": n(r[2]), "deadBy": [n(v) for v in r[3:8]], "inj": n(r[8]), "injBy": [n(v) for v in r[9:13]] + [n(last)], "deadBlank": r[2] == ""}
    assert sum(row["injBy"]) == row["inj"], row
    if not row["deadBlank"]: assert sum(row["deadBy"]) == row["dead"] and row["dead"] + row["inj"] == row["tot"], row
    Y.append(row); i += 14
    if "※" in r[13]: break
print([(r["y"], r["dead"], r["inj"], r["injBy"]) for r in Y])
scs = next(v for kk, v in D.items() if "2024년" in kk); SIDO = {}
for yr in ("2024", "2025"):
    a = next(j for j, c in enumerate(scs) if f"({yr})" in c); j = scs.index("합계", a + 5); rows = []
    while True:
        r = scs[j:j + 14]; nm = r[0].replace("(남･북부통합)", ""); last = r[13].split("※")[0]
        row = {"n": nm, "dead": n(r[2]), "inj": n(r[8]), "injBy": [n(v) for v in r[9:13]] + [n(last)]}
        assert sum(row["injBy"]) == row["inj"], (yr, row); rows.append(row); j += 14
        if "※" in r[13]: break
    assert sum(x["inj"] for x in rows[1:]) == rows[0]["inj"], yr
    SIDO[yr] = rows; print(yr, len(rows), rows[0])
# 활동량
r = k.table(os.path.join(H, "raw", "ems.json")); hy = r[0][1:]; hk = r[1] if len(r[1]) == len(hy) else r[1][1:]; EMS = {}; EMS_S = {}   # 둘째 머리줄에는 이름 칸이 없다
for x in r[3:]:
    if len(x) < 3: continue
    for yy, kk, v in zip(hy, hk, x[1:]):
        if kk.startswith("출동건수"):
            if x[0] == "전국": EMS[int(yy)] = n(v)
            EMS_S.setdefault(x[0], {})[int(yy)] = n(v)
r = k.table(os.path.join(H, "raw", "rescue.json")); RES = {int(y): n(v) for y, v in zip(r[0][1:], next(x for x in r if x and x[0].startswith("출동건수"))[1:])}
q23 = json.load(open(os.path.join(H, "..", "q23-fire", "q23_data.json"), encoding="utf-8")); FIRE = dict(zip(q23["Y"], q23["yt"]))
print("구급 출동", EMS); print("구조 출동", RES); print("화재", FIRE)
for r_ in Y:
    y = r_["y"]; r_["fire"] = FIRE.get(y); r_["res"] = RES.get(y); r_["ems"] = EMS.get(y)
    r_["per"] = [r_["injBy"][0] / FIRE[y] * 1e4 if y in FIRE else None, r_["injBy"][1] / RES[y] * 1e4 if y in RES else None, r_["injBy"][2] / EMS[y] * 1e4 if y in EMS else None]
    print(y, "공상 비중", [round(v / r_["inj"] * 100, 1) for v in r_["injBy"]], "1만 건당", [None if v is None else round(v, 2) for v in r_["per"]])
import geo_sido
json.dump({"geo": geo_sido.geo(), "ACT": ACT, "Y": Y, "SIDO": SIDO, "emsSido": {kk: v for kk, v in EMS_S.items()}}, open(os.path.join(H, "q42_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
tot = [sum(r_["injBy"][j] for r_ in Y) for j in range(5)]; print("10년 공상 합", sum(tot), tot, [round(v / sum(tot) * 100, 1) for v in tot])
dd = [sum(r_["deadBy"][j] for r_ in Y) for j in range(5)]; print("순직 합(2016–2024)", sum(dd), dd)
f9 = [r_ for r_ in Y if r_["y"] <= 2024]; print("2016–2024 1만 건당: 화재", sum(r_["injBy"][0] for r_ in f9) / sum(r_["fire"] for r_ in f9) * 1e4, "구조", sum(r_["injBy"][1] for r_ in f9) / sum(r_["res"] for r_ in f9) * 1e4, "구급", sum(r_["injBy"][2] for r_ in f9) / sum(r_["ems"] for r_ in f9) * 1e4)
for yr in SIDO:
    print(yr, sorted([(x["n"], x["inj"], round(x["injBy"][4] / x["inj"] * 100) if x["inj"] else 0) for x in SIDO[yr][1:]], key=lambda z: -z[1])[:8])
