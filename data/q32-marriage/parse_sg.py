"""Sigungu marriages/divorces per year from KOSIS DT_1B8000I (sg_YYYY.html) -> sg.json"""
import sys, re, json, glob, os
sys.path.insert(0, os.path.dirname(__file__))
from kosis_table import rows, num
SIDO = ['서울특별시','부산광역시','대구광역시','인천광역시','광주광역시','대전광역시','울산광역시','세종특별자치시','경기도','강원특별자치도','충청북도','충청남도','전북특별자치도','전라남도','경상북도','경상남도','제주특별자치도']
src = sys.argv[1]
out = {}
for f in sorted(glob.glob(f"{src}/sg_*.html")):
    y = int(re.search(r"sg_(\d{4})", f).group(1)); R = rows(f)
    head = R[1]; ix = {k: head.index(k) + 1 for k in head}
    cur = None; d = {}
    for r in R[3:]:
        if not r or not r[0]: continue
        name = re.sub(r"^\d+\)", "", r[0]).strip()
        rec = {"m": num(r[ix["혼인건수 (건)"]]), "mr": num(r[ix["조혼인율 (천명당)"]]), "d": num(r[ix["이혼건수 (건)"]]), "dr": num(r[ix["조이혼율 (천명당)"]]), "b": num(r[ix["출생건수 (명)"]])}
        if name == "전국" or name.startswith("국"): d[name.replace(" ", "")] = rec; continue
        if name in SIDO: cur = name; d[name] = rec; continue
        d[f"{cur}|{name}"] = rec
    out[y] = d
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
print(len(out), {y: len(v) for y, v in out.items() if y in (2000, 2015, 2025)})
