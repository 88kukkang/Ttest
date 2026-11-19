"""#45 계산: 기상청 태풍목록(영향도)과 일본기상청 RSMC 최적경로(위치·중심기압·최대풍속)를 태풍번호로 잇는다.
'한국에 영향' = 기상청 영향도가 직접영향 또는 상륙(상륙은 2002년부터 따로 적었고, 그 전에는 직접영향에 들어 있다).
한국에 가장 가까웠을 때 = 최적경로 점 가운데 기준점(북위 35.9°, 동경 127.8°)에서 가장 가까운 점.
출력: q45_data.json"""
import os, json, zipfile, math, collections, statistics as st
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
K = json.load(open(os.path.join(R, "kma_typhoon_list.json"), encoding="utf-8"))
txt = zipfile.ZipFile(os.path.join(R, "jma_bst_all.zip")).read("bst_all.txt").decode("ascii").splitlines()
T = {}; i = 0
while i < len(txt):
    h = txt[i]; n = int(h[12:15]); intl = h[6:10]; pts = []
    for x in txt[i + 1:i + 1 + n]:
        y = int(x[0:2]); y = 1900 + y if y > 50 else 2000 + y; w = x[33:36].strip()
        pts.append([f"{y}{x[2:8]}", int(x[13]), int(x[15:18]) / 10, int(x[19:23]) / 10, int(x[24:28]), int(w) if w else None])
    T[intl] = pts; i += 1 + n
REF = (35.9, 127.8)
def km(a, b, c, d):
    p1, p2 = math.radians(a), math.radians(c); dl = math.radians(d - b)
    return 6371 * math.acos(min(1, math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)))
TY = []; miss = 0
for r in K:
    y = int(r[5][:4]); key = f"{y % 100:02d}{int(r[0]):02d}"; imp = r[4] != "없음"
    o = {"y": y, "no": int(r[0]), "ko": r[1], "en": r[2], "imp": {"없음": 0, "직접영향": 1, "상륙": 2}[r[4]], "start": r[5], "end": r[6]}
    p = T.get(key)
    if p:   # 2026년은 최적경로가 확정 전이고 시즌 중이라 지도에만 쓰고 추세 계산에서는 뺀다
        o["minp"] = min(q[4] for q in p); o["maxw"] = max((q[5] for q in p if q[5] is not None), default=None)
        if imp:
            near = min(p, key=lambda q: km(q[2], q[3], *REF)); o["near"] = {"t": near[0], "km": round(km(near[2], near[3], *REF)), "p": near[4], "w": near[5], "lat": near[2], "lon": near[3]}
            close = [q for q in p if km(q[2], q[3], *REF) <= 400]   # 기준점 400km 안: 남해안·제주까지 들어온다
            if close: c = min(close, key=lambda q: q[4]); o["close"] = {"t": c[0], "p": c[4], "w": c[5], "km": round(km(c[2], c[3], *REF))}
            o["trk"] = [[q[2], q[3], q[4]] for q in p if 15 <= q[2] <= 50 and 105 <= q[3] <= 150]
    elif imp: miss += 1
    TY.append(o)
print("태풍", len(TY), "영향", sum(1 for o in TY if o["imp"]), "경로 없는 영향 태풍", miss)
IMP = [o for o in TY if o["imp"] and "near" in o and o["y"] <= 2025]
dec = lambda y: y // 10 * 10
print("\n연대별: 발생 / 영향 / 영향 중 9–10월 / 가까울 때 중심기압 중앙값 / 950hPa 이하로 다가온 수")
for d in range(1950, 2030, 10):
    a = [o for o in TY if dec(o["y"]) == d]; b = [o for o in IMP if dec(o["y"]) == d]; bb = [o for o in TY if o["imp"] and dec(o["y"]) == d]
    yrs = len(set(o["y"] for o in a))
    if not b: print(d, len(a), len(bb)); continue
    late = sum(1 for o in b if int(o["near"]["t"][4:6]) >= 9)
    print(d, f"{len(a)}({len(a) / yrs:.1f}/년)", f"{len(bb)}({len(bb) / yrs:.2f}/년)", f"9–10월 {late}({late / len(b) * 100:.0f}%)", "기압 중앙값", st.median(o["near"]["p"] for o in b), "≤950", sum(1 for o in b if o["near"]["p"] <= 950), "≤970", sum(1 for o in b if o["near"]["p"] <= 970))
print("\n가장 강하게 다가온 태풍(가까울 때 중심기압)")
for o in sorted(IMP, key=lambda o: o["near"]["p"])[:15]: print(" ", o["y"], o["no"], o["ko"], o["en"], o["near"], "일생 최저", o["minp"])
print("\n가장 늦게 온 태풍(가까울 때 날짜, 달-일)")
for o in sorted(IMP, key=lambda o: o["near"]["t"][4:8])[-10:]: print(" ", o["y"], o["ko"], o["en"], o["near"]["t"], o["near"]["p"])
print("가장 이르게"); 
for o in sorted(IMP, key=lambda o: o["near"]["t"][4:8])[:5]: print(" ", o["y"], o["ko"], o["en"], o["near"]["t"], o["near"]["p"])
print("\n400km 안에 들어온 태풍: 연대별 수 / 그때 최저기압 중앙값 / 970 이하 / 960 이하")
for d in range(1950, 2030, 10):
    b = [o for o in IMP if dec(o["y"]) == d and "close" in o]; a = [o for o in IMP if dec(o["y"]) == d]
    if b: print(d, len(b), "/", len(a), st.median(o["close"]["p"] for o in b), sum(1 for o in b if o["close"]["p"] <= 970), sum(1 for o in b if o["close"]["p"] <= 960))
for a, b in ((1951, 1987), (1988, 2025)):
    s_ = [o for o in IMP if a <= o["y"] <= b and "close" in o]; print(f"{a}–{b} 400km 안 {len(s_)}개 기압 평균 {st.mean(o['close']['p'] for o in s_):.1f} 중앙값 {st.median(o['close']['p'] for o in s_)} ≤960 {sum(1 for o in s_ if o['close']['p'] <= 960)}")
print("가장 강하게 들어온(400km 안)", [(o["y"], o["ko"] or o["en"], o["close"]) for o in sorted([o for o in IMP if "close" in o], key=lambda o: o["close"]["p"])[:12]])
print("400km 밖으로만 지난 영향 태풍", sum(1 for o in IMP if "close" not in o))
# 달별
mon = collections.Counter(int(o["near"]["t"][4:6]) for o in IMP); print("\n달별", sorted(mon.items()))
for a, b in ((1951, 1987), (1988, 2025), (1951, 1980), (1996, 2025)):
    s = [o for o in IMP if a <= o["y"] <= b]; print(f"{a}–{b}: {len(s)}개 {len(s) / (b - a + 1):.2f}/년, 9월 이후 {sum(1 for o in s if int(o['near']['t'][4:6]) >= 9) / len(s) * 100:.0f}%, 가까울 때 기압 평균 {st.mean(o['near']['p'] for o in s):.1f}, 중앙값 {st.median(o['near']['p'] for o in s)}, 최대풍속 평균 {st.mean(o['near']['w'] for o in s if o['near']['w']) if any(o['near']['w'] for o in s) else '-'}")
# 연도별 수
YC = collections.Counter(o["y"] for o in TY if o["imp"]); YA = collections.Counter(o["y"] for o in TY)
print("영향 0개인 해", [y for y in range(1951, 2027) if YC[y] == 0]); print("가장 많은 해", YC.most_common(6)); print("2026", YC[2026], YA[2026], [ (o['ko'], o['imp']) for o in TY if o['y']==2026 and o['imp']])
# 모든 태풍의 일생 최저기압(전체 발생 태풍, 세기 추세)
for a, b in ((1951, 1987), (1988, 2025)):
    s = [o["minp"] for o in TY if "minp" in o and a <= o["y"] <= b]; print(f"전체 태풍 {a}–{b} 일생 최저기압 중앙값 {st.median(s)}, 930 이하 비율 {sum(1 for v in s if v <= 930) / len(s) * 100:.1f}%")
json.dump({"ty": TY, "ref": REF}, open(os.path.join(H, "q45_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(os.path.getsize(os.path.join(H, "q45_data.json")))
