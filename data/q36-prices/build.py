"""Build q36_data.json: item-level CPI (KOSIS 101 DT_1J22112, 2020=100, national), monthly 2014.01-2026.10.
usage: python3 build.py <rawdir with cpi_YYYY.json>
The table rows come back in tree order with the level in the label's indent (0 = total and the six groups,
10 = sub-group, 20 = item); items that did not exist yet are missing from early years."""
import json, os, sys, glob, re, html
H = os.path.dirname(os.path.abspath(__file__))
raw = sys.argv[1]
num = lambda s: float(s.replace(",", "")) if re.match(r"^-?[\d,.]+$", s.strip()) else None
series = {}; meta = {}; months = []; order = []
for f in sorted(glob.glob(f"{raw}/cpi_*.json")):
    h = json.loads(open(f, encoding="utf-8").read())["result"][0]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S)
    hdr = [re.sub(r"[^0-9.]", "", html.unescape(re.sub(r"<[^>]+>", "", c))) for c in re.findall(r"<th[^>]*>(.*?)</th>", rows[0], re.S)][2:]
    g1 = g2 = None
    for r in rows[1:]:
        m = re.search(r"<td class='first trHeader' title='([^']*)' sortSn='\d+'><span>&nbsp;</span><span class='last' style='[^']*margin-left:(\d+)px'", r)
        if not m or m.group(1) == "전국": 
            cells = re.findall(r"<td class='first trHeader' title='([^']*)'[^>]*><span>&nbsp;</span><span class='last' style='[^']*margin-left:(\d+)px'", r)
            if len(cells) < 2: continue
            name, lvl = html.unescape(cells[1][0]), int(cells[1][1])
        else: name, lvl = html.unescape(m.group(1)), int(m.group(2))
        vals = [num(v) for v in re.findall(r"<td class='value[^']*' title='([^']*)'", r)]
        if lvl == 0: g1, g2 = name, None; key = ("G", name)
        elif lvl == 10: g2 = name; key = ("S", g1, name)
        else: key = ("I", g1, g2, name)
        if key not in meta: meta[key] = True; order.append(key)
        for mth, v in zip(hdr, vals): series.setdefault(key, {})[mth] = v
    months += hdr
months = sorted(set(months))
items = [{"n": k[3], "g1": k[1], "g2": re.sub(r"^\([^)]*\)", "", k[2] or ""), "v": [series[k].get(m) for m in months]} for k in order if k[0] == "I"]
out = {"m": months, "total": [series[("G", "총지수")].get(m) for m in months],
       "groups": {k[1]: [series[k].get(m) for m in months] for k in order if k[0] == "G" and k[1] != "총지수"}, "items": items}
json.dump(out, open(os.path.join(H, "q36_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("months", months[0], months[-1], len(months), "items", len(items), "groups", list(out["groups"]), os.path.getsize(os.path.join(H, "q36_data.json")))
