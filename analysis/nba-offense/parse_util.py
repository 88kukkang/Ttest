"""Basketball-Reference 표를 data-stat 속성으로 읽는다(주석 안에 숨은 표도 꺼낸다)."""
import re
from bs4 import BeautifulSoup, Comment
def tables(html):
    soup = BeautifulSoup(html, "lxml")
    out = {t.get("id"): t for t in soup.find_all("table") if t.get("id")}
    for c in soup.find_all(string=lambda s: isinstance(s, Comment) and "<table" in s):
        for t in BeautifulSoup(c, "lxml").find_all("table"):
            if t.get("id"): out.setdefault(t.get("id"), t)
    return out
def rows(table):
    res = []
    body = table.find("tbody") or table
    for tr in body.find_all("tr"):
        if "thead" in (tr.get("class") or []) or "over_header" in (tr.get("class") or []): continue
        cells = tr.find_all(["th", "td"])
        if not cells: continue
        d = {}
        for c in cells:
            k = c.get("data-stat")
            if k: d[k] = c.get_text(strip=True); 
            if k and c.get("data-append-csv"): d[k + "_id"] = c.get("data-append-csv")
            a = c.find("a")
            if k and a and a.get("href", "").startswith("/teams/"): d[k + "_abbr"] = a["href"].split("/")[2]
        if d: res.append(d)
    return res
