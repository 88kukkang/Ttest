import unittest

import pandas as pd

from nba_trend.sources import _ScheduleParser, _bbref_date, _bbref_team, clean_regular_season
from nba_trend.standings import build_logs

# basketball-reference 일정 표 구조를 줄여 옮긴 예시
BBREF_SAMPLE = """
<table class="suppress_glossary sortable stats_table" id="schedule" data-cols-to-freeze=",1">
<thead><tr><th aria-label="Date" data-stat="date_game" scope="col">Date</th>
<th data-stat="visitor_team_name" scope="col">Visitor/Neutral</th><th data-stat="visitor_pts" scope="col">PTS</th>
<th data-stat="home_team_name" scope="col">Home/Neutral</th><th data-stat="home_pts" scope="col">PTS</th></tr></thead>
<tbody>
<tr><th scope="row" class="left " data-stat="date_game" csk="202604120BOS"><a href="/boxscores/index.fcgi?month=4&amp;day=12&amp;year=2026">Sun, Apr 12, 2026</a></th>
<td class="right " data-stat="game_start_time">1:00p</td>
<td class="left " data-stat="visitor_team_name" csk="BRK.2026041201"><a href="/teams/BRK/2026.html">Brooklyn Nets</a></td>
<td class="right " data-stat="visitor_pts">101</td>
<td class="left " data-stat="home_team_name" csk="BOS.2026041201"><a href="/teams/BOS/2026.html">Boston Celtics</a></td>
<td class="right " data-stat="home_pts">117</td>
<td class="center " data-stat="box_score_text"><a href="/boxscores/202604120BOS.html">Box Score</a></td></tr>
<tr class="thead"><th colspan="11">Playoffs</th></tr>
<tr><th scope="row" class="left " data-stat="date_game" csk="202604140MIA">Tue, Apr 14, 2026</th>
<td class="left " data-stat="visitor_team_name"><a href="/teams/CHO/2026.html">Charlotte Hornets</a></td>
<td class="right " data-stat="visitor_pts">99</td>
<td class="left " data-stat="home_team_name"><a href="/teams/MIA/2026.html">Miami Heat</a></td>
<td class="right " data-stat="home_pts">104</td></tr>
</tbody></table>
"""


class BbrefParserTest(unittest.TestCase):
    def test_reads_rows_until_playoffs(self):
        p = _ScheduleParser()
        p.feed(BBREF_SAMPLE)
        self.assertTrue(p.reached_playoffs)
        self.assertEqual(len(p.rows), 1)
        row = p.rows[0]
        self.assertEqual(_bbref_date(row["date_game"]), "2026-04-12")
        self.assertEqual(_bbref_team(row["visitor_team_name"]), "BKN")
        self.assertEqual(_bbref_team(row["home_team_name"]), "BOS")
        self.assertEqual(int(row["home_pts"]["text"]), 117)

    def test_date_without_csk(self):
        cell = {"text": "Tue, Oct 21, 2025", "csk": None}
        self.assertEqual(_bbref_date(cell), "2025-10-21")


class CleanTest(unittest.TestCase):
    def test_drops_cup_final_and_non_nba(self):
        cols = ["date", "away", "home", "away_pts", "home_pts"]
        # NYK, SAS 가 결승 포함 83경기가 되도록 채운다
        filler = [("2025-11-01", "NYK", "SAS", 101, 100)] * 81
        games = pd.DataFrame(filler + [
            ("2025-12-15", "NYK", "SAS", 100, 98),
            ("2025-12-15", "BOS", "DET", 100, 98),
            ("2025-12-16", "SAS", "NYK", 113, 124),  # NBA컵 결승: 그날 유일한 경기
            ("2026-02-15", None, None, 150, 140),     # 올스타전 (normalize 결과 None)
        ], columns=cols)
        out = clean_regular_season(games, log=lambda *_: None)
        self.assertNotIn("2025-12-16", set(out["date"]))
        self.assertEqual(len(out), 83)


class StandingsTest(unittest.TestCase):
    def test_ranks_after_each_day(self):
        games = pd.DataFrame([
            ("2025-10-21", "BOS", "NYK", 90, 100),
            ("2025-10-22", "BOS", "DET", 110, 100),
            ("2025-10-22", "NYK", "MIA", 95, 99),
        ], columns=["date", "away", "home", "away_pts", "home_pts"])
        logs = build_logs(games)
        # 10/21 뒤: NYK 1-0 이 동부 1위, BOS 0-1 은 0경기 팀들(.500) 아래
        self.assertEqual(logs["NYK"][0]["conf_rank"], 1)
        self.assertEqual(logs["BOS"][0]["conf_rank"], 15)
        # 10/22 뒤: BOS 1-1, NYK 1-1 동률 -> 상대 전적에서 NYK 우위
        self.assertLess(logs["NYK"][1]["conf_rank"], logs["BOS"][1]["conf_rank"])
        self.assertEqual(logs["MIA"][0]["conf_rank"], 1)


if __name__ == "__main__":
    unittest.main()
