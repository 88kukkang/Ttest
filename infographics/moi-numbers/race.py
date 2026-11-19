"""소비쿠폰·고유가 피해지원금 신청 현황 보도(참고)자료에서 날마다의 신청률과 시도별 지급 방식을 읽는다."""
import json, re, os, datetime as dt
H = os.path.dirname(os.path.abspath(__file__))
docs = json.load(open(f"{H}/../web/docs.bin", encoding="utf-8"))["docs"]
SIDO = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주", "전남광주"]
num = lambda s: int(s.replace(",", ""))
out = []
for ntt, date, dept, title, text in docs:
    if not re.search(r"(소비쿠폰|고유가 피해지원금).*(현황|마감|결과|꼭 신청|일간)|신청률 90%|10명 중 9명|첫 주", title): continue
    m = re.search(r"[’']?(\d{2})\.(\d{1,2})\.(\d{1,2})\.?\s*(?:\([월화수목금토일]\))?\s*(\d{1,2})시\s*(?:신청·지급\s*마감\s*)?기준", text)
    if m: y, mo, d, h = 2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    else:
        m = re.search(r"\(?(\d{1,2})\.(\d{1,2})\.\s*(\d{1,2})시\s*기준\)|(\d{1,2})월\s*(\d{1,2})일?\s*\(.\)\s*(\d{1,2})(?:시|:00)\s*기준", text)
        if not m: continue
        g = [x for x in m.groups() if x is not None]; y = int(date[:4]); mo, d, h = map(int, g)
    prog = "coupon" if "소비쿠폰" in title else "oil"
    rec = {"ntt": ntt, "pub": date, "title": title, "prog": prog, "at": f"{y:04d}-{mo:02d}-{d:02d}", "hour": h}
    t = re.search(r"총\s*([\d,]+(?:만)?\s*[\d,]*\s*명?)\s*\(([\d.]+)%\)\s*신청,\s*([\d조,\s]+억)\s*원", text)
    if t: rec["pct"] = float(t.group(2))
    s2 = re.search(r"\(2차 대상자\)\s*총\s*([\d,.]+)만\s*명\s*신청\(대상자 대비\s*([\d.]+)%\)", text)
    if s2: rec["pct2"] = float(s2.group(2))
    s1 = re.search(r"\(1차 대상자\)\s*총\s*([\d,.]+)만\s*명\s*신청\(대상자 대비\s*([\d.]+)%\)", text)
    if s1: rec["pct1"] = float(s1.group(2))
    # 시도 표: 이름 다음 숫자 7개 (신청자, 카드, 상품권 모바일·카드, 상품권 지류, 선불, 지급액, 대상자) + 신청률
    rows = {}
    for sd in ["계"] + SIDO:
        name = (r"\s*".join(sd) if sd != "계" else "계")
        if sd in ("광주", "전남"): name = "(?:구)?" + name   # 2026. 7. 전남광주 통합 뒤 표에는 '구광주'·'구전남'
        pat = (r"\n" + name + r"\s*\n" + r"([\d,]+)\s*\n" * 7 + r"([\d.]+)%")
        mm = re.search(pat, text)
        if mm: rows[sd] = [num(mm.group(i)) for i in range(1, 8)] + [float(mm.group(8))]
    if rows: rec["rows"] = rows
    if "pct" not in rec and "계" in rows: rec["pct"] = rows["계"][7]
    if "pct" not in rec:
        p = re.search(r"(?:대상자의|인원의|전체 신청 대상자의)\s*([\d.]+)%", text)
        if p: rec["pct"] = float(p.group(1))
    out.append(rec)
out.sort(key=lambda r: (r["at"], r["hour"]))
json.dump(out, open(f"{H}/race_raw.json", "w", encoding="utf-8"), ensure_ascii=False)
for r in out: print(r["prog"], r["at"], r["hour"], r.get("pct"), r.get("pct1"), r.get("pct2"), len(r.get("rows", {})), r["title"][:40])
