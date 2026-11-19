"""Q30: winner bloc of every 읍면동 in six presidential elections (2002-2025)."""
import csv, io, collections, json, re
FILES = {2002: "e_15133805.csv", 2007: "e_15104365.csv", 2012: "e_2012.csv", 2017: "e_2017.csv", 2022: "e_2022.csv", 2025: "f.bin"}
CONS = ("한나라당", "새누리당", "자유한국당", "국민의힘")
LIB = ("새천년민주당", "대통합민주신당", "민주통합당", "더불어민주당")
SIDO = {"서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "경기": "경기도", "강원": "강원도", "충북": "충청북도", "충남": "충청남도", "전북": "전라북도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도", "제주": "제주특별자치도",
        "강원특별자치도": "강원도", "전북특별자치도": "전라북도", "제주도": "제주특별자치도"}
SPECIAL = re.compile(r"투표|잘못|합계|소계")


def load(f):
    t = open(f, "rb").read().decode("utf-8", "ignore"); t = t[t.find("시도명"):]
    return list(csv.DictReader(io.StringIO(t)))


def cand_bloc(c):
    if c.startswith(CONS): return "C"
    if c.startswith(LIB): return "L"
    return "O"


res = {}
for y, f in FILES.items():
    agg = collections.defaultdict(collections.Counter)
    for r in load(f):
        d = r["읍면동명"]
        if not d or SPECIAL.search(d) or not r["투표구명"]: continue
        sd = SIDO.get(r["시도명"], r["시도명"]); sd = SIDO.get(sd, sd)
        k = (sd, r["구시군명"].replace(" ", ""), d)
        try: v = int(float(r["득표수"] or 0))
        except ValueError: continue
        agg[k][r["후보자"]] += v
    out = {}
    for k, c in agg.items():
        cands = {n: v for n, v in c.items() if n not in ("선거인수", "투표수", "무효 투표수", "기권자수")}
        if not cands: continue
        valid = sum(cands.values())
        if valid == 0: continue
        win = max(cands, key=cands.get)
        cb = sum(v for n, v in cands.items() if cand_bloc(n) == "C"); lb = sum(v for n, v in cands.items() if cand_bloc(n) == "L")
        out["|".join(k)] = {"w": cand_bloc(win), "wn": win, "c": round(cb / valid * 100, 1), "l": round(lb / valid * 100, 1), "n": valid, "e": c.get("선거인수", 0)}
    res[y] = out
    print(y, len(out), collections.Counter(v["w"] for v in out.values()))
json.dump(res, open("units.json", "w"), ensure_ascii=False)
