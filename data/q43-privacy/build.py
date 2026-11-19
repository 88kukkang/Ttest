"""#43 계산: 개인정보 유출 사고의 원인과 개인이 신고·상담한 침해의 유형.
입력(raw/): enforcement_15177148.xlsx(개인정보보호위원회 조사 및 처분 통계, 2026 상반기), complaints_15119353.zip(침해 신고센터 신고·상담),
survey_15119394.zip(일반국민 침해 경험 실태), incidents_15140309.csv(민간 침해사고 신고), leak_report_2024.json(KISA 보고서에서 옮긴 숫자).
출력: q43_data.json"""
import os, re, io, csv, json, zipfile, html
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
def dec(b):
    for enc in ("utf-8-sig", "cp949"):
        try: return b.decode(enc)
        except UnicodeDecodeError: pass
def zcsv(fn):
    z = zipfile.ZipFile(os.path.join(R, fn)); out = {}
    for i in z.infolist():
        try: nm = i.filename.encode("cp437").decode("cp949")
        except Exception: nm = i.filename
        out[nm] = [[c.strip() for c in r] for r in csv.reader(io.StringIO(dec(z.read(i)))) if r]
    return out
n = lambda s: 0 if s in ("-", "") else float(s) if "." in s else int(s)
# ── 조사·처분 통계 xlsx ──
z = zipfile.ZipFile(os.path.join(R, "enforcement_15177148.xlsx"))
ss = [html.unescape(re.sub(r"<[^>]+>", "", m)) for m in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf8"), re.S)]
def sheet(kk):
    rows = []
    for row in re.findall(r"<row [^>]*>(.*?)</row>", z.read(f"xl/worksheets/sheet{kk}.xml").decode("utf8"), re.S):
        out = []
        for a, b in re.findall(r"<c ([^>]*?)(?:/>|>(.*?)</c>)", row, re.S):
            v = re.search(r"<v>(.*?)</v>", b or "")
            if v: out.append(re.sub(r"\s+", " ", ss[int(v.group(1))]).strip() if 't="s"' in a else v.group(1))
        if out: rows.append(out)
    return rows
s1 = sheet(1); yrs = s1[0][1:]; print(yrs)
get = lambda rows, key, skip: [n(v) for v in next(r for r in rows if key in r)[skip:]]
orgs = {"민간": [n(v) for v in s1[1][-7:]], "공공": [n(v) for v in s1[2][-7:]], "합계": [n(v) for v in s1[3][-7:]]}
recs = {"민간": [n(v) for v in s1[4][-7:]], "공공": [n(v) for v in s1[5][-7:]], "합계": [n(v) for v in s1[6][-7:]]}
assert all(a + b == c for a, b, c in zip(orgs["민간"], orgs["공공"], orgs["합계"])) and all(a + b == c for a, b, c in zip(recs["민간"], recs["공공"], recs["합계"]))
s3 = sheet(3); sub = s3[1]; GROUP = ["해킹"] * 4 + ["업무 과실"] * 4 + ["시스템 오류"] * 4 + ["기타"]
names = ["SQL 인젝션", "악성코드", "웹셸", "그 밖의 해킹", "접근통제 미설정", "이메일 오발송", "개인정보 파일 게시", "그 밖의 과실", "소스코드 오류", "접근권한 미확인", "연동 오류", "그 밖의 오류", "기타"]
print(sub)
TYPES = {}
for r in s3[2:]:
    key = r[0].split(" ")[0].replace("(단위", "").strip(); vals = [n(v) for v in r[2:]]; assert len(vals) == 13 and sum(vals) == n(r[1]), r; TYPES[key] = vals
assert all(a + b == c for a, b, c in zip(TYPES["민간"], TYPES["공공"], TYPES["합계"]))
s4 = sheet(4); fines = {"y": s4[0][2:], "pen_n": [n(v) for v in s4[1][-7:]], "pen_amt": [n(v) for v in s4[2][-7:]], "fine_n": [n(v) for v in s4[3][-7:]], "fine_amt": [n(v) for v in s4[4][-7:]]}
s2 = sheet(2); disp = {"민간": [n(v) for v in s2[1][-7:]], "공공": [n(v) for v in s2[2][-7:]]}
# ── 신고·상담 ──
c = zcsv("complaints_15119353.zip"); q = next(v for kk, v in c.items() if "접수유형" in kk); yr = next(v for kk, v in c.items() if "신고·상담 현황" in kk); pr = next(v for kk, v in c.items() if "처리" in kk)
CT = q[0][1:-1]; Q = [{"q": r[0], "v": [n(v) for v in r[1:-1]], "tot": n(r[-1])} for r in q[1:]]
for r in Q: assert sum(r["v"]) == r["tot"], r
YR = [{"y": int(r[0][:4]), "report": n(r[1]), "consult": n(r[2]), "tot": n(r[3])} for r in yr[1:]]
sv = zcsv("survey_15119394.zip"); SV = {kk.replace(".csv", ""): v for kk, v in sv.items()}
inc = list(csv.reader(io.StringIO(dec(open(os.path.join(R, "incidents_15140309.csv"), "rb").read()))))
INC = {h_: n(v) for h_, v in zip(inc[0][1:], inc[1][1:])}
LEAK = json.load(open(os.path.join(R, "leak_report_2024.json"), encoding="utf-8"))
assert sum(LEAK["cause_2024"].values()) == 307 and sum(LEAK["hack_type_2024"].values()) == 171 and sum(LEAK["cause_public_2024"].values()) == 104 and sum(LEAK["cause_private_2024"].values()) == 203
out = {"years": yrs, "orgs": orgs, "recs": recs, "types": TYPES, "typeNames": names, "typeGroup": GROUP, "fines": fines, "disp": disp, "CT": CT, "Q": Q, "YR": YR, "survey": SV, "incidents": INC, "leak": LEAK, "proc": pr}
json.dump(out, open(os.path.join(H, "q43_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
# ── 요약 ──
for key in ("합계", "민간", "공공"):
    v = TYPES[key]; g = {}
    for a, b in zip(GROUP, v): g[a] = g.get(a, 0) + b
    print(key, sum(v), g, {a: round(b / sum(v) * 100, 1) for a, b in g.items()})
print("세부 순위", sorted(zip(names, TYPES["합계"]), key=lambda x: -x[1]))
print("유출 기관 수", dict(zip(yrs, orgs["합계"])), "| 유출 건수(천)", dict(zip(yrs, recs["합계"])), "합", sum(recs["합계"]))
print("기관당 평균 유출 건수(천)", {y: round(b / a, 1) for y, a, b in zip(yrs, orgs["합계"], recs["합계"])})
y22 = [r for r in Q if r["q"].startswith("22")]; t22 = [sum(r["v"][j] for r in y22) for j in range(len(CT))]; print("2022 유형", sorted(zip(CT, t22), key=lambda x: -x[1]), sum(t22))
print("2022 비중", [(a, round(b / sum(t22) * 100, 1)) for a, b in sorted(zip(CT, t22), key=lambda x: -x[1])])
print("연도", YR); print("과징금", fines); print("침해사고", INC)
for kk, v in SV.items():
    print(kk)
    for r in v: print("  ", r)
