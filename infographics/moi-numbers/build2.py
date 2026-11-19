"""행안부 보도자료 DB에서 '발표 내용' 인포그래픽 세 장의 숫자를 뽑는다. 모든 숫자는 보도자료 본문에 실린 값이다.
입력: ../web/docs.bin, race_raw.json(race.py 결과)  출력: data2.json"""
import json, re, os
H = os.path.dirname(os.path.abspath(__file__))
docs = json.load(open(f"{H}/../web/docs.bin", encoding="utf-8"))["docs"]
def eok(s):
    """'84조 7,036억' / '1조' / '2,371억' → 억 원"""
    s = s.replace(" ", ""); jo = re.search(r"([\d,.]+)조", s); ek = re.search(r"([\d,.]+)억", s)
    return (float(jo.group(1).replace(",", "")) * 1e4 if jo else 0) + (float(ek.group(1).replace(",", "")) if ek else 0)
def doc(date, pat):
    r = [d for d in docs if d[1] == date and re.search(pat, d[3])]; assert len(r) == 1, (date, pat, len(r)); return r[0]
def find(t, pat):
    m = re.search(pat, t); assert m, pat; return m

# ---------- 1. 예산 ----------
B = {}
d = doc("2024-12-11", "2025년도 행정안전부 예산안 72조"); t = d[4]
m = find(t, r"지방교부세\s*([\d조,\s]+억)\s*원,\s*사업비\s*([\d조,\s]+억)\s*원,\s*기본경비·인건비\s*([\d조,\s]+억)")
B["2025"] = {"label": "2025 확정", "total": eok(find(d[3], r"([\d조,\s]+억)\s*원")[1]), "grant": eok(m[1]), "prog": eok(m[2]), "base": eok(m[3]), "ntt": d[0], "date": d[1]}
d = doc("2025-12-03", "2026년 행정안전부 예산"); t = d[4]
m = find(t, r"지방교부세\s*([\d조,\s]+억)\s*원,\s*기본경비·인건비\s*([\d조,\s]+억)\s*원,\s*사업비\s*([\d조,\s]+억)")
B["2026"] = {"label": "2026 확정", "total": eok(find(d[3], r"([\d조,\s]+억)\s*원")[1]), "grant": eok(m[1]), "base": eok(m[2]), "prog": eok(m[3]), "ntt": d[0], "date": d[1]}
d = doc("2026-09-02", "2027년 예산안"); t = d[4]
m = find(t, r"지방교부세가\s*([\d조,\s]+억)\s*원으로.*?사업비\s*([\d조,\s]+억)\s*원,\s*인건비 및 기본경비\s*([\d조,\s]+억)")
B["2027"] = {"label": "2027 정부안", "total": eok(find(d[3], r"([\d조,\s]+억)\s*원")[1]), "grant": eok(m[1]), "prog": eok(m[2]), "base": eok(m[3]), "ntt": d[0], "date": d[1]}
body = t[t.index("예산안 주요 사업 개요"):]
heads = list(re.finditer(r"\n(\d)\.\s*([^:\n]+?)\s*:\s*([\d조,\s]+억)\s*원", body))
fields = []
for i, h in enumerate(heads):
    seg = body[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(body)]
    items = [{"name": a.strip(), "v": eok(b)} for a, b in re.findall(r"○\s*\(([^:]+?):\s*([\d조,\s]+(?:억)?)\s*원\)", seg)]
    fields.append({"name": h[2].strip(), "v": eok(h[3]), "items": items})
B["fields2027"] = fields
for y in ("2025", "2026", "2027"):
    b = B[y]; assert abs(b["grant"] + b["prog"] + b["base"] - b["total"]) < 2, (y, b)
assert abs(sum(f["v"] for f in fields) - B["2027"]["prog"]) < 2
# 추경 (확정)
SUP = []
for date, pat in [("2025-05-01", "추가경정예산 1조"), ("2025-07-05", "제2회 추경예산"), ("2026-04-12", "추가경정예산 9조")]:
    d = doc(date, pat); SUP.append({"date": date, "title": d[3], "v": eok(find(d[3], r"([\d조,\s]+억)\s*원")[1]), "ntt": d[0]})
B["supp"] = SUP

# ---------- 2. 지원금 레이스 ----------
raw = json.load(open(f"{H}/race_raw.json", encoding="utf-8"))
import datetime as dt
START = {"c1": "2025-07-21", "c2": "2025-09-22", "o1": "2026-04-27", "o2": "2026-05-18"}
def el(r, k): return round((dt.date.fromisoformat(r["at"]) - dt.date.fromisoformat(START[k])).days + (r["hour"] - 9) / 24, 3)
R = {k: [] for k in START}
for r in raw:
    if r["prog"] == "coupon":
        k = "c1" if r["at"] <= "2025-09-12" else "c2"; R[k].append([el(r, k), r["pct"], r["ntt"], r["at"], r["hour"]])
    else:
        if r["at"] <= "2026-05-08": R["o1"].append([el(r, "o1"), r["pct"], r["ntt"], r["at"], r["hour"]])
        else:
            if "pct1" in r: R["o1"].append([el(r, "o1"), r["pct1"], r["ntt"], r["at"], r["hour"]])
            if "pct2" in r: R["o2"].append([el(r, "o2"), r["pct2"], r["ntt"], r["at"], r["hour"]])
# 5.18 2차 대상자 신청률은 보도자료에 없어 표의 누계에서 계산: (누계 신청자 − 1차 대상자 신청자) ÷ (누계 대상자 − 1차 대상자)
r518 = next(r for r in raw if r["at"] == "2026-05-18")
txt = next(d[4] for d in docs if d[0] == r518["ntt"])
p1n = float(find(txt, r"\(1차 대상자\)\s*총\s*([\d.]+)만\s*명")[1]) * 1e4
o1tot = next(r for r in raw if r["at"] == "2026-05-08")["rows"]["계"][6]
tot = r518["rows"]["계"]
R["o2"].insert(0, [el(r518, "o2"), round(100 * (tot[0] - p1n) / (tot[6] - o1tot), 1), r518["ntt"], r518["at"], r518["hour"], "계산"])
# 마감 시점 시도별 지급 방식
FIN = {"c1": "2025-09-12", "c2": "2025-10-31", "o": "2026-07-03"}
pay = {}
for k, at in FIN.items():
    r = next(x for x in raw if x["at"] == at and "rows" in x)
    pay[k] = {"ntt": r["ntt"], "at": at, "rows": r["rows"]}
RACE = {"series": R, "pay": pay, "meta": {"c1": {"name": "소비쿠폰 1차", "who": "전 국민", "target": next(x for x in raw if x["at"] == "2025-09-12")["rows"]["계"][6]},
        "c2": {"name": "소비쿠폰 2차", "who": "국민 90%", "target": next(x for x in raw if x["at"] == "2025-10-31")["rows"]["계"][6]},
        "o1": {"name": "고유가 피해지원금 1차", "who": "취약계층", "target": o1tot},
        "o2": {"name": "고유가 피해지원금 2차", "who": "국민 70%", "target": tot[6] - o1tot}}}

# ---------- 3. 생활인구 ----------
LP = []   # [월, 생활인구(만), 체류/등록 배수 or None, 출처 ntt]
def lp_months(date, pat, year_of):
    d = doc(date, pat)
    for m in re.finditer(r"(\d{1,2})월\s*약\s*(\d)천\s*(\d{1,3})만\s*명", d[4][:6000]):
        mo = int(m[1]); LP.append([f"{year_of(mo)}-{mo:02d}", int(m[2]) * 1000 + int(m[3]), None, d[0]])
lp_months("2025-12-09", "한눈에 보는 생활인구", lambda m: 2025)
lp_months("2026-02-24", "인구감소지역 20곳", lambda m: 2025)
lp_months("2026-05-28", "10월 황금연휴", lambda m: 2025)
lp_months("2026-07-30", "2026년 1분기 생활인구", lambda m: 2026)
lp_months("2026-10-29", "2026년 5월 생활인구", lambda m: 2026)
seen = {}; [seen.setdefault(x[0], x) for x in LP]; LP = sorted(seen.values())
# 배수: 2026년은 표의 배수(B/A) 행, 2025년 2분기는 본문 문장
# 표의 세 열은 그 분기의 세 달 순서다(1분기 1·2·3월, 2분기 4·5·6월)
for date, pat, mons in [("2026-07-30", "2026년 1분기 생활인구", ["2026-01", "2026-02", "2026-03"]), ("2026-10-29", "2026년 5월 생활인구", ["2026-04", "2026-05", "2026-06"])]:
    d = doc(date, pat); t = d[4]
    vals = find(t, r"배수\(B/A\)\s*\n([\d.]+)\s*\n[-\d.]+\s*\n[-\d.]+\s*\n([\d.]+)\s*\n[-\d.]+\s*\n[-\d.]+\s*\n([\d.]+)")
    reg = find(t, r"등록인구\(A\)\s*\n([\d,]+)\s*\n[-\d,]+\s*\n[-\d,]+\s*\n([\d,]+)\s*\n[-\d,]+\s*\n[-\d,]+\s*\n([\d,]+)")
    for mo, v, rg in zip(mons, vals.groups(), reg.groups()):
        x = next(x for x in LP if x[0] == mo); x[2] = float(v); x.append(int(rg.replace(",", "")) / 10)
d = doc("2025-12-09", "한눈에 보는 생활인구"); t = d[4]
for mo, pat in [(4, r"배수는\s*([\d.]+)배이며,\s*전달인 3월"), (5, r"5월은[^\n]*?배수는\s*([\d.]+)배"), (6, r"6월은[^\n]*?배수는\s*([\d.]+)배")]:
    v = float(find(t, pat)[1]); next(x for x in LP if x[0] == f"2025-{mo:02d}")[2] = v
# 기록 지역 (본문 문장)
REC = []
d = doc("2024-07-25", "490만여 명"); REC.append({"place": "전남 구례군", "x": float(find(d[4], r"구례군은 체류 인구가 등록인구의\s*([\d.]+)배")[1]), "when": "2024년 1분기", "ntt": d[0]})
d = doc("2024-10-30", "2천 360만 체류인구"); REC.append({"place": "강원 양양군", "x": float(find(d[4], r"양양군 체류인구는 등록인구 대비\s*([\d.]+)배")[1]), "when": "2024년 2분기", "ntt": d[0]})
d = doc("2026-10-29", "2026년 5월 생활인구"); REC.append({"place": "강원 양양군", "x": float(find(d[4], r"양양은 2026년 5월 등록인구의\s*([\d.]+)배")[1]), "when": "2026년 5월", "ntt": d[0]})
regA = float(find(d[4], r"등록인구\(약\s*([\d.]+)만 명\)")[1])
LIFE = {"months": LP, "records": REC, "reg2026_5": regA,
        "peak": max(LP, key=lambda x: x[1])}
out = {"budget": B, "race": RACE, "life": LIFE, "titles": {}}
need = {b["ntt"] for b in [B["2025"], B["2026"], B["2027"]]} | {s["ntt"] for s in SUP} | {x[2] for k in R for x in R[k]} | {p["ntt"] for p in pay.values()} | {x[3] for x in LP} | {r["ntt"] for r in REC}
out["titles"] = {d[0]: [d[1], d[3]] for d in docs if d[0] in need}
json.dump(out, open(f"{H}/data2.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(json.dumps({y: B[y] for y in ("2025", "2026", "2027")}, ensure_ascii=False)); print([(f["name"], f["v"], len(f["items"]), sum(i["v"] for i in f["items"])) for f in fields]); print(SUP)
for k in R: print(k, [(x[0], x[1]) for x in R[k]])
print(LP); print(REC, regA)
