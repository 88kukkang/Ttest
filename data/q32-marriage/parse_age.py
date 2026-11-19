"""Husband age x wife age marriages per year from KOSIS DT_1B83A02 (age_YYYY.html) -> age.json {year: {hAge: {wAge: n}}}"""
import sys, re, json, glob, os
sys.path.insert(0, os.path.dirname(__file__))
from kosis_table import rows, num
out = {}
for f in sorted(glob.glob(f"{sys.argv[1]}/age_*.html")):
    y = re.search(r"age_(\d{4})", f).group(1); h = None; d = {}
    for r in rows(f)[2:]:
        if len(r) < 3: continue
        if r[0]: h = r[0]
        v = num(r[2])
        if v is not None: d.setdefault(h, {})[r[1]] = v
    out[y] = d
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
print(len(out), list(out["2025"].keys())[:50]); print(list(out["2025"]["30세"].keys()))
