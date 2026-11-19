"""#49 계산: 세종학당재단 국가별 세종학당 수강생 수(2021–2025년, 공공데이터포털 15127358)를 지역별로 묶고 세계지도에 놓는다.
지역 묶음은 이 장이 정했다. 함께: 한국국제교류재단 해외대학 한국학 현황(15041591), 세종학당 학습 앱 다운로드·가입(15159571·15159589).
지도 점은 world.mjs(d3-geo, world-atlas 110m, Equal Earth)로 만든 geo.json. 출력: q49_data.json"""
import os, csv, io, json, collections
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
def rd(f):
    b = open(os.path.join(R, f), "rb").read()
    for enc in ("utf-8-sig", "cp949"):
        try: return [r for r in csv.reader(io.StringIO(b.decode(enc))) if r]
        except UnicodeDecodeError: pass
REG = {"동북아시아": "중국 일본 몽골 대한민국", "동남아시아": "베트남 인도네시아 필리핀 태국 말레이시아 캄보디아 라오스 미얀마 동티모르", "남아시아": "인도 네팔 방글라데시 스리랑카 파키스탄",
       "러시아·중앙아시아": "러시아 우즈베키스탄 카자흐스탄 키르기스스탄 타지키스탄 투르크메니스탄 아제르바이잔",
       "유럽": "독일 덴마크 라트비아 루마니아 룩셈부르크 리투아니아 벨기에 벨라루스 불가리아 세르비아 스웨덴 스페인 슬로바키아 슬로베니아 아이슬란드 에스토니아 영국 오스트리아 우크라이나 이탈리아 체코 크로아티아 튀르키예 포르투갈 폴란드 프랑스 핀란드 헝가리",
       "북미": "미국 캐나다", "중남미": "과테말라 멕시코 볼리비아 브라질 아르헨티나 아이티 에콰도르 엘살바도르 우루과이 칠레 콜롬비아 쿠바 페루",
       "중동·아프리카": "나이지리아 남아프리카공화국 마다가스카르 말라위 모로코 바레인 보츠와나 사우디아라비아 아랍에미리트 알제리 에스와티니 요르단 우간다 이란 이집트 케냐 코트디부아르 쿠웨이트 탄자니아 튀니지 팔레스타인",
       "오세아니아": "호주"}
R2 = {c: g for g, cs in REG.items() for c in cs.split()}
r = rd("students_2021_2025.csv"); YS = [int(h[:4]) for h in r[0][1:]]
C = [{"n": x[0], "v": [int(v or 0) for v in x[1:]], "g": R2[x[0]]} for x in r[1:] if x[0]]
geo = json.load(open(os.path.join(H, "geo.json"), encoding="utf-8"))
for c in C: c["xy"] = geo["pts"][c["n"]]
T = [sum(c["v"][j] for c in C) for j in range(len(YS))]; print("합계", dict(zip(YS, T)), len(C), "나라")
G = {g: [sum(c["v"][j] for c in C if c["g"] == g) for j in range(len(YS))] for g in REG}
for g, v in G.items(): print(f"  {g:10s}", v, f"{v[-1] / T[-1] * 100:.1f}%", f"2021→2025 {(v[-1] / v[0] - 1) * 100:+.0f}%" if v[0] else "")
ASIA = ("동북아시아", "동남아시아", "남아시아", "러시아·중앙아시아")
out_ = [sum(G[g][j] for g in G if g not in ASIA) for j in range(len(YS))]; print("아시아 밖", out_, [round(o / t * 100, 1) for o, t in zip(out_, T)])
outR = [sum(G[g][j] for g in G if g not in ASIA) for j in range(len(YS))]
print("러시아 제외 아시아", [sum(G[g][j] for g in ASIA) - next(c for c in C if c["n"] == "러시아")["v"][j] for j in range(len(YS))])
srt = sorted(C, key=lambda c: -c["v"][-1]); print("2025 상위", [(c["n"], c["v"][-1], round(c["v"][-1] / T[-1] * 100, 1)) for c in srt[:12]])
grow = sorted([c for c in C if c["v"][0] >= 300], key=lambda c: -(c["v"][-1] / c["v"][0])); print("많이 는 곳(2021≥300)", [(c["n"], c["v"][0], c["v"][-1], round(c["v"][-1] / c["v"][0], 1)) for c in grow[:12]])
print("줄어든 곳", [(c["n"], c["v"][0], c["v"][-1]) for c in grow[-8:]])
print("2025 0명", [c["n"] for c in C if c["v"][-1] == 0], "2021 0명", [c["n"] for c in C if c["v"][0] == 0])
print("한 해라도 1천 명 이상", sum(1 for c in C if max(c["v"]) >= 1000))
# 한국학 대학
u = rd("korean_studies_universities.csv"); UN = collections.Counter(x[1] for x in u[1:]); US = collections.Counter(x[1] for x in u[1:] if x[8] == "Y")
APP = [[x[0].replace(" ", ""), int(x[1] or 0), int(x[2] or 0), int(x[3] or 0)] for x in rd("app_downloads_2025.csv")[1:] if x[0]]
SIGN = [[x[0], int(x[1])] for x in rd("app_signups_2025.csv")[1:] if x[0] and x[1]]
print("앱 다운로드 2025 합", [sum(a[k] for a in APP) for k in (1, 2, 3)], "가입", sum(s[1] for s in SIGN))
json.dump({"YS": YS, "C": C, "T": T, "G": G, "regs": list(REG), "asia": ASIA, "univ": dict(UN), "univSejong": dict(US), "app": APP, "sign": SIGN, "geo": {k: geo[k] for k in ("world", "kor", "W", "H")}},
          open(os.path.join(H, "q49_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(os.path.getsize(os.path.join(H, "q49_data.json")))
