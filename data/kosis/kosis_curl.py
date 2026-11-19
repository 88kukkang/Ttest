"""KOSIS statHtml tables without a browser or API key.

  meta = kosis_curl.meta("101", "DT_1DA7147S")               # table metadata: items, classes, periods
  kosis_curl.fetch("101", "DT_1DA7147S", "M,202610,202609,@", out="x.json",
                   items=None,                                # None = all items
                   classes={"G": None, "M": ["905"]})         # class id -> item ids (None = all)
  rows = kosis_curl.table("x.json")                            # list of rows, colspans expanded
  tr = kosis_curl.tree("354", "DT_HIRA4T")                     # all levels of nested classes (sido -> sigungu)

How it works: statHtmlContent.do returns the page script, which holds the table's metadata as JSON (g_jsonStatInfo).
html.do returns the table as HTML inside JSON. Both accept a plain POST as long as every form field is present, blank ones
included (template_body.txt is one captured request; parse it with keep_blank_values=True). The period string is
"<M|Q|H|Y>,<period>,<period>,...,@". Requests go through curl so the proxy settings of the machine apply.
"""
import html as _html, json, os, re, subprocess, time
from urllib.parse import parse_qsl, urlencode
H = os.path.dirname(os.path.abspath(__file__))
TPL = parse_qsl(open(os.path.join(H, "template_body.txt"), encoding="utf-8").read(), keep_blank_values=True)
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"

def _post(ep, org, tbl, body, tries=6):
    ref = f"https://kosis.kr/statHtml/statHtml.do?orgId={org}&tblId={tbl}&conn_path=I2"
    for i in range(tries):
        r = subprocess.run(["curl", "-sS", "--max-time", "120", "-A", UA, "-H", "X-Requested-With: XMLHttpRequest", "-H", "Referer: " + ref,
                            "-H", "Content-Type: application/x-www-form-urlencoded; charset=UTF-8", "--data-binary", "@-", f"https://kosis.kr/statHtml/{ep}"],
                           input=body.encode(), capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 500: return r.stdout.decode("utf-8", "replace")
        time.sleep(2 + 2 * i)
    raise RuntimeError(f"{ep} {tbl} failed: {r.stderr[-200:]}")

def _body(org, tbl, over):
    blank = {"fieldList", "colAxis", "rowAxis", "statId", "tblNm", "tblEngNm", "classAllArr", "classSet"}
    return urlencode([(k, over.get(k, tbl if k == "tblId" else org if k == "orgId" else "" if k in blank else v)) for k, v in TPL])

def meta(org, tbl, cache=None):
    cache = cache or os.path.join(H, "meta", f"{org}_{tbl}.json")
    if os.path.exists(cache): return json.load(open(cache, encoding="utf-8"))
    t = _post("statHtmlContent.do", org, tbl, _body(org, tbl, {}))
    m = re.search(r"var g_jsonStatInfo\s*=\s*'(.*?)';\s*\n", t, re.S)
    if not m: raise RuntimeError("no g_jsonStatInfo for " + tbl)
    s = m.group(1)
    try: d = json.loads(s)
    except ValueError: d = json.loads(s.replace("\\'", "'"))
    os.makedirs(os.path.dirname(cache), exist_ok=True); json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
    return d

def describe(org, tbl):
    d = meta(org, tbl); pi = d["periodInfo"]
    print(tbl, d["tblNm"], "|", d.get("containPeriod"), "| unit", d.get("unitNm"))
    print("  items:", [(i["itmId"], i["scrKor"]) for i in d["itemInfo"]["itmList"]][:30])
    for c in d["classInfoList"]:
        print(f"  class {c['classId']} (sn {c['sn']}) {c['classNm']} n={c['itmCnt']}:", [(i["itmId"], i["scrKor"]) for i in c["itmList"]][:40])

def _over(d, fl, its, cl, prd):
    return {"fieldList": json.dumps(fl, ensure_ascii=False), "rowAxis": ",".join(c["classId"] for c in cl), "colAxis": "TIME,ITEM" if len(its) > 1 else "TIME",
            "statId": str(d.get("statId") or ""), "tblNm": d["tblNm"], "tblEngNm": d.get("tblEngNm") or "", "periodStr": prd.split(",")[0],
            "classAllArr": json.dumps([{"objVarId": c["classId"], "ovlSn": str(c["sn"])} for c in cl]),
            "classSet": json.dumps([{"objVarId": c["classId"], "ovlSn": str(c["sn"]), "visible": "true"} for c in cl]), "endNum": "100000"}

def tree(org, tbl, cache=None):
    """Every item of every class, all levels: {classId: [{itmId, upItmId, lvl, scrKor}, ...]}.
    meta() lists only the first level of a nested class (sido but not sigungu); this asks treeInfo.do for the rest."""
    cache = cache or os.path.join(H, "meta", f"{org}_{tbl}_tree.json")
    if os.path.exists(cache): return json.load(open(cache, encoding="utf-8"))
    d = meta(org, tbl); cl = sorted(d["classInfoList"], key=lambda c: int(c["sn"]))
    its = [i["itmId"] for i in d["itemInfo"]["itmList"]]; pi = d["periodInfo"]
    ps = next(p for p in d["periodStr"].split("#") if pi.get("defaultEnd" + p)); prd = f"{ps},{pi['defaultEnd' + ps]},@"
    fl = [{"targetId": "PRD", "targetValue": "", "prdValue": prd}] + [{"targetId": "ITM_ID", "targetValue": v, "prdValue": ""} for v in its]
    for c in cl: fl += [{"targetId": f"OV_L{c['sn']}_ID", "targetValue": i["itmId"], "prdValue": ""} for i in c["itmList"]]
    over = _over(d, fl, its, cl, prd)
    over.update({"periodStr": d["periodStr"], "defaulPeriodArr": json.dumps({ps: [int(pi["defaultEnd" + ps])]}), "defaultItmArr": json.dumps([{"data": its}]),
                 "defaultClassArr": json.dumps([{"objVarId": c["classId"], "data": [i["itmId"] for i in c["itmList"]]} for c in cl], ensure_ascii=False)})
    t = _post("treeInfo.do", org, tbl, _body(org, tbl, over))
    out = {}
    for m in re.finditer(r'"lvl":(\d+),"orgId":"[^"]*","tblId":"[^"]*","scrEng":(?:"[^"]*"|null),"itmId":"([^"]+)","upItmId":(?:"([^"]*)"|null),"rownum":\d+,"objVarId":"([^"]+)","charItmSn":\d+,"leaf":\d+,"scrKor":"([^"]*)"', t):
        out.setdefault(m.group(4), []).append({"itmId": m.group(2), "upItmId": m.group(3), "lvl": int(m.group(1)), "scrKor": m.group(5)})
    if not out: raise RuntimeError("no tree for " + tbl)
    json.dump(out, open(cache, "w", encoding="utf-8"), ensure_ascii=False); return out

def fetch(org, tbl, prd, out, items=None, classes=None):
    if os.path.exists(out) and os.path.getsize(out) > 2000 and '"result"' in open(out, encoding="utf-8").read(200000): return out
    d = meta(org, tbl); classes = classes or {}
    fl = [{"targetId": "PRD", "targetValue": "", "prdValue": prd}]
    its = items or [i["itmId"] for i in d["itemInfo"]["itmList"]]
    fl += [{"targetId": "ITM_ID", "targetValue": v, "prdValue": ""} for v in its]
    cl = sorted(d["classInfoList"], key=lambda c: int(c["sn"]))
    for c in cl:
        vals = classes.get(c["classId"]) or [i["itmId"] for i in c["itmList"]]
        fl += [{"targetId": f"OV_L{c['sn']}_ID", "targetValue": v, "prdValue": ""} for v in vals]
    over = _over(d, fl, its, cl, prd)
    t = _post("html.do", org, tbl, _body(org, tbl, over))
    if '"result"' not in t: raise RuntimeError(f"{tbl} {prd[:30]}: {t[:200]}")
    open(out, "w", encoding="utf-8").write(t); return out

def table(fn):
    h = json.loads(open(fn, encoding="utf-8").read())["result"][0]; out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = []
        for m in re.finditer(r"<t([hd])([^>]*)>(.*?)</t[hd]>", r, re.S):
            cs = re.search(r"colspan=[\"']?(\d+)", m.group(2))
            cells += [_html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()] * (int(cs.group(1)) if cs else 1)
        out.append(cells)
    return out

def num(s):
    try: return float(s.replace(",", "").strip())
    except ValueError: return None

if __name__ == "__main__":
    import sys
    describe(sys.argv[1], sys.argv[2])
