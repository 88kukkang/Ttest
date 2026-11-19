"""#47 계산: 사회통합실태조사 기관별 신뢰 정도(KOSIS 417 DT_417001_0038). '신뢰한다' = ③ 약간 + ④ 매우.
출력: q47_data.json"""
import os, sys, json
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
sys.path.insert(0, os.path.join(H, "..", "kosis")); import kosis_curl as k
LV = ["전혀", "별로", "약간", "매우", "평균"]
def parse(fn):
    r = k.table(os.path.join(R, fn)); ys = [int(y) for y in r[0][3:]]; out = {}; g = inst = None
    for x in r[2:]:
        if len(x) < 4: continue
        if x[0]: g = x[0]
        if x[1]: inst = x[1]
        lv = next(i for i, l in enumerate(LV) if l in x[2])
        out.setdefault(g, {}).setdefault(inst, [[None] * len(ys) for _ in LV])[lv] = [k.num(v) for v in x[3:]]
    return ys, out
YA, A = parse("trust_all.json"); YG, G = parse("trust_groups.json")
INST = list(A["전체"].keys()); print(INST, YA)
for inst in INST:
    v = A["전체"][inst]
    for j in range(len(YA)):
        if v[0][j] is None: continue   # 공기업은 2016년부터 물었다
        s = sum(v[i][j] for i in range(4)); assert abs(s - 100) < .6, (inst, YA[j], s)
tr = lambda v, j: None if v[2][j] is None else v[2][j] + v[3][j]
last = len(YA) - 1
print("2025 신뢰한다(③+④) 낮은 순")
for inst in sorted(INST, key=lambda i: tr(A["전체"][i], last)):
    v = A["전체"][inst]; print(f"  {inst:8s} {tr(v, last):5.1f}  전혀 {v[0][last]:4.1f}  평균 {v[4][last]}  | 2013 {tr(v, 0) or 0:5.1f}  2024 {tr(v, last - 1):5.1f}  min {min(tr(v, j) for j in range(len(YA)) if tr(v, j) is not None):.1f}({YA[min((j for j in range(len(YA)) if tr(v, j) is not None), key=lambda j: tr(v, j))]}) max {max(tr(v, j) for j in range(len(YA)) if tr(v, j) is not None):.1f}({YA[max((j for j in range(len(YA)) if tr(v, j) is not None), key=lambda j: tr(v, j))]})")
AGE = ["19~29세", "30~39세", "40~49세", "50~59세", "60세 이상"]; jg = YG.index(2025)
print("나이별 2025")
for inst in INST:
    print(f"  {inst:8s}", [round(tr(G[a][inst], jg), 1) for a in AGE], "범위", round(max(tr(G[a][inst], jg) for a in AGE) - min(tr(G[a][inst], jg) for a in AGE), 1))
print("특성 그룹", list(G.keys()))
out = {"years": YA, "inst": INST, "all": {i: A["전체"][i] for i in INST}, "gy": YG, "groups": {g: {i: G[g][i] for i in INST} for g in G}}
json.dump(out, open(os.path.join(H, "q47_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(os.path.getsize(os.path.join(H, "q47_data.json")))
