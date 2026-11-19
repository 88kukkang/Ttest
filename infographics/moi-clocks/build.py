"""행안부 보도자료 DB(3,648건)에서 인포그래픽 세 장의 숫자를 만든다.
입력: ../web/docs.bin (DB 페이지의 docs.b64.txt를 풀어 놓은 JSON), ../dataset/attachments.csv (첨부 파일명)
출력: viz_data.json
"""
import json, re, collections, datetime as dt, csv, os
H = os.path.dirname(os.path.abspath(__file__))
docs = json.load(open(f"{H}/../web/docs.bin", encoding="utf-8"))["docs"]   # [ntt, date, dept, title, text]
FIRST, LAST = min(d[1] for d in docs), max(d[1] for d in docs)

# ---- 1. 자연재난: 제목에 나온 재난 종류 (앞에 있는 규칙이 먼저) ----
NAT = [("fire", "산불", r"산불"), ("quake", "지진", r"지진"), ("typhoon", "태풍·강풍", r"태풍|강풍|풍랑"),
       ("rain", "호우·장마", r"호우|장마|폭우|홍수|침수|산사태|우기|풍수해"), ("heat", "폭염", r"폭염|무더위|열대야"),
       ("snow", "대설·한파", r"대설|폭설|한파|강추위|동파"), ("drought", "가뭄", r"가뭄")]
NATRE = re.compile("|".join(p for _, _, p in NAT))
SOC = re.compile(r"화재|사고|참사|붕괴|폭발|전산장애|전산실|전산망|장애(?!인)|정전|오물|풍선|침몰|추락|유출|인파|테러|싱크홀|땅꺼짐")
nat, soc = [], []
for ntt, d, dept, title, text in docs:
    t = title.strip()
    for k, _, p in NAT:
        if re.search(p, t):
            nat.append([d, k, ntt, t]); break
    else:
        if SOC.search(t): soc.append([d, ntt, t])

def conc(rows, key=lambda r: r[0]):
    """2024·2025년 두 해를 달별로 합쳐, 연달은 석 달에 몰린 최대 비율."""
    m = collections.Counter(int(key(r)[5:7]) for r in rows if key(r)[:4] in ("2024", "2025"))
    tot = sum(m.values()); best = max(range(1, 13), key=lambda s: sum(m[(s + i - 1) % 12 + 1] for i in range(3)))
    return {"share": round(100 * sum(m[(best + i - 1) % 12 + 1] for i in range(3)) / tot, 1), "start": best, "n": tot,
            "months": [m[i] for i in range(1, 13)]}

natStat = {k: conc([r for r in nat if r[1] == k]) for k, _, _ in NAT}
natStat["all"] = conc(nat); socStat = conc(soc)

# 주별 사회재난 수 (월요일 시작)
def monday(s): D = dt.date.fromisoformat(s); return D - dt.timedelta(D.weekday())
w0, w1 = monday(FIRST), monday(LAST)
weeks = []; w = w0
while w <= w1: weeks.append(w); w += dt.timedelta(7)
sw = collections.Counter(monday(r[0]) for r in soc); nw = collections.Counter(monday(r[0]) for r in nat)
weekly = [[str(w), sw[w], nw[w]] for w in weeks]

# ---- 3. 보도 시점: 첨부 파일명 앞 "YYMMDD (조간)" ----
first = {}
for r in csv.DictReader(open(f"{H}/../dataset/attachments.csv", encoding="utf-8-sig")):
    k = r["ntt_id"]
    if k not in first or int(r["seq"]) < int(first[k]["seq"]): first[k] = r
title_of = {d[0]: d[3] for d in docs}; pub_of = {d[0]: d[1] for d in docs}
pat = re.compile(r"(\d{6})[\s+★]*\(([^)]*)\)")
def kind(s):
    s = s.replace(" ", "").replace("+", "").replace("★", "")
    m = re.fullmatch(r"(?:[월화수목금토일])?(\d{1,2})시(\d{2})?분?(?:보도가능)?", s)
    if m: return "hour", int(m.group(1)) + (int(m.group(2)) / 60 if m.group(2) else 0)
    if "조간" in s: return "morning", None
    if "석간" in s: return "evening", None
    if s.startswith("즉시"): return "now", None
    if "참고" in s: return "ref", None
    if re.search(r"종료|시작|의결|이후|발표", s): return "event", s
    return None, s
emb = []; skipped = collections.Counter()
for k, r in first.items():
    m = pat.search(r["filename"] or "")
    if not m: skipped["표시 없음"] += 1; continue
    kd, v = kind(m.group(2))
    try: D = dt.datetime.strptime("20" + m.group(1), "%Y%m%d").date()
    except ValueError: skipped["날짜 오류"] += 1; continue
    if k not in pub_of or abs((D - dt.date.fromisoformat(pub_of[k])).days) > 10: skipped["날짜 불일치"] += 1; continue
    if kd is None: skipped["기타 표기"] += 1; continue
    ev = None
    if kd == "event": ev = "국무회의" if "국무회의" in v else ("국회 의결" if "의결" in v else ("브리핑" if "브리핑" in v else "기타 행사"))
    emb.append([str(D), D.weekday(), kd, round(v, 2) if kd == "hour" else None, ev, k, title_of.get(k, "")])
emb.sort()
E = {"n": len(emb), "first": emb[0][0], "last": emb[-1][0], "skipped": dict(skipped), "total": len(first)}
grid = collections.Counter((e[2], e[1]) for e in emb)
E["grid"] = {f"{a}|{b}": c for (a, b), c in grid.items()}
E["hours"] = dict(sorted(collections.Counter(int(e[3]) for e in emb if e[2] == "hour").items()))
E["events"] = dict(collections.Counter(e[4] for e in emb if e[4]))
E["evday"] = dict(collections.Counter(f"{e[4]}|{e[1]}" for e in emb if e[4]))

out = {"first": FIRST, "last": LAST, "n_docs": len(docs),
       "natTypes": [[k, n] for k, n, _ in NAT], "nat": nat, "natStat": natStat,
       "soc": soc, "socStat": socStat, "weekly": weekly, "emb": emb, "E": E}
json.dump(out, open(f"{H}/viz_data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(nat), len(soc), E["n"], E["skipped"], os.path.getsize(f"{H}/viz_data.json"))
print({k: (v["share"], v["start"], v["n"]) for k, v in natStat.items()}, (socStat["share"], socStat["start"], socStat["n"]))
print(sorted(E["grid"].items())); print(E["hours"]); print(E["events"], E["evday"])

# ---- 사회재난 큰 사건: 제목 키워드로 묶음 (사건 이름은 제목에 쓰인 말) ----
EVENTS = [("서천특화시장 화재", r"서천", "2024-01-22", "2024-02-29"), ("화성 공장 화재", r"화성", "2024-06-24", "2024-07-31"),
          ("제주항공 여객기 사고", r"제주항공|여객기|항공기|무안", "2024-12-29", "2025-03-31"),
          ("국가정보자원관리원 화재·전산장애", r"국가정보자원관리원|국정자원|전산장애|전산실|정보시스템|행정서비스|장애(?!인)", "2025-09-26", "2025-12-31"),
          ("대전 대덕구 공장 화재", r"대전|대덕", "2026-03-20", "2026-06-30"), ("10·29 이태원참사", r"이태원", "2024-01-01", "2026-12-31"),
          ("핼러윈·인파 관리", r"핼러윈|인파", "2024-01-01", "2026-12-31")]
ev = []
for name, p, a, b in EVENTS:
    rows = [r for r in soc if re.search(p, r[2]) and a <= r[0] <= b]
    if not rows: continue
    pk = collections.Counter(str(monday(r[0])) for r in rows).most_common(1)[0]
    ev.append({"name": name, "n": len(rows), "first": min(r[0] for r in rows),
               "last": max(r[0] for r in rows), "peak": pk[0], "peakN": pk[1], "oct": round(sum(r[0][5:7] == "10" for r in rows) / len(rows), 2)})
ev.sort(key=lambda e: -e["n"])
top10 = sorted((w[1] for w in weekly), reverse=True)[:10]
SUN = [e for e in emb if e[1] == 6]
disaster = lambda t: bool(NATRE.search(t) or SOC.search(t) or re.search(r"중앙재난안전대책본부|중대본|긴급", t))
out["events"] = ev
out["socTop10"] = {"weeks": len(weekly), "n": sum(top10), "share": round(100 * sum(top10) / len(soc), 1)}
out["sunday"] = {"n": len(SUN), "now": sum(e[2] == "now" for e in SUN), "disaster": sum(disaster(e[6]) for e in SUN)}
wkTot = collections.Counter(e[1] for e in emb); out["E"]["byDay"] = [wkTot[i] for i in range(7)]
json.dump(out, open(f"{H}/viz_data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print([(e["name"],e["n"],e["first"],e["last"],e["peak"],e["peakN"]) for e in ev]); print(out["socTop10"], out["sunday"], out["E"]["byDay"])
