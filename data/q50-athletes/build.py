"""#50 계산: 병무청 체육요원 연도별 편입 인원(공공데이터포털 15086043, 1996–2024년)과 대회 연도.
종목별 인원은 공개 파일에 없어, 국회 국방위원회 김병주 의원실이 병무청에서 받은 자료를 보도한 기사(raw/news_fnnews_20261014.txt)의 숫자를 2차 자료로 쓴다.
편입 기준은 병역법 시행령 제68조의11(raw/decree_68-11.json). 출력: q50_data.json"""
import os, csv, io, json
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
r = list(csv.reader(io.StringIO(open(os.path.join(R, "sports_service_by_year.csv"), "rb").read().decode("cp949"))))
Y = [[int(x[0]), int(x[1])] for x in r[1:] if x and x[0].strip()]
AG = {1998: "방콕(12월)", 2002: "부산(9–10월)", 2006: "도하(12월)", 2010: "광저우(11월)", 2014: "인천(9–10월)", 2018: "자카르타·팔렘방(8–9월)", 2023: "항저우(9–10월)", 2026: "아이치·나고야(9–10월)"}
OG = {1996: "애틀랜타", 1998: "나가노(겨울)", 2000: "시드니", 2002: "솔트레이크(겨울)", 2004: "아테네", 2006: "토리노(겨울)", 2008: "베이징", 2010: "밴쿠버(겨울)", 2012: "런던", 2014: "소치(겨울)", 2016: "리우", 2018: "평창(겨울)", 2021: "도쿄", 2022: "베이징(겨울)", 2024: "파리", 2026: "밀라노·코르티나(겨울)"}
tot = sum(v for _, v in Y); print("1996–2024 합", tot, len(Y), "해")
after = {1999, 2003, 2007, 2011, 2014, 2015, 2018, 2019, 2023, 2024}   # 아시안게임이 열린 해(가을)와 그다음 해(겨울 대회는 다음 해)
s = sum(v for y, v in Y if y in after); print("아시안게임 뒤 해들", s, round(s / tot * 100, 1))
print("많은 해", sorted(Y, key=lambda z: -z[1])[:8])
NEWS = {"2018": {"tot": 41, "축구": 20, "야구": 9}, "2023": {"tot": 57, "축구": 20, "야구": 19}, "2026": {"tot": 56, "축구": 20, "야구": 16, "농구": 8, "3대3 농구": 4},
        "team": {"2018": 80.5, "2023": 89.5}}
for k in ("2018", "2023", "2026"):
    n = NEWS[k]; print(k, "축구+야구", n["축구"] + n["야구"], round((n["축구"] + n["야구"]) / n["tot"] * 100, 1))
law = json.load(open(os.path.join(R, "decree_68-11.json"), encoding="utf-8"))
json.dump({"Y": Y, "AG": AG, "OG": OG, "news": NEWS, "law": law["text"]}, open(os.path.join(H, "q50_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
