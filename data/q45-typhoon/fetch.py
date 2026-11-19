"""#45 원자료 받기.
1) 기상청 기상자료개방포털 태풍목록(공공데이터포털 15043569가 가리키는 곳): typList.do 에 연도 범위를 POST하면 표가 온다(로그인 없이).
2) 일본기상청 RSMC Tokyo 태풍 최적경로(bst_all.zip): 6시간마다 위치·중심기압·최대풍속. 2차 자료가 아니라 WMO 지역특별기상센터의 공식 자료다."""
import os, re, html, json, subprocess
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, "raw")
def curl(args):
    for i in range(5):
        r = subprocess.run(["curl", "-sS", "--max-time", "180", "-A", "Mozilla/5.0"] + args, capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 1000: return r.stdout
    raise RuntimeError(r.stderr[-300:])
t = curl(["-X", "POST", "https://data.kma.go.kr/data/typhoonData/typList.do?pgmNo=688", "--data",
          "pgmNo=688&startDt=1951&endDt=2026&pageIndex=1&schListCnt=3000&lrgClssCd=WRN&mddlClssCd=WRN03&serviceSe=F00102&dataFormCd=F00503&menuNo=773&stnIds=_0&elementCds=TYP"]).decode("utf8", "replace")
rows = []
for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
    c = [html.unescape(re.sub(r"<[^>]+>|\s+", " ", x)).strip() for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
    if len(c) > 6 and c[0] != "태풍번호": rows.append(c[:7])
json.dump(rows, open(os.path.join(R, "kma_typhoon_list.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("기상청 태풍", len(rows))
open(os.path.join(R, "jma_bst_all.zip"), "wb").write(curl(["https://www.jma.go.jp/jma/jma-eng/jma-center/rsmc-hp-pub-eg/Besttracks/bst_all.zip"]))
print("JMA", os.path.getsize(os.path.join(R, "jma_bst_all.zip")))
