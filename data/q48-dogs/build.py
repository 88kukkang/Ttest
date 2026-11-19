"""#48 계산: 시군구(229곳, 일반구는 시로 합침)별 등록된 개·고양이 누계(2022년 말)를 주민등록 세대수·인구로 나눈다.
입력: raw/pets_20221231.csv (15125454의 2022.12.31 판; 2023.12.08 '수정' 판도 값이 같다), raw/pop_*.json, raw/hh_*.json (fetch.py).
출력: q48_data.json"""
import os, sys, csv, io, json, re, statistics as st
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
sys.path.insert(0, os.path.join(H, "..", "kosis")); sys.path.insert(0, os.path.join(H, "..")); import kosis_curl as k, geo_sido
G = json.load(open(os.path.join(H, "..", "q19-closures", "q19_data.json"), encoding="utf-8"))
places = [(p[0], p[1]) for p in G["P"]]; pidx = {p: i for i, p in enumerate(places)}
SH = {"서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구", "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전", "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
      "강원도": "강원", "강원특별자치도": "강원", "충청북도": "충북", "충청남도": "충남", "전라북도": "전북", "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주"}
ALIAS = {("세종", "세종특별자치시"): ("세종", "세종시"), ("세종", "조치원읍"): ("세종", "세종시"), ("경기", "여주군"): ("경기", "여주시"), ("충북", "청원군"): ("충북", "청주시"),
         ("충남", "당진군"): ("충남", "당진시"), ("경북", "군위군"): ("대구", "군위군"), ("경남", "창원"): ("경남", "창원시"), ("인천", "남구"): ("인천", "미추홀구")}
def place(sd, nm):
    nm = re.sub(r"^\d+\)", "", nm).strip(); c = (sd, nm.split(" ")[0]); c = ALIAS.get(c, c); return pidx.get(c)
b = open(os.path.join(R, "pets_20221231.csv"), "rb").read(); rows = list(csv.reader(io.StringIO(b.decode("cp949"))))
DOG = [0] * len(places); CAT = [0] * len(places); SIDO = {}
for x in rows[1:]:
    if not x[1]: SIDO[x[0]] = (int(x[2]), int(x[3])); continue
    i = place(SH[x[0]], x[1]); assert i is not None, x; DOG[i] += int(x[2]); CAT[i] += int(x[3])
nd, nc = sum(DOG), sum(CAT); print("개", nd, "고양이", nc, "시도 합", sum(v[0] for v in SIDO.values()), sum(v[1] for v in SIDO.values()))
PC = {"11": "서울", "26": "부산", "27": "대구", "28": "인천", "29": "광주", "30": "대전", "31": "울산", "36": "세종", "41": "경기", "51": "강원", "43": "충북", "44": "충남", "52": "전북", "46": "전남", "47": "경북", "48": "경남", "50": "제주"}
def den(tag):
    v = [0] * len(places); nat = None
    for code, sd in list(PC.items()) + [("00", "전국")]:
        r = k.table(os.path.join(R, f"{tag}_{code}.json")); first = True
        for x in r[2:]:
            if len(x) < 2: continue
            val = int(k.num(x[1]) or 0)
            if first:
                first = False
                if sd == "전국": nat = val
                if sd != "세종": continue
            elif sd == "세종": continue   # 세종은 첫 줄(시 전체)만 쓴다. 아래 읍·면·동 줄을 더하면 두 번 센다
            i = place(sd, x[0])
            if i is not None and val: v[i] += val
    return v, nat
POP, npop = den("pop"); HH, nhh = den("hh")
print("인구 합", sum(POP), npop, "세대 합", sum(HH), nhh, "없는 곳", [places[i] for i in range(len(places)) if not POP[i] or not HH[i]])
P = []
for i, (sd, nm) in enumerate(places):
    g = G["P"][i]; P.append({"s": sd, "n": nm, "x": g[2], "y": g[3], "codes": g[7], "dog": DOG[i], "cat": CAT[i], "pop": POP[i], "hh": HH[i]})
f = lambda p: p["dog"] / p["hh"] * 100
print(f"전국 100세대당 개 {nd / nhh * 100:.2f}, 1천 명당 {nd / npop * 1000:.1f}, 고양이 100세대당 {nc / nhh * 100:.2f}")
srt = sorted(P, key=f, reverse=True)
print("많은 곳", [(p["s"], p["n"], round(f(p), 1), p["dog"]) for p in srt[:12]])
print("적은 곳", [(p["s"], p["n"], round(f(p), 1), p["dog"]) for p in srt[-12:]])
print("개 수 많은 곳", [(p["s"], p["n"], p["dog"]) for p in sorted(P, key=lambda p: -p["dog"])[:8]])
print("고양이 많은 곳", [(p["s"], p["n"], p["cat"], round(p["cat"] / p["hh"] * 100, 2)) for p in sorted(P, key=lambda p: -p["cat"])[:8]])
for sd in ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]:
    ps = [p for p in P if p["s"] == sd]; print(f"  {sd} 100세대당 {sum(p['dog'] for p in ps) / sum(p['hh'] for p in ps) * 100:.1f} 고양이 {sum(p['cat'] for p in ps) / sum(p['hh'] for p in ps) * 100:.2f} 중앙값 {st.median(f(p) for p in ps):.1f}")
# 도시 대 군
gun = [p for p in P if p["n"].endswith("군")]; gu = [p for p in P if p["n"].endswith("구")]; si = [p for p in P if p["n"].endswith("시")]
for nm_, ps in (("구", gu), ("시", si), ("군", gun)): print(nm_, len(ps), round(sum(p["dog"] for p in ps) / sum(p["hh"] for p in ps) * 100, 1))
json.dump({"P": P, "U": G["U"], "sidoPaths": G["sidoPaths"], "geo": geo_sido.geo(), "nat": {"dog": nd, "cat": nc, "pop": npop, "hh": nhh}},
          open(os.path.join(H, "q48_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(os.path.getsize(os.path.join(H, "q48_data.json")))
