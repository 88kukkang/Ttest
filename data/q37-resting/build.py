"""Build q37_data.json ('쉬었음' = not working, not looking, just resting) from KOSIS 101 files fetched by fetch.py.
usage: python3 build.py <rawdir>"""
import json, os, sys, glob, re
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, "..", "kosis"))
import kosis_curl as K
raw = sys.argv[1]
def load(prefix, ncls):
    """-> {month: {tuple(class labels + item?): value}} ; carries row labels forward over merged cells"""
    out = {}
    for f in sorted(glob.glob(f"{raw}/{prefix}_*.json")):
        R = K.table(f); hdr = R[0][ncls:]; sub = R[1] if len(R[1]) == len(hdr) and any(x for x in R[1]) else None   # item names when several items
        prev = [None] * ncls
        for r in R[1:]:
            if len(r) <= ncls or all(K.num(x) is None for x in r[ncls:]): continue
            lab = [r[i].strip() or prev[i] for i in range(ncls)]; prev = lab
            for j, v in enumerate(r[ncls:]):
                m = re.sub(r"[^0-9.]", "", hdr[j]); key = tuple(lab) + ((sub[j].strip(),) if sub else ())
                out.setdefault(m, {})[key] = K.num(v)
    return out
rest = load("rest", 2); pop = load("pop", 1); act = load("act", 2)
M = sorted(rest)
AG = ["15 - 19세", "20 - 29세", "30 - 39세", "40 - 49세", "50 - 59세", "60세이상"]
g = lambda d, m, k: d.get(m, {}).get(k)
out = {"m": M, "ages": AG}
out["rest"] = {a: [g(rest, m, (a, "쉬었음")) for m in M] for a in AG + ["계", "15 - 29세"]}
items = sorted({k[1] for k in pop[M[-1]]}); print("pop items", items)
P = lambda a, it: [g(pop, m, (a, it)) for m in M]
out["pop"] = {a: P(a, "인구 (천명)") for a in AG + ["15세 이상 전체", "15 - 29세"]}
out["emp"] = {a: P(a, "취업자 (천명)") for a in AG + ["15 - 29세"]}
out["unemp"] = {a: P(a, "실업자 (천명)") for a in AG + ["15 - 29세"]}
out["nea"] = {a: P(a, "비경제활동인구 (천명)") for a in AG + ["15 - 29세"]}
states = sorted({k[1] for k in act[M[-1]]}); print("act states", states)
out["act"] = {s: {sx: [g(act, m, (sx, s)) for m in M] for sx in ("계", "남자", "여자")} for s in states}
def why(fn, ncls):
    R = K.table(os.path.join(raw, fn)); hdr = [re.sub(r"[^0-9.]", "", x) for x in R[0][ncls:]]; prev = [None] * ncls; d = {}
    for r in R[1:]:
        if len(r) <= ncls or all(K.num(x) is None for x in r[ncls:]): continue
        lab = [r[i].strip() or prev[i] for i in range(ncls)]; prev = lab
        d["|".join(lab)] = dict(zip(hdr, [K.num(x) for x in r[ncls:]]))
    return d
out["whyAge"] = why("why_age.json", 3); out["whySex"] = why("why_sex.json", 2)
# annual averages (2026 = January-October) so that one frame is one year
YRS = sorted({m[:4] for m in M})
def ann(series):
    res = []
    for y in YRS:
        v = [x for m, x in zip(M, series) if m.startswith(y) and x is not None]; res.append(round(sum(v) / len(v), 1) if v else None)
    return res
out["yrs"] = [int(y) for y in YRS]
out["ann"] = {k: {a: ann(out[k][a]) for a in out[k]} for k in ("rest", "pop", "emp", "unemp", "nea")}
json.dump(out, open(os.path.join(H, "q37_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", M[0], M[-1], len(M), os.path.getsize(os.path.join(H, "q37_data.json")))
