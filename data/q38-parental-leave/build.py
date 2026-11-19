"""Build q38_data.json (parental leave) from KOSIS 101 육아휴직통계 files fetched by fetch.py and the 2025 EI benefit CSVs.
usage: python3 build.py <rawdir>"""
import json, os, sys, re, csv
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "..", "kosis"))
import kosis_curl as K
raw = sys.argv[1]
def tab(t, ncls):
    R = K.table(os.path.join(raw, t + ".json")); hdr = [re.sub(r"[^0-9]", "", x) for x in R[0][ncls:]]; prev = [None] * ncls; d = {}
    for r in R[1:]:
        if len(r) <= ncls or all(K.num(x) is None for x in r[ncls:]): continue
        lab = [r[i].strip() or prev[i] for i in range(ncls)]; prev = lab
        d["|".join(lab)] = {int(y): K.num(v) for y, v in zip(hdr, r[ncls:])}
    return d
out = {}
for t, n in [("A001", 1), ("A002", 2), ("A003", 2), ("A004", 2), ("A005", 2), ("B001", 1), ("B002", 1), ("B003", 2), ("B004", 2), ("B005", 2),
             ("C001", 1), ("C002", 1), ("C003", 2), ("C004", 2), ("C005", 2), ("D001", 1), ("D002", 2), ("D003", 2), ("D004", 2), ("E001", 2), ("E002", 2), ("F001", 1)]:
    try: out[t] = tab(t, n)
    except Exception as e:
        try: out[t] = tab(t, 1)
        except Exception as e2: print(t, "fail", e2)
def ei(fn):
    R = list(csv.reader(open(os.path.join(H, fn), encoding="cp949"))); return {r[0]: [int(x) for x in r[1:]] for r in R[1:]}
out["ei2025"] = {"sex": ei("ei_15100479_sex_2025_cp949.csv"), "region": ei("ei_15100479_region_2025_cp949.csv")}
json.dump(out, open(os.path.join(H, "q38_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", os.path.getsize(os.path.join(H, "q38_data.json")))
for t in out:
    if t == "ei2025": continue
    ks = list(out[t]); print(t, len(ks), ks[:7], {y: v for y, v in list(out[t][ks[min(1, len(ks) - 1)]].items())[:3]})
