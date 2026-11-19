"""#46 계산: 국가 해안쓰레기 모니터링(해양환경공단). 60개 정점, 2기 조사방법(2018–2023)의 개수·무게,
2018·2019년 정점별 세부 항목(15044008)으로 외국에서 온 것(외국기인)과 '어디서 쓰던 물건인지'(이 장의 분류)를 센다.
출력: q46_data.json"""
import os, sys, csv, io, json, re, collections, subprocess
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
def rd(f):
    b = open(os.path.join(R, f), "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try: return [r for r in csv.reader(io.StringIO(b.decode(enc))) if r]
        except UnicodeDecodeError: pass
num = lambda s: float(s.replace(",", "")) if s not in ("", "-") else 0.0
ALIAS = {"순천 반월": "여수 반월", "울주 진하해변": "울주 나사리", "신안 고장리해변": "신안 고장", "인천 영종도 용유해변": "인천 영종도", "태안 안면도 바람아래해변": "태안 안면도",
         "포항 구룡포 대보해변": "포항 구룡포", "인천 백령도 사곶해안": "인천 백령도", "거제 두모몽돌해변": "거제 두모"}   # 세부 항목 파일(2018·2019)의 옛 정점 이름
key = lambda s: re.sub(r"\s+|갯벌$|해변$|해안$", "", ALIAS.get(s.strip(), s.strip()))
EXTRA = {"인천덕적도서포리": "서해"}   # 2018·2019년에만 있던 정점: 지도에는 없고 바다별 합에만 넣는다
# 정점과 바다
fixlon = lambda v: v * 10 if v < 100 else v   # 정점 20곳(0042–0061)은 경도의 소수점이 한 자리 앞에 찍혀 있다(12.82 → 128.2)
S = {key(x[1]): {"n": x[1], "lat": float(x[2]), "lon": fixlon(float(x[3])), "lonFixed": float(x[3]) < 100} for x in rd("sites_15129575.csv")[1:]}
def sea(lat, lon):
    if lat < 33.7 and lon < 127.2: return "제주"
    if lat >= 35.35 and lon >= 128.5: return "동해"
    if lon < 126.2 or lat >= 34.75 and lon < 127.0: return "서해"   # 이 장의 경계: 동경 126.2° 서쪽이거나, 북위 34.75° 북쪽의 서해안
    return "남해"
for s in S.values(): s["sea"] = sea(s["lat"], s["lon"])
print(collections.Counter(s["sea"] for s in S.values()))
# 좌표를 한국 지도 틀(q19)로: scratchpad/geo/proj46.mjs 와 같은 투영 — 결과를 raw/site_xy.json 에 둔다
XY = {k: v for k, v in json.load(open(os.path.join(R, "site_xy.json"), encoding="utf-8")).items()}
# 2기 정점별 개수·무게
r = rd("sites_2018_2023_15069306.csv"); YS = [int(h.split()[0]) for h in r[0][1::2]]
for x in r[1:]:
    s = S[key(x[0])]; s["cnt"] = [num(v) for v in x[1::2]]; s["kg"] = [num(v) for v in x[2::2]]
assert all("cnt" in s for s in S.values())
# 유형별(2018–2023 합)
TYPES = [[x[0], num(x[1]), num(x[2])] for x in rd("types_2018_2023_15069304.csv")[1:]]
TC = sum(t[1] for t in TYPES); TK = sum(t[2] for t in TYPES)
print("유형 합", TC, TK, sum(sum(s["cnt"]) for s in S.values()), sum(sum(s["kg"]) for s in S.values()))
# 시기별
SEASON = [[int(x[0])] + [num(v) for v in x[1:]] for x in rd("season_2018_2023_15069303.csv")[1:]]
# 1기 연도별
Y1 = [[int(x[0]), num(x[1]), num(x[2])] for x in rd("years_2008_2017_15069297.csv")[1:]]
# 세부 항목 2018·2019: 어디서 쓰던 물건인가(이 장의 분류)
FISH = ["밧줄", "부표", "어망", "그물", "낚싯줄", "낚시", "형광찌", "미끼", "통발", "어상자", "양식"]
LIFE = ["음료수병", "뚜껑", "포장지", "비닐봉지", "식품용기", "1회용", "담배꽁초", "종이컵", "우유팩", "음식물포장", "세제", "화장품", "농약", "폭죽", "장난감", "라이터", "주사기", "약병", "풍선", "위생장갑", "충전재", "옷,", "옷, 모자"]
def src(cls, mat, det):
    if cls == "외국기인": return "외국"
    if cls in ("금속", "목재", "고무", "기타(+혼합재질)"): return "모름"   # 낚시추와 캔, 양식장 목재와 나무젓가락이 한 항목에 섞여 있다
    if any(w in det for w in FISH): return "바다"
    if cls in ("유리",) or any(w in det for w in LIFE): return "육지"
    return "모름"
XTRA = {}; ITEMS = {}; SRCS = ["바다", "육지", "외국", "모름"]
for f in ("items_2018_15044008.csv", "items_2019_15044008.csv"):
    r = rd(f); h = r[0]; yi, si, ci, mi, di, ni = (h.index(c) for c in ("년도", "지역", "분류", "재질", "상세분류", "개수"))
    for x in r[1:]:
        n = int(num(x[ni]))
        if not n: continue
        y = int(x[yi]); s = key(x[si]); kk = (x[ci], x[mi], x[di])
        ITEMS.setdefault(y, collections.Counter())[kk] += n
        if s in EXTRA: XTRA.setdefault(EXTRA[s], collections.Counter())[src(*kk)] += n; continue
        S[s].setdefault("src", {}).setdefault(str(y), collections.Counter())[src(*kk)] += n
for y, c in ITEMS.items():
    tot = sum(c.values()); g = collections.Counter()
    for kk, v in c.items(): g[src(*kk)] += v
    print(y, tot, {a: (g[a], round(g[a] / tot * 100, 1)) for a in SRCS}, "정점", sum(1 for s in S.values() if str(y) in s.get("src", {})))
def icon(cls, mat, det):
    if cls == "외국기인": return "foreign"
    if cls == "유리": return "glass"
    if cls == "금속": return "can"
    if cls == "목재": return "wood"
    if cls in ("고무", "기타(+혼합재질)"): return "misc"
    if cls in ("종이",) or "1회용" in det: return "cup"
    if "천연" in cls or det.startswith("옷"): return "cloth"
    if "부표" in det: return "buoy"
    if any(w in det for w in ("밧줄", "끈", "어망", "그물", "낚싯줄")) or mat == "섬유형": return "rope"
    if "담배" in det: return "butt"
    if mat == "발포형": return "foam"
    if mat == "필름형": return "bag"
    if any(w in det for w in ("음료수병", "용기", "세제", "농약", "약병")): return "bottle"
    if "파편" in det or "기타 플라스틱" in det: return "frag"
    return "misc"
GAME = collections.Counter()
for y, c in ITEMS.items():
    for kk, v in c.items(): GAME[(icon(*kk), src(*kk))] += v
print("줍기 판", sorted(GAME.items(), key=lambda z: -z[1]))
TOPITEMS = {str(y): [[kk[0], kk[1], kk[2], v, src(*kk)] for kk, v in c.most_common(40)] for y, c in ITEMS.items()}
# 바다별
print("\n바다별 2018–2023 정점당 연평균")
for sv in ("서해", "남해", "동해", "제주"):
    ss = [s for s in S.values() if s["sea"] == sv]; n = len(ss); sy = sum(1 for s in ss for v in s["cnt"] if v > 0)   # 조사한 정점·해만
    c = sum(sum(s["cnt"]) for s in ss) / sy; k = sum(sum(s["kg"]) for s in ss) / sy
    fr = collections.Counter(XTRA.get(sv, {}))
    for s in ss:
        for y, cc in s.get("src", {}).items(): fr.update(cc)
    ft = sum(fr.values()) or 1
    print(f"  {sv} {n}곳 정점·해 {sy} 개수 {c:.0f} 무게 {k:.1f}kg | 외국 {fr['외국'] / ft * 100:.1f}% 바다 {fr['바다'] / ft * 100:.1f}% 육지 {fr['육지'] / ft * 100:.1f}% (항목 {ft})")
fs_ = sorted((s for s in S.values() if s.get("src")), key=lambda s: -sum(c["외국"] for c in s["src"].values()) / sum(sum(c.values()) for c in s["src"].values()))
print("외국 비중 높은 정점", [(s["n"], round(sum(c["외국"] for c in s["src"].values()) / sum(sum(c.values()) for c in s["src"].values()) * 100, 1), sum(c["외국"] for c in s["src"].values())) for s in fs_[:10]])
print("외국 0인 정점 수", sum(1 for s in fs_ if sum(c["외국"] for c in s["src"].values()) == 0), "/", len(fs_))
top = sorted(S.values(), key=lambda s: -sum(s["kg"])); print("무게 많은 정점", [(s["n"], round(sum(s["kg"]))) for s in top[:8]]); print("적은", [(s["n"], round(sum(s["kg"]), 1)) for s in top[-5:]])
topc = sorted(S.values(), key=lambda s: -sum(s["cnt"])); print("개수 많은 정점", [(s["n"], round(sum(s["cnt"]))) for s in topc[:8]])
print("조사 정점 수", [sum(1 for s in S.values() if s["cnt"][j] > 0) for j in range(len(YS))]); print("연도별 전국 개수", [round(sum(s["cnt"][j] for s in S.values())) for j in range(len(YS))], "무게", [round(sum(s["kg"][j] for s in S.values())) for j in range(len(YS))])
for s in S.values(): s["xy"] = XY[s["n"]]; s["src"] = {y: dict(c) for y, c in s.get("src", {}).items()}
SEASRC = {}
for sv in ("서해", "남해", "동해", "제주"):
    fr = collections.Counter(XTRA.get(sv, {}))
    for s in S.values():
        if s["sea"] == sv:
            for cc in s["src"].values(): fr.update(cc)
    SEASRC[sv] = dict(fr)
sys.path.insert(0, os.path.join(H, "..")); import geo_sido
out = {"game": [[a, b, v] for (a, b), v in GAME.most_common()], "geo": geo_sido.geo(), "seaSrc": SEASRC, "YS": YS, "sites": list(S.values()), "types": TYPES, "season": SEASON, "y1": Y1, "items": TOPITEMS, "srcs": SRCS}
json.dump(out, open(os.path.join(H, "q46_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(os.path.getsize(os.path.join(H, "q46_data.json")))
