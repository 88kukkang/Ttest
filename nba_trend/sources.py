"""경기 결과 수집.

두 가지 소스를 지원하며 둘 다 같은 형태의 표(date, away, home, away_pts, home_pts)를 돌려준다.

- bbref: basketball-reference.com 시즌 일정 페이지 (기본값)
- sportsdataverse: GitHub에 공개된 ESPN 팀 박스스코어 (bbref에 접속할 수 없을 때의 대안)

season 은 basketball-reference 관례를 따른다. 2026 = 2025-26 시즌.
"""

import io
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser

import pandas as pd

from .teams import normalize

USER_AGENT = "Mozilla/5.0 (nba-trend; personal stats project)"
BBREF_URL = "https://www.basketball-reference.com/leagues/NBA_{season}_games-{month}.html"
BBREF_MONTHS = ["october", "november", "december", "january", "february", "march", "april"]
# basketball-reference는 분당 20회 이상 요청하면 일시 차단한다.
BBREF_DELAY_SEC = 3.5
SDV_URL = ("https://github.com/sportsdataverse/sportsdataverse-data/releases/download/"
           "espn_nba_team_boxscores/team_box_{season}.csv")

COLUMNS = ["date", "away", "home", "away_pts", "home_pts"]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


class _ScheduleParser(HTMLParser):
    """bbref 일정 표(table#schedule)를 data-stat 속성 기준으로 읽는다."""

    def __init__(self):
        super().__init__()
        self.rows = []
        self.reached_playoffs = False
        self._in_table = False
        self._in_tbody = False
        self._row = None
        self._row_is_header = False
        self._row_text = []
        self._cell = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table" and a.get("id") == "schedule":
            self._in_table = True
        if not self._in_table or self.reached_playoffs:
            return
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._row = {}
            self._row_is_header = "thead" in (a.get("class") or "")
            self._row_text = []
        elif tag in ("td", "th") and self._row is not None and a.get("data-stat"):
            self._cell = a["data-stat"]
            self._row[self._cell] = {"text": "", "csk": a.get("csk"), "href": None}
        elif tag == "a" and self._cell and self._row is not None:
            self._row[self._cell]["href"] = a.get("href")

    def handle_endtag(self, tag):
        if not self._in_table:
            return
        if tag in ("td", "th"):
            self._cell = None
        elif tag == "tr" and self._row is not None:
            # 정규시즌과 플레이오프 사이에는 "Playoffs" 구분 행이 있다.
            if self._row_is_header and "Playoffs" in "".join(self._row_text):
                self.reached_playoffs = True
            elif not self._row_is_header:
                self.rows.append(self._row)
            self._row = None
        elif tag == "tbody":
            self._in_tbody = False
        elif tag == "table":
            self._in_table = False

    def handle_data(self, data):
        if self._row is not None:
            self._row_text.append(data)
            if self._cell:
                self._row[self._cell]["text"] += data


def _bbref_team(cell):
    href = cell.get("href") or ""
    parts = href.strip("/").split("/")  # teams/HOU/2026.html
    if len(parts) >= 2 and parts[0] == "teams":
        abbr = normalize(parts[1])
        if abbr:
            return abbr
    return normalize(cell["text"])


def _bbref_date(cell):
    csk = cell.get("csk") or ""
    if csk[:8].isdigit():
        return f"{csk[:4]}-{csk[4:6]}-{csk[6:8]}"
    return datetime.strptime(cell["text"].strip(), "%a, %b %d, %Y").strftime("%Y-%m-%d")


def fetch_bbref(season, raw_dir=None):
    records = []
    for i, month in enumerate(BBREF_MONTHS):
        if i:
            time.sleep(BBREF_DELAY_SEC)
        url = BBREF_URL.format(season=season, month=month)
        try:
            html = _get(url).decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:  # 해당 월에 경기가 없는 시즌
                continue
            raise
        if raw_dir:
            raw_dir.mkdir(parents=True, exist_ok=True)
            (raw_dir / f"bbref_{season}_{month}.html").write_text(html, encoding="utf-8")
        parser = _ScheduleParser()
        parser.feed(html)
        for row in parser.rows:
            try:
                away_pts = int(row["visitor_pts"]["text"])
                home_pts = int(row["home_pts"]["text"])
            except (KeyError, ValueError):
                continue  # 아직 치르지 않은 경기
            records.append({
                "date": _bbref_date(row["date_game"]),
                "away": _bbref_team(row["visitor_team_name"]),
                "home": _bbref_team(row["home_team_name"]),
                "away_pts": away_pts,
                "home_pts": home_pts,
            })
        print(f"  bbref {season} {month}: {len(parser.rows)} rows", file=sys.stderr)
        if parser.reached_playoffs:
            break
    return pd.DataFrame(records, columns=COLUMNS)


def fetch_sportsdataverse(season):
    raw = pd.read_csv(io.BytesIO(_get(SDV_URL.format(season=season))))
    reg = raw[raw["season_type"] == 2]  # 2 = 정규시즌 (3 = 플레이오프, 5 = 플레이인)
    home = reg[reg["team_home_away"] == "home"]
    return pd.DataFrame({
        "date": pd.to_datetime(home["game_date"]).dt.strftime("%Y-%m-%d"),
        "away": home["opponent_team_display_name"].map(normalize),
        "home": home["team_display_name"].map(normalize),
        "away_pts": home["opponent_team_score"].astype(int),
        "home_pts": home["team_score"].astype(int),
    }, columns=COLUMNS)


def clean_regular_season(games, log=print):
    """순위에 반영되지 않는 경기를 걸러낸다.

    - 올스타전 등 NBA 30개 팀이 아닌 경기
    - NBA컵 결승: 그날 유일한 경기이고 두 팀 모두 83경기가 되는 경기
    - 모든 팀이 82경기를 마친 날 이후의 경기(플레이인)
    """
    g = games.dropna(subset=["away", "home"]).sort_values("date", kind="stable")
    g = g.reset_index(drop=True)
    dropped = len(games) - len(g)
    if dropped:
        log(f"  NBA 팀이 아닌 경기 {dropped}개 제외")

    counts = pd.concat([g["away"], g["home"]]).value_counts()
    over = set(counts[counts > 82].index)
    per_day = g["date"].map(g["date"].value_counts())
    cup = g[(per_day == 1) & g["away"].isin(over) & g["home"].isin(over)]
    for _, r in cup.iterrows():
        log(f"  NBA컵 결승 제외: {r.date} {r.away} {r.away_pts} @ {r.home} {r.home_pts}")
    g = g.drop(cup.index).reset_index(drop=True)

    played = {}
    end = None
    for date, day in g.groupby("date", sort=True):
        for t in pd.concat([day["away"], day["home"]]):
            played[t] = played.get(t, 0) + 1
        if len(played) == 30 and min(played.values()) >= 82:
            end = date
            break
    if end is not None:
        late = g[g["date"] > end]
        if len(late):
            log(f"  정규시즌 종료({end}) 이후 경기 {len(late)}개 제외")
        g = g[g["date"] <= end].reset_index(drop=True)
    return g


def load_games(season, source, cache_dir, refresh=False, log=print):
    """정리된 정규시즌 경기 표를 돌려준다. 결과는 cache_dir 에 CSV로 저장한다."""
    cache = cache_dir / f"games_{season}.csv"
    if cache.exists() and not refresh:
        log(f"{season}: 캐시 사용 ({cache})")
        return pd.read_csv(cache)

    sources = ["bbref", "sportsdataverse"] if source == "auto" else [source]
    last_error = None
    for name in sources:
        log(f"{season}: {name} 에서 수집 중...")
        try:
            if name == "bbref":
                games = fetch_bbref(season, raw_dir=cache_dir / "raw")
            else:
                games = fetch_sportsdataverse(season)
        except (urllib.error.URLError, OSError) as e:
            log(f"  {name} 실패: {e}")
            last_error = e
            continue
        games = clean_regular_season(games, log=log)
        games.insert(0, "source", name)
        cache_dir.mkdir(parents=True, exist_ok=True)
        games.to_csv(cache, index=False)
        return games
    raise RuntimeError(f"{season} 시즌 데이터를 가져오지 못했습니다") from last_error
