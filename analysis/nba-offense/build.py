"""NBA 공격 50년(1976-77~2025-26) 분석용 자료를 만든다.
입력: raw/ (fetch.py로 받은 Basketball-Reference 페이지)  출력: nba_data.json
모든 숫자는 Basketball-Reference 표에서 계산한다."""
import json, os, re, sys, math, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_util import tables, rows

H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(H, "raw")
Y0, Y1 = 1977, 2026                     # 시즌 끝 해 기준: 1976-77 ~ 2025-26
MULTI = re.compile(r"^(TOT|\dTM)$")      # 이적 선수의 합계 행
f = lambda x: float(x) if x not in ("", None) else None
lab = lambda y: f"{y - 1}-{str(y)[2:]}"

def read(name): return tables(open(os.path.join(RAW, name + ".html"), encoding="utf-8").read())

# ---------- 리그 평균 ----------
LG = {}
for r in rows(read("leagues_per_game")["stats-Regular-Season"]):
    if not r.get("season") or r.get("lg_id") != "NBA": continue
    y = int(r["season"][:4]) + 1
    if Y0 <= y <= Y1:
        LG[y] = {k: f(r.get(k)) for k in ["pts_per_g", "pace", "off_rtg", "ts_pct", "efg_pct", "fg_pct", "fg3_pct", "ft_pct", "fga_per_g", "fg3a_per_g", "fta_per_g",
                                         "ft_per_g", "fg3_per_g", "tov_per_g", "orb_per_g", "ast_per_g", "fg_per_g", "tov_pct", "orb_pct", "ft_rate", "mp_per_g", "g", "age"]}

seasons, players, teams_out = [], [], []
for y in range(Y0, Y1 + 1):
    T = read(f"{y}_teams")
    tot = {r["team_abbr"]: r for r in rows(T["totals-team"]) if r.get("team_abbr")}
    adv = {r["team_abbr"]: r for r in rows(T["advanced-team"]) if r.get("team_abbr")}
    G = max(int(r["g"]) for r in tot.values())          # 그 시즌 팀당 경기 수
    pg = rows(read(f"{y}_per_game")["per_game_stats"])
    pp = {}; [pp.setdefault((r.get("name_display_id"), r.get("team_name_abbr")), r) for r in rows(read(f"{y}_per_poss")["per_poss"])]
    ad = {}; [ad.setdefault((r.get("name_display_id"), r.get("team_name_abbr")), r) for r in rows(read(f"{y}_advanced")["advanced"])]
    pg = [r for r in pg if r.get("name_display_id") and r.get("games")]
    multi_ids = {r["name_display_id"] for r in pg if MULTI.match(r.get("team_name_abbr", ""))}

    # --- 팀별 득점 집중 ---
    by_team = {}
    for r in pg:
        tm = r["team_name_abbr"]
        if MULTI.match(tm) or tm not in tot: continue
        g = int(r["games"]); pts = f(r["pts_per_g"]) * g; fga = (f(r["fga_per_g"]) or 0) * g; fta = (f(r["fta_per_g"]) or 0) * g
        a = ad.get((r["name_display_id"], tm), {})
        by_team.setdefault(tm, []).append({"id": r["name_display_id"], "name": r["name_display"], "pts": pts, "fga": fga, "fta": fta,
                                           "mp": (f(r["mp_per_g"]) or 0) * g, "g": g, "usg": f(a.get("usg_pct"))})
    trows = []
    for tm, ps in by_team.items():
        tp = float(tot[tm]["pts"]); tfga = float(tot[tm]["fga"])
        sh = sorted((p["pts"] / tp for p in ps), reverse=True)
        top = max(ps, key=lambda p: p["pts"])
        hhi = sum(x * x for x in sh)
        usg = [p for p in ps if p["usg"] is not None and p["mp"] >= 500 * G / 82]
        tu = max(usg, key=lambda p: p["usg"]) if usg else None
        a = adv.get(tm, {})
        tppg = tp / int(tot[tm]["g"])
        reg = [p for p in ps if p["g"] >= 0.5 * G]                      # 팀 경기 절반 이상 뛴 선수
        pgTop = max(reg, key=lambda p: p["pts"] / p["g"]) if reg else top
        trows.append({"pgShare": round(pgTop["pts"] / pgTop["g"] / tppg, 4), "pgName": pgTop["name"], "pgMpg": round(pgTop["mp"] / pgTop["g"], 1), "pgP36": round(pgTop["pts"] / pgTop["mp"] * 36, 1) if pgTop["mp"] else None, "nUsed": len(ps),
                      "topGames": round(top["g"] / G, 3), "tm": tm, "top": round(sh[0], 4), "top2": round(sum(sh[:2]), 4), "top3": round(sum(sh[:3]), 4), "eff": round(1 / hhi, 2),
                      "topName": top["name"], "topId": top["id"], "topPpg": round(top["pts"] / top["g"], 1), "topFgaSh": round(top["fga"] / tfga, 4),
                      "topUsg": tu["usg"] if tu else None, "topUsgName": tu["name"] if tu else None,
                      "pace": f(a.get("pace")), "ortg": f(a.get("off_rtg")), "ppg": round(tp / int(tot[tm]["g"]), 1),
                      "w": int(a["wins"]) if a.get("wins") else None})
        teams_out.append(dict(trows[-1], y=y))

    # --- 선수-시즌 (이적 선수는 합계 행) ---
    pace_of = {tm: f(adv[tm]["pace"]) for tm in adv}
    for r in pg:
        pid, tm = r["name_display_id"], r["team_name_abbr"]
        if pid in multi_ids and not MULTI.match(tm): continue
        g = int(r["games"]); mpg = f(r["mp_per_g"]) or 0
        p = pp.get((pid, tm), {}); a = ad.get((pid, tm), {})
        # 이적 선수의 팀 페이스: 그 시즌 뛴 팀들의 출전 시간 가중 평균
        if MULTI.match(tm):
            parts = [x for x in pg if x["name_display_id"] == pid and not MULTI.match(x["team_name_abbr"]) and x["team_name_abbr"] in pace_of]
            w = sum((f(x["mp_per_g"]) or 0) * int(x["games"]) for x in parts) or 1
            tpace = sum(pace_of[x["team_name_abbr"]] * (f(x["mp_per_g"]) or 0) * int(x["games"]) for x in parts) / w
            tlast = parts[-1]["team_name_abbr"] if parts else tm
        else:
            tpace = pace_of.get(tm); tlast = tm
        players.append({"y": y, "id": pid, "n": r["name_display"], "tm": tlast, "multi": bool(MULTI.match(tm)), "age": f(r.get("age")),
                        "g": g, "gs": int(r["games_started"]) if r.get("games_started") else None, "mpg": mpg, "ppg": f(r["pts_per_g"]),
                        "fga": f(r.get("fga_per_g")), "fta": f(r.get("fta_per_g")), "fg3a": f(r.get("fg3a_per_g")),
                        "p100": f(p.get("pts_per_poss")), "usg": f(a.get("usg_pct")), "ts": f(a.get("ts_pct")), "tpace": round(tpace, 1) if tpace else None,
                        "G": G})

    # --- 시즌 요약 ---
    q = [p for p in players if p["y"] == y and p["mpg"] * p["g"] >= 1500 * G / 82]           # 주전급: 82경기 기준 1,500분 이상
    sc = [p for p in players if p["y"] == y and p["g"] >= math.ceil(0.7 * G)]                  # 득점왕 자격: 경기 수 70% 이상
    ppgs = sorted(p["ppg"] for p in q)
    pct = lambda a, x: a[min(len(a) - 1, int(round(x * (len(a) - 1))))]
    lead = max(sc, key=lambda p: p["ppg"])
    top10 = sorted((p["ppg"] for p in sc), reverse=True)[:10]
    usg_q = sorted(p["usg"] for p in q if p["usg"] is not None)
    tops = [t["top"] for t in trows]
    seasons.append({"y": y, "s": lab(y), "G": G, "nTeams": len(tot), "lg": LG[y],
                    "nQ": len(q), "p10": pct(ppgs, .1), "p50": pct(ppgs, .5), "p90": pct(ppgs, .9), "max": ppgs[-1],
                    "lead": {"n": lead["n"], "id": lead["id"], "ppg": lead["ppg"], "p100": lead["p100"]}, "top10": round(sum(top10) / len(top10), 2),
                    "n20": sum(p["ppg"] >= 20 for p in sc), "n25": sum(p["ppg"] >= 25 for p in sc), "n30": sum(p["ppg"] >= 30 for p in sc),
                    "usgP50": pct(usg_q, .5) if usg_q else None, "usgP90": pct(usg_q, .9) if usg_q else None,
                    "nUsg30": sum(u >= 30 for u in usg_q) if usg_q else None, "nUsg28": sum(u >= 28 for u in usg_q) if usg_q else None,
                    "topShare": round(st.mean(tops), 4), "topShareMed": round(st.median(tops), 4),
                    "top2": round(st.mean(t["top2"] for t in trows), 4), "eff": round(st.mean(t["eff"] for t in trows), 2),
                    "topFga": round(st.mean(t["topFgaSh"] for t in trows), 4),
                    "pgShare": round(st.mean(t["pgShare"] for t in trows), 4), "nUsed": round(st.mean(t["nUsed"] for t in trows), 2),
                    "topGames": round(st.mean(t["topGames"] for t in trows), 3),
                    "aceMpg": round(st.mean(t["pgMpg"] for t in trows), 1), "aceP36": round(st.mean(t["pgP36"] for t in trows if t["pgP36"]), 1),
                    "topUsg": round(st.mean(t["topUsg"] for t in trows if t["topUsg"]), 1) if any(t["topUsg"] for t in trows) else None})
    print(y, len(tot), G, len(q), lead["n"], lead["ppg"], round(st.mean(tops), 3), flush=True)

# 표시용으로 줄이기: 선수는 시즌당 출전 500분(82경기 기준) 이상만
keep = [p for p in players if p["mpg"] * p["g"] >= 500 * p["G"] / 82]
PC = ["y", "id", "n", "tm", "multi", "age", "g", "mpg", "ppg", "p100", "usg", "ts", "tpace", "fga", "fta", "fg3a"]
TC = ["y", "tm", "pgShare", "pgName", "nUsed", "topGames", "top", "top2", "top3", "eff", "topName", "topId", "topPpg", "topFgaSh", "topUsg", "topUsgName", "pace", "ortg", "ppg", "w"]
out = {"source": "Basketball-Reference.com", "seasons": seasons,
       "tcols": TC, "teams": [[t[k] for k in TC] for t in teams_out],
       "pcols": PC, "players": [[(int(p[k]) if k == "multi" else p[k]) for k in PC] for p in keep]}
json.dump(out, open(os.path.join(H, "nba_data.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("players", len(keep), "teams", len(teams_out), os.path.getsize(os.path.join(H, "nba_data.json")))
