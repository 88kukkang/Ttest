"""Basketball-Reference에서 1976-77~2025-26 시즌 표를 받는다. 사이트 요청 한도(분당 20회)를 지키려고 4.2초 간격."""
import os, sys, time, subprocess
OUT = sys.argv[1]
pages = [("leagues_per_game", "https://www.basketball-reference.com/leagues/NBA_stats_per_game.html")]
for y in range(1977, 2027):
    for kind in ("per_game", "per_poss", "advanced"):
        pages.append((f"{y}_{kind}", f"https://www.basketball-reference.com/leagues/NBA_{y}_{kind}.html"))
    pages.append((f"{y}_teams", f"https://www.basketball-reference.com/leagues/NBA_{y}.html"))
for name, url in pages:
    path = os.path.join(OUT, name + ".html")
    if os.path.exists(path) and os.path.getsize(path) > 20000: continue
    for attempt in range(3):
        r = subprocess.run(["curl", "-s", "-A", "Mozilla/5.0 (research script)", "--max-time", "60", "-o", path, "-w", "%{http_code}", url], capture_output=True, text=True)
        code = r.stdout.strip(); print(name, code, flush=True)
        time.sleep(4.2)
        if code == "200": break
        if code == "429": time.sleep(70)
