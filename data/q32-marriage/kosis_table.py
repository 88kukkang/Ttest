"""Parse a KOSIS html.do JSON response into header rows and body rows (colspans expanded)."""
import json, re, html
def rows(fn):
    j = json.loads(open(fn, encoding="utf-8").read()); h = j["result"][0]
    out = []
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S):
        cells = []
        for m in re.finditer(r"<t([hd])([^>]*)>(.*?)</t[hd]>", r, re.S):
            cs = re.search(r"colspan=[\"']?(\d+)", m.group(2)); rs = re.search(r"rowspan=[\"']?(\d+)", m.group(2))
            txt = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
            cells += [txt] * (int(cs.group(1)) if cs else 1)
        out.append(cells)
    return out
def num(s):
    s = s.replace(",", "").strip()
    try: return float(s)
    except ValueError: return None
