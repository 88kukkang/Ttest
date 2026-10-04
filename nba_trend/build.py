"""경기 데이터를 모아 인터랙티브 HTML 그래프를 만든다.

    python -m nba_trend.build                       # 2025-26 시즌, 2024-25와 비교
    python -m nba_trend.build --season 2027         # 2026-27 시즌 (진행 중이어도 됨)
    python -m nba_trend.build --source sportsdataverse --refresh
"""

import argparse
import json
from datetime import date
from pathlib import Path

from .sources import load_games
from .standings import build_logs
from .teams import TEAMS

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).with_name("template.html")
BODY_MARK = "<!--BODY-->"
DATA_MARK = "/*__NBA_DATA__*/null"


def season_label(season):
    return f"{season - 1}-{str(season)[-2:]}"


def season_payload(season, games):
    logs = build_logs(games)
    return {
        "label": season_label(season),
        "games": len(games),
        "first": games["date"].min(),
        "last": games["date"].max(),
        "teams": {
            t: [[g["date"], g["opp"], int(g["home"]), g["pts"], g["opp_pts"],
                 g["conf_rank"], g["league_rank"]] for g in log]
            for t, log in logs.items() if log
        },
    }


def render(payload):
    template = TEMPLATE.read_text(encoding="utf-8")
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fragment = template.replace(DATA_MARK, data)
    head, body = fragment.split(BODY_MARK)
    page = ("<!doctype html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            f"{head.strip()}\n</head>\n<body>\n{body.strip()}\n</body>\n</html>\n")
    return page, fragment.replace(BODY_MARK, "")


def main(argv=None):
    p = argparse.ArgumentParser(description="NBA 시즌 레이스 그래프 생성")
    p.add_argument("--season", type=int, default=2026, help="시즌 끝 연도 (2026 = 2025-26)")
    p.add_argument("--compare", default="auto",
                   help="비교할 시즌 끝 연도. auto = 직전 시즌, none = 비교 안 함")
    p.add_argument("--source", choices=["auto", "bbref", "sportsdataverse"], default="auto",
                   help="auto 는 basketball-reference 를 먼저 시도하고 실패하면 sportsdataverse 사용")
    p.add_argument("--refresh", action="store_true", help="캐시를 무시하고 다시 수집")
    p.add_argument("--data-dir", type=Path, default=ROOT / "data")
    p.add_argument("--out", type=Path, default=ROOT / "docs" / "index.html")
    p.add_argument("--fragment-out", type=Path, help="<html>/<body> 없이 본문만 담은 HTML도 저장")
    args = p.parse_args(argv)

    seasons = [args.season]
    compare = None
    if args.compare != "none":
        compare = args.season - 1 if args.compare == "auto" else int(args.compare)
        seasons.append(compare)

    payload = {
        "generated": date.today().isoformat(),
        "current": str(args.season),
        "previous": str(compare) if compare else None,
        "teams": TEAMS,
        "seasons": {},
    }
    sources = set()
    for season in seasons:
        games = load_games(season, args.source, args.data_dir, refresh=args.refresh)
        sources.update(games["source"].unique())
        payload["seasons"][str(season)] = season_payload(season, games)
    payload["source"] = "bbref" if sources == {"bbref"} else "sportsdataverse"

    page, fragment = render(payload)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print(f"저장: {args.out} ({len(page) / 1024:.0f} KB)")
    if args.fragment_out:
        args.fragment_out.parent.mkdir(parents=True, exist_ok=True)
        args.fragment_out.write_text(fragment, encoding="utf-8")
        print(f"저장: {args.fragment_out}")


if __name__ == "__main__":
    main()
