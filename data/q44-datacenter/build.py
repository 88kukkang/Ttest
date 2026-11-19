"""#44 계산: 데이터센터 전기공급 현황(한국전력 15127315, 2023.12.31 기준 지역본부별 호수·계약전력)과
행정구역별 용도별 판매전력량(KOSIS 310 DT_31002_A006, MWh). 실제 사용량은 공개돼 있지 않아
'계약전력 × 가동률 × 8,760시간'으로 범위를 낸다(가동률은 독자가 정한다). 출력: q44_data.json"""
import os, sys, csv, io, json
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
sys.path.insert(0, os.path.join(H, "..", "kosis")); sys.path.insert(0, os.path.join(H, "..")); import kosis_curl as k
def rd(f):
    b = open(os.path.join(R, f), "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try: return list(csv.reader(io.StringIO(b.decode(enc))))
        except UnicodeDecodeError: pass
n = lambda s: float(s.replace(",", "")) if s not in ("", "-") else 0.0
DC = [{"n": x[0], "cnt": int(x[1]), "mw": int(x[2])} for x in rd("datacenter_supply_20231231.csv")[1:] if len(x) >= 3 and x[0]]
tc = sum(d["cnt"] for d in DC); tm = sum(d["mw"] for d in DC); print("데이터센터", tc, "호", tm, "MW", DC)
cap = [d for d in DC if d["n"] in ("서울", "인천", "경기")]; print("수도권", sum(d["cnt"] for d in cap), sum(d["cnt"] for d in cap) / tc, sum(d["mw"] for d in cap), sum(d["mw"] for d in cap) / tm)
r = k.table(os.path.join(R, "sales.json")); hy = r[0][1:]; hs = r[1] if len(r[1]) == len(hy) else r[1][1:]; SALES = {}; lvl_parent = None
for x in r[3:]:
    if len(x) < 3: continue
    nm = x[0]
    for yy, sd, v in zip(hy, hs, x[1:]): SALES.setdefault(nm, {}).setdefault(sd, {})[int(yy)] = n(v)
print(list(SALES.keys()))
T = SALES["합계"]["계"]; print("전국 판매량 TWh", {y: round(v / 1e6, 1) for y, v in T.items()})
full = tm * 8760 / 1e6   # TWh, 계약전력을 1년 내내 다 쓴다면
print(f"계약전력 전부 24시간: {full:.2f} TWh = 2023 전국의 {full / (T[2023] / 1e6) * 100:.2f}%")
for nm in SALES: print(nm, "2023 전국", round(SALES[nm]["계"][2023] / 1e6, 2), "TWh", "서울", round(SALES[nm]["서울"][2023] / 1e6, 2), "경기", round(SALES[nm]["경기"][2023] / 1e6, 2), "제주", round(SALES[nm]["제주"][2023] / 1e6, 2), "| 2010→2025 전국", round(SALES[nm]["계"][2010] / 1e6, 1), round(SALES[nm]["계"][2025] / 1e6, 1))
REG = {"서울": ["서울"], "인천": ["인천"], "경기": ["경기"], "강원": ["강원"], "충북": ["충북"], "대전충남": ["대전", "충남", "세종"], "전북": ["전북"], "광주전남": ["광주", "전남"], "대구경북": ["대구", "경북"], "부산울산경남": ["부산", "울산", "경남"], "제주": ["제주"]}
for d in DC:
    d["sido"] = REG[d["n"]]; d["sales23"] = sum(SALES["합계"][s][2023] for s in d["sido"]); d["svc23"] = sum(SALES["서비스업"][s][2023] for s in d["sido"])
    d["full"] = d["mw"] * 8760; print(d["n"], d["cnt"], d["mw"], f"전부 쓰면 그 지역 판매량의 {d['full'] / d['sales23'] * 100:.1f}%, 서비스업의 {d['full'] / d['svc23'] * 100:.1f}%")
idc = [(int(x[3]), int(x[4]), int(x[5])) for x in rd("incheon_idc_usage.csv")[1:] if len(x) > 5]; print("인천 IDC", sum(v for y, m, v in idc if y == 2020), "kWh(2020)", len(idc))
SIDO = [s for s in hs[:19] if s not in ("계", "개성")]
import geo_sido
out = {"geo": geo_sido.geo(), "dc": DC, "dcTot": {"cnt": tc, "mw": tm}, "years": sorted(T), "sido": SIDO,
       "sales": {nm: {sd: [SALES[nm][sd].get(y, 0) for y in sorted(T)] for sd in ["계"] + SIDO} for nm in SALES},
       "idc": idc}
json.dump(out, open(os.path.join(H, "q44_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
svc = SALES["서비스업"]; print("서비스업 2010→2025 증가율", {s: round((svc[s][2025] / svc[s][2010] - 1) * 100) for s in SIDO if svc[s][2010]})
print("서비스업 2019→2025", {s: round((svc[s][2025] / svc[s][2019] - 1) * 100, 1) for s in ["계"] + SIDO})
