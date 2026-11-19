"""65+ one-person households (Census, via SGIS thematic map) by sido and sigungu, 2015-2024."""
import json, subprocess, time
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
TID = "stat_house_age_65_mt1_psn_1_family_cnt_irds"
SIDO = ["11", "21", "22", "23", "24", "25", "26", "29", "31", "32", "33", "34", "35", "36", "37", "38", "39"]


def get(adm, year):
    url = f"https://sgis.mods.go.kr/ServiceAPI/thematicMap/getThemaMapDataForChart.json?thema_map_data_id={TID}&adm_cd={adm}&data_year={year}&area_type=auto"
    for i in range(8):
        r = subprocess.run(["curl", "-sS", "--max-time", "40", "-A", UA, "-e", "https://sgis.mods.go.kr/view/thematicMap/thematicMapMain", url], capture_output=True, text=True)
        try:
            return adm, year, json.loads(r.stdout)["result"]["detailInfo"]
        except Exception:
            time.sleep(1 + i)
    raise SystemExit(f"fail {adm} {year} {r.stdout[:200]}")


jobs = [(a, y) for y in range(2015, 2025) for a in ["00"] + SIDO]
out = {}
with ThreadPoolExecutor(6) as ex:
    for adm, year, rows in ex.map(lambda j: get(*j), jobs):
        for r in rows:
            out.setdefault(r["adm_cd"], {})[year] = int(float(r["right_data_val"]))
json.dump(out, open("sgis_65_1p.json", "w"), ensure_ascii=False)
print(len(out), sum(len(v) for v in out.values()))
