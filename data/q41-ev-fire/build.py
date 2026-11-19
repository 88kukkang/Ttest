"""#41 계산: 전기차 화재(소방청 15138615, 2021~2024) ÷ 전기차 등록 대수(한국전력 15039554) 와
전체 자동차 화재(소방청 연간화재통계 15060386, 장소중분류=자동차, 오토바이 제외) ÷ 자동차 등록 대수(KOSIS 116 DT_MLTM_5498).
연간화재통계 원본(연 6MB)은 저장소에 넣지 않았다: ../q23-fire/build.py 의 내려받기 방법을 따라 FIRE_DIR 에 y_2021.bin … f.bin(2024) 을 둔다.
출력: q41_data.json"""
import os, sys, csv, io, json, re, glob, collections
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
sys.path.insert(0, os.path.join(H, "..", "kosis")); import kosis_curl as k
FIRE_DIR = os.environ.get("FIRE_DIR", "")
def rd(f):
    b = open(f, "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try: return list(csv.reader(io.StringIO(b.decode(enc))))
        except UnicodeDecodeError: pass
YEARS = [2021, 2022, 2023, 2024]
# ── 전체 자동차 화재 ──
cache = os.path.join(R, "vehicle_fires.json")
if FIRE_DIR:
    VF = {}
    for y in YEARS:
        r = rd(os.path.join(FIRE_DIR, "f.bin" if y == 2024 else f"y_{y}.bin")); h = r[0]; j = h.index("장소중분류"); s = h.index("장소소분류"); c = h.index("발화요인대분류")
        rows = [x for x in r[1:] if len(x) > s and x[j] == "자동차"]
        VF[y] = {"all": len(rows), "moto": sum(1 for x in rows if x[s] == "오토바이"), "kind": dict(collections.Counter(x[s] for x in rows)),
                 "cause": dict(collections.Counter(x[c] for x in rows if x[s] != "오토바이"))}
    json.dump(VF, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
VF = {int(a): b for a, b in json.load(open(cache, encoding="utf-8")).items()}
# ── 전기차 화재 ──
EV = []
for f in ["ev_fire_2021_2023.csv", "ev_fire_2024.csv"]:
    r = rd(os.path.join(R, f))
    for x in r[1:]:
        if len(x) < 11: continue
        EV.append({"d": x[1], "sido": x[2], "sgg": x[3], "c1": x[4], "c2": x[5], "loc": x[6], "fl": x[7], "ug": x[8], "st": x[9], "pt": x[10]})
print("전기차 화재", len(EV), collections.Counter(e["d"][:4] for e in EV))
# ── 등록 대수 ──
r = k.table(os.path.join(R, "veh_total.json")); hd = r[0][3:]; tot = {p: 0 for p in hd}
for x in r[2:]:
    if len(x) > 3:
        for p, v in zip(hd, x[3:]): tot[p] += int(k.num(v))
evr = {}; evsido = {}
for f in sorted(glob.glob(os.path.join(R, "kepco_*.csv"))) + [os.path.join(R, "n_15039554.csv")]:
    r = rd(f); h = r[0]
    for x in r[1:]:
        d = dict(zip(h, x)); t = sum(int(d[c]) for c in h[1:] if c != "합계" and d.get(c))
        # 2022.3까지 파일은 날짜가 '그달 1일'로 적혀 있지만 값은 그달 말 수치다(국토부 연말 등록 대수와 맞춰 확인): 달로만 쓴다
        evr[x[0][:7]] = t; evsido[x[0][:7]] = {c: int(d[c]) for c in h[1:] if c != "합계" and d.get(c)}
print("연말 전기차", {y: evr[f"{y}-12"] for y in range(2018, 2026)}); print("연말 전체", tot)
RATE = []
for y in YEARS:
    e0, e1 = evr[f"{y - 1}-12"], evr[f"{y}-12"]; t0, t1 = tot[f"{y - 1}.12"], tot[f"{y}.12"]
    ef = sum(1 for e in EV if e["d"][:4] == str(y)); af = VF[y]["all"] - VF[y]["moto"]
    em = (e0 + e1) / 2; tm = (t0 + t1) / 2
    RATE.append({"y": y, "ev_fire": ef, "ev_reg": round(em), "ev_end": e1, "all_fire": af, "all_reg": round(tm), "all_end": t1,
                 "ev": ef / em * 1e4, "all": af / tm * 1e4, "non": (af - ef) / (tm - em) * 1e4, "moto": VF[y]["moto"]})
    print(y, RATE[-1])
ef = sum(x["ev_fire"] for x in RATE); em = sum(x["ev_reg"] for x in RATE); af = sum(x["all_fire"] for x in RATE); am = sum(x["all_reg"] for x in RATE)
print(f"4년 합: 전기차 {ef}건 / {em:,}대·년 = 1만 대당 {ef / em * 1e4:.2f} | 전체 {af}건 / {am:,} = {af / am * 1e4:.2f} | 전기차 아닌 차 {(af - ef) / (am - em) * 1e4:.2f}")
print("상태", collections.Counter(e["st"] for e in EV)); print("장소", collections.Counter(e["loc"] for e in EV)); print("지하", collections.Counter(e["ug"] for e in EV))
print("요인", collections.Counter(e["c1"] for e in EV)); print("발화지점", collections.Counter(e["pt"] for e in EV))
print("충전중 요인", collections.Counter(e["c1"] for e in EV if e["st"] == "충전중")); print("주차 요인", collections.Counter(e["c1"] for e in EV if e["st"] == "주차"))
print("지하 상태", collections.Counter(e["st"] for e in EV if e["ug"] == "지하"))
print("담배꽁초", sum(1 for e in EV if e["c2"] == "담배꽁초"), "적재함", sum(1 for e in EV if e["pt"] == "적재함"), "적재함+부주의", sum(1 for e in EV if e["pt"] == "적재함" and e["c1"] == "부주의"))
allc = collections.Counter()
for y in YEARS: allc.update(VF[y]["cause"])
print("전체 차 요인", allc.most_common())
# ── 지도 자리 맞추기 ──
G = json.load(open(os.path.join(H, "..", "q19-closures", "q19_data.json"), encoding="utf-8"))
SH = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
      "강원특별자치도": "강원", "강원도": "강원", "충청북도": "충북", "충청남도": "충남", "전라북도": "전북", "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}
pidx = {(p[0], p[1]): i for i, p in enumerate(G["P"])}; miss = set()
def place(sd, nm):
    nm = nm.strip(); c = (sd, nm.split(" ")[0])
    if sd == "세종": c = ("세종", "세종시")
    if c not in pidx:
        m = re.match(r"(.+?시)(.+구)$", nm)
        if m: c = (sd, m.group(1))
    return pidx.get(c)
for e in EV:
    e["s"] = SH[e["sido"]]; e["p"] = place(e["s"], e["sgg"])
    if e["p"] is None: miss.add((e["s"], e["sgg"]))
print("못 맞춘 시군구", miss)
# 시군구 전기차 등록(운행차량 기준, 한국교통안전공단 15142951)
r = rd(os.path.join(R, "ev_reg_sigungu.csv")); reg = [0] * len(G["P"]); miss2 = set(); regsum = 0
for x in r[1:]:
    a = x[0].split(" ", 1); sd = SH.get(a[0], a[0]); nm = a[1] if len(a) > 1 else a[0]; i = place(sd, nm); regsum += int(x[7])
    if i is None: miss2.add(x[0]); continue
    reg[i] += int(x[7])
print("등록 못 맞춘 곳", miss2, "합", sum(reg), regsum)
fires = [[e["d"], e["p"], {"운행중": 0, "정차": 0, "견인중": 0, "주차": 1, "충전중": 2}[e["st"]], e["c1"], e["c2"], e["loc"], 1 if e["ug"] == "지하" else 0, e["pt"], e["fl"]] for e in sorted(EV, key=lambda e: e["d"])]
P = [{"s": p[0], "n": p[1], "x": p[2], "y": p[3], "codes": p[7], "ev": reg[i]} for i, p in enumerate(G["P"])]
mon = sorted(evr); 
out = {"rate": RATE, "fires": fires, "P": P, "U": G["U"], "sidoPaths": G["sidoPaths"], "W": G["W"], "H": G["H"],
       "evMonthly": [[m, evr[m]] for m in mon], "evSido": evsido[max(m for m in mon if m <= "2024-12")], "totEnd": tot,
       "cause": {"ev": dict(collections.Counter(e["c1"] for e in EV)), "all": dict(allc)}, "kind": {str(y): VF[y]["kind"] for y in YEARS}}
json.dump(out, open(os.path.join(H, "q41_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(os.path.getsize(os.path.join(H, "q41_data.json")))
sd = collections.Counter(e["s"] for e in EV); es = out["evSido"]
print("시도별 4년 화재/2024말 등록", {s: (sd[s], es.get(s)) for s in es})
top = collections.Counter(e["p"] for e in EV).most_common(8); print([(P[i]["s"], P[i]["n"], c, P[i]["ev"]) for i, c in top])
