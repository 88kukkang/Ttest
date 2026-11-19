"""#40 계산: 수능 접수현황(한국교육과정평가원 15098903)·응시현황(15098904), 1994~2026학년도.
1994학년도는 시험을 두 번 봤다(8월·11월): 2차(11월)를 쓴다. 출력: q40_data.json"""
import os, csv, io, json
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
def rd(f):
    b = open(os.path.join(R, f), "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try: return list(csv.reader(io.StringIO(b.decode(enc))))
        except UnicodeDecodeError: pass
a = rd("csat_applicants.csv"); h = [c.strip() for c in a[0]]; print(h)
Y = {}
for x in a[1:]:
    d = dict(zip(h, [c.strip() for c in x])); y = int(d["학년도"])
    Y[y] = {"y": y, "tot": int(d["총 계"]), "m": int(d["남"]), "f": int(d["여"]), "cur": int(d["재학생"]), "grad": int(d["졸업생"]), "ged": int(d["검정등"]), "fee": d.get("5개 영역 응시수수료") or d.get("4개 영역 응시수수료"), "per": d["기간(1)"]}
t = rd("csat_takers.csv"); th = [c.strip() for c in t[0]]
for x in t[1:]:
    d = dict(zip(th, [c.strip() for c in x])); y = int(d["학년도"])
    Y[y].update({"app": int(d["지원인원(명)"]), "took": int(d["응시인원(명)"]), "rate": float(d["응시율(퍼센트)"]), "date": d["시험일정"]})
rows = [Y[y] for y in sorted(Y)]
for r in rows:
    assert r["cur"] + r["grad"] + r["ged"] == r["tot"], r
    assert r["app"] == r["tot"], r
    r["gs"] = r["grad"] / r["tot"] * 100; r["ges"] = r["ged"] / r["tot"] * 100; r["ns"] = (r["grad"] + r["ged"]) / r["tot"] * 100
    print(r["y"], f"{r['tot']:,}", f"재학 {r['cur']:,} 졸업 {r['grad']:,} 검정 {r['ged']:,} | 졸업생 {r['gs']:.1f}% 검정 {r['ges']:.1f}% 합 {r['ns']:.1f}% | 응시율 {r['rate']} 결시 {r['app'] - r['took']:,}")
json.dump({"rows": rows}, open(os.path.join(H, "q40_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
mx = max(rows, key=lambda r: r["gs"]); mn = min(rows, key=lambda r: r["gs"]); print("졸업생 비중 최고", mx["y"], mx["gs"], "최저", mn["y"], mn["gs"])
mx = max(rows, key=lambda r: r["grad"]); mn = min(rows, key=lambda r: r["grad"]); print("졸업생 수 최다", mx["y"], mx["grad"], "최소", mn["y"], mn["grad"])
mx = max(rows, key=lambda r: r["tot"]); print("지원자 최다", mx["y"], mx["tot"]); mx = max(rows, key=lambda r: r["ged"]); print("검정 최다", mx["y"], mx["ged"])
