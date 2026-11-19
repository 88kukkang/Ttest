"""#39 계산: 시군구(229곳, 일반구는 시로 합침)별 의사 수·인구 1,000명당 의사 수·전문과목별 전문의 수.
입력: raw/doc_*.json, raw/pop_*.json, raw/spec_*.json (fetch.py), 지도 도형은 ../q19-closures/q19_data.json 재사용.
출력: q39_data.json"""
import os, sys, json, re, glob
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
sys.path.insert(0, os.path.join(H, "..", "kosis")); import kosis_curl as k
G = json.load(open(os.path.join(H, "..", "q19-closures", "q19_data.json"), encoding="utf-8"))
SIDO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]
HC = dict(zip(["11", "21", "22", "23", "24", "25", "26", "41", "31", "32", "33", "34", "35", "36", "37", "38", "39"], SIDO))
PC = dict(zip(["11", "26", "27", "28", "29", "30", "31", "36", "41", "51", "43", "44", "52", "46", "47", "48", "50"], SIDO))
places = [(p[0], p[1]) for p in G["P"]]; pidx = {p: i for i, p in enumerate(places)}
ALIAS = {("인천", "남구"): ("인천", "미추홀구"), ("충북", "청원군"): ("충북", "청주시"), ("경북", "군위군"): ("대구", "군위군"), ("세종", "세종특별자치시"): ("세종", "세종시"),
         ("부산", "진구"): ("부산", "부산진구"), ("경남", "진해시"): ("경남", "창원시"), ("경남", "마산시"): ("경남", "창원시"), ("충남", "연기군"): ("세종", "세종시")}
def place(sido, nm):
    nm = re.sub(r"^\d+\)", "", nm).strip(); c = (sido, nm.split(" ")[0]); c = ALIAS.get(c, c)
    return pidx.get(c)
def n(s): v = k.num(s); return 0 if v is None else int(v)

# ── 의사 수 ──
JOBS = ["의사", "일반의", "인턴", "레지던트", "전문의"]
per = k.table(os.path.join(R, "doc_00.json"))[0][2:]
doc = [dict() for _ in places]; sido_doc = {}; nat_doc = {}; miss = set()
for code, sd in list(HC.items()) + [("00", "전체")]:
    r = k.table(os.path.join(R, f"doc_{code}.json")); hd = r[0][2:]; cur = None   # 세종 표에는 2009년 열이 없다 → 열 이름으로 맞춘다
    for x in r[2:]:
        if len(x) < 3: continue
        if x[0]: cur = x[0]
        got = dict(zip(hd, x[2:])); vals = [n(got.get(q, "")) for q in per]
        if cur in (sd, "전체"): (nat_doc if sd == "전체" else sido_doc.setdefault(sd, {}))[x[1]] = vals; continue
        i = place(sd, cur)
        if i is None: miss.add((sd, cur)); continue
        a = doc[i].setdefault(x[1], [0] * len(vals)); doc[i][x[1]] = [p + q for p, q in zip(a, vals)]
print("의사 시점", per, "| 못 맞춘 이름", miss)
# ── 인구 ──
pop = [None] * len(places); sido_pop = {}; pper = None; nat_pop = None
for code, sd in list(PC.items()) + [("00", "전국")]:
    r = k.table(os.path.join(R, f"pop_{code}.json")); pper = r[0][1:]; first = True
    for x in r[2:]:
        if len(x) < 2: continue
        vals = [n(v) for v in x[1:]]
        if first:
            first = False
            if sd == "전국": nat_pop = vals
            else: sido_pop[sd] = vals
            if sd != "세종": continue
        nm = re.sub(r"^\d+\)", "", x[0]).strip(); c = ALIAS.get((sd, nm), (sd, nm)); i = pidx.get(c)
        if i is None: continue
        if pop[i] is None: pop[i] = vals
        elif c != (sd, nm) or (sd, nm) in (("인천", "미추홀구"),): pop[i] = [a or b for a, b in zip(pop[i], vals)]   # 남구→미추홀구 이름 변경
# 군위군은 2023.7 대구로 옮김: 경북 표의 옛 값으로 빈칸을 채운다
r = k.table(os.path.join(R, "pop_47.json"))
for x in r[2:]:
    if len(x) > 1 and re.sub(r"^\d+\)", "", x[0]).strip() == "군위군":
        i = pidx[("대구", "군위군")]; old = [n(v) for v in x[1:]]; pop[i] = [a or b for a, b in zip(pop[i] or [0] * len(old), old)]
print("인구 시점", pper, "| 인구 없는 곳", [places[i] for i, v in enumerate(pop) if not v or not v[-1]])
# ── 전문과목 ──
SPEC = None; spec = [dict() for _ in places]; nat_spec = {}
for code, sd in list(HC.items()) + [("00", "전체")]:
    r = k.table(os.path.join(R, f"spec_{code}.json")); cur = None
    for x in r[2:]:
        if len(x) < 3: continue
        if x[0]: cur = x[0]
        if cur in (sd, "전체"):
            if sd == "전체": nat_spec[x[1]] = n(x[2])
            continue
        i = place(sd, cur)
        if i is not None: spec[i][x[1]] = spec[i].get(x[1], 0) + n(x[2])
SPEC = [s for s in nat_spec if s != "계"]

LAST = len(per) - 1; PL = len(pper) - 1
IX = {"2014": (per.index("2014.4/4"), pper.index("2014.12")), "2019": (per.index("2019.4/4"), pper.index("2019.12")), "2026": (LAST, PL)}
print("의사 없는 곳", [places[i] for i, d in enumerate(doc) if "의사" not in d])
P = []
for i, (sd, nm) in enumerate(places):
    g = G["P"][i]; d = doc[i]
    row = {"s": sd, "n": nm, "x": g[2], "y": g[3], "codes": g[7], "pop": pop[i][PL], "doc": d["의사"][LAST], "sp": d["전문의"][LAST], "gp": d["일반의"][LAST], "tr": d["인턴"][LAST] + d["레지던트"][LAST],
           "d14": d["의사"][IX["2014"][0]], "p14": pop[i][IX["2014"][1]], "d19": d["의사"][IX["2019"][0]], "p19": pop[i][IX["2019"][1]],
           "spec": [spec[i].get(s, 0) for s in SPEC]}
    P.append(row)
# ── 인구 크기 원(돌링 카토그램) 자리: 넓이 = 인구. 제 자리에서 시작해 겹치지 않을 때까지 밀어낸다 ──
import math
KR = math.sqrt(0.25 * G["W"] * G["H"] / (math.pi * sum(p["pop"] for p in P)))
RF = [KR * math.sqrt(p["pop"]) for p in P]; C = [[p["x"], p["y"], 0.0] for p in P]; O = [(c[0], c[1]) for c in C]
for it in range(2400):
    grow = min(1, (it + 1) / 1500)        # 원을 조금씩 키우며 밀어내면 이웃 관계가 덜 흐트러진다
    pull = 0.02 * max(0, 1 - it / 1800)   # 제 자리로 당기는 힘은 줄여 가다, 마지막 600번은 밀어내기만 한다
    for i, c in enumerate(C):
        c[2] = RF[i] * grow; c[0] += (O[i][0] - c[0]) * pull; c[1] += (O[i][1] - c[1]) * pull
    for i in range(len(C)):
        a = C[i]
        for j in range(i + 1, len(C)):
            b = C[j]; dx = b[0] - a[0]; dy = b[1] - a[1]; d = math.hypot(dx, dy) or 0.01; need = a[2] + b[2] + 0.8
            if d < need:
                m = (need - d) / 2; ux, uy = dx / d, dy / d; wa = b[2] ** 2 / ((a[2] ** 2 + b[2] ** 2) or 1); wb = 1 - wa
                a[0] -= ux * m * 2 * wa; a[1] -= uy * m * 2 * wa; b[0] += ux * m * 2 * wb; b[1] += uy * m * 2 * wb
ov = sum(1 for i in range(len(C)) for j in range(i + 1, len(C)) if math.hypot(C[i][0] - C[j][0], C[i][1] - C[j][1]) < C[i][2] + C[j][2] - 0.3)
x0 = min(c[0] - c[2] for c in C); x1 = max(c[0] + c[2] for c in C); y0 = min(c[1] - c[2] for c in C); y1 = max(c[1] + c[2] for c in C)
print("돌링: 겹침", ov, "범위", round(x0), round(x1), round(y0), round(y1))
for p, c in zip(P, C): p["cx"] = round(c[0], 1); p["cy"] = round(c[1], 1); p["cr"] = round(c[2], 2)
tot_doc = sum(p["doc"] for p in P); tot_pop = sum(p["pop"] for p in P)
print("시군구 합 의사", tot_doc, "전국 표", nat_doc["의사"][LAST], "| 인구 합", tot_pop, "전국", nat_pop[PL])
S = []
for sd in SIDO:
    d = sido_doc[sd]; S.append({"n": sd, "doc": d["의사"], "sp": d["전문의"], "gp": d["일반의"], "in": d["인턴"], "re": d["레지던트"], "pop": sido_pop[sd]})
# 시도 분기 흐름
r = k.table(os.path.join(R, "doc_sido_q.json")); qper = r[0][2:]; cur = None; Q = {}
for x in r[2:]:
    if len(x) < 3: continue
    if x[0]: cur = x[0]
    Q.setdefault(cur, {})[x[1]] = [n(v) for v in x[2:]]
out = {"per": per, "pper": pper, "P": P, "U": G["U"], "sidoPaths": G["sidoPaths"], "W": G["W"], "H": G["H"], "S": S, "SPEC": SPEC, "natSpec": [nat_spec[s] for s in SPEC],
       "nat": {"doc": nat_doc["의사"], "sp": nat_doc["전문의"], "gp": nat_doc["일반의"], "in": nat_doc["인턴"], "re": nat_doc["레지던트"], "pop": nat_pop},
       "dbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)], "qper": qper, "Q": {kk: Q[kk] for kk in ["전체", "서울"] if kk in Q}, "Qall": {kk: v["의사"] for kk, v in Q.items()}}
json.dump(out, open(os.path.join(H, "q39_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(os.path.getsize(os.path.join(H, "q39_data.json")))

# ── 요약(본문에 쓸 숫자) ──
f = lambda p: p["doc"] / p["pop"] * 1000
nat = nat_doc["의사"][LAST] / nat_pop[PL] * 1000
print(f"전국 의사 {nat_doc['의사'][LAST]:,} / 인구 {nat_pop[PL]:,} = 1,000명당 {nat:.2f}")
for s in S: print(f"  {s['n']} 의사 {s['doc'][LAST]:,} ({s['doc'][LAST] / nat_doc['의사'][LAST] * 100:.1f}%) 인구 {s['pop'][PL] / nat_pop[PL] * 100:.1f}% → {s['doc'][LAST] / s['pop'][PL] * 1000:.2f}  | 2014 {s['doc'][IX['2014'][0]] / s['pop'][IX['2014'][1]] * 1000:.2f}")
cap = [s for s in S if s["n"] in ("서울", "경기", "인천")]
print("수도권 의사 비중", sum(s["doc"][LAST] for s in cap) / nat_doc["의사"][LAST], "인구", sum(s["pop"][PL] for s in cap) / nat_pop[PL])
srt = sorted(P, key=f, reverse=True)
print("상위", [(p["s"], p["n"], round(f(p), 2), p["doc"]) for p in srt[:15]])
print("하위", [(p["s"], p["n"], round(f(p), 2), p["doc"]) for p in srt[-15:]])
print("전국 평균 이상인 곳", sum(1 for p in P if f(p) >= nat), "/", len(P), "| 그곳 인구 비중", sum(p["pop"] for p in P if f(p) >= nat) / tot_pop)
print("1명 미만", sum(1 for p in P if f(p) < 1), "인구", sum(p["pop"] for p in P if f(p) < 1))
seoul = [p for p in P if p["s"] == "서울"]; print("서울 구", sorted([(p["n"], round(f(p), 2)) for p in seoul], key=lambda z: -z[1]))
for sname in ["소아청소년과", "산부인과", "응급의학과", "정신건강의학과", "피부과", "성형외과", "심장혈관흉부외과", "신경외과", "안과"]:
    j = SPEC.index(sname); z = [p for p in P if p["spec"][j] == 0]
    print(sname, "전국", nat_spec[sname], "0명인 곳", len(z), [p["s"] + " " + p["n"] for p in z][:12], "| 서울 비중", sum(p["spec"][j] for p in seoul) / nat_spec[sname], "강남구", next(p["spec"][j] for p in P if p["n"] == "강남구"))
print("분기", qper[0], qper[-1]); a = Q["전체"]
for i, q in enumerate(qper):
    if q in ("2023.4/4", "2024.1/4", "2024.2/4", "2024.4/4", "2025.2/4", "2025.3/4", "2025.4/4", "2026.2/4", "2019.4/4"): print(" ", q, {j: a[j][i] for j in JOBS})
