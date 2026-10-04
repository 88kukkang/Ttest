"""경기 결과로 팀별 경기 로그와 날짜별 순위를 계산한다."""

from collections import defaultdict
from fractions import Fraction

from .teams import TEAMS


class _Record:
    __slots__ = ("w", "l", "pf", "pa", "cw", "cl")

    def __init__(self):
        self.w = self.l = self.pf = self.pa = self.cw = self.cl = 0


def _pct(w, l):
    return Fraction(w, w + l) if w + l else Fraction(1, 2)


def _rank(teams, rec, h2h):
    """승률 순으로 정렬한다. 동률이면 (승-패), 상대전적, 컨퍼런스 승률, 득실차 순.

    NBA 공식 타이브레이커(디비전 우승 여부 등)를 단순화한 것이라
    최종 시드가 공식 순위와 다를 수 있다.
    """
    by_pct = defaultdict(list)
    for t in teams:
        by_pct[_pct(rec[t].w, rec[t].l)].append(t)

    ordered = []
    for pct in sorted(by_pct, reverse=True):
        group = by_pct[pct]

        def key(t, group=group):
            r = rec[t]
            hw = sum(h2h[t][o] for o in group if o != t)
            hl = sum(h2h[o][t] for o in group if o != t)
            return (-(r.w - r.l), -_pct(hw, hl), -_pct(r.cw, r.cl), -(r.pf - r.pa), t)

        ordered.extend(sorted(group, key=key))
    return {t: i + 1 for i, t in enumerate(ordered)}


def build_logs(games):
    """팀별 경기 로그 리스트를 돌려준다.

    각 항목: date, opp, home(bool), pts, opp_pts, conf_rank, league_rank
    순위는 그날 모든 경기가 끝난 시점의 순위다.
    """
    rec = {t: _Record() for t in TEAMS}
    h2h = {t: defaultdict(int) for t in TEAMS}
    logs = {t: [] for t in TEAMS}
    east = [t for t in TEAMS if TEAMS[t]["conf"] == "E"]
    west = [t for t in TEAMS if TEAMS[t]["conf"] == "W"]

    for date, day in games.sort_values("date", kind="stable").groupby("date", sort=True):
        today = []
        for g in day.itertuples(index=False):
            same_conf = TEAMS[g.away]["conf"] == TEAMS[g.home]["conf"]
            for team, opp, pts, opp_pts, home in (
                (g.away, g.home, g.away_pts, g.home_pts, False),
                (g.home, g.away, g.home_pts, g.away_pts, True),
            ):
                r = rec[team]
                won = pts > opp_pts
                r.w += won
                r.l += not won
                r.pf += pts
                r.pa += opp_pts
                if same_conf:
                    r.cw += won
                    r.cl += not won
                if won:
                    h2h[team][opp] += 1
                entry = {"date": date, "opp": opp, "home": home,
                         "pts": int(pts), "opp_pts": int(opp_pts)}
                logs[team].append(entry)
                today.append((team, entry))

        conf_rank = {**_rank(east, rec, h2h), **_rank(west, rec, h2h)}
        league_rank = _rank(list(TEAMS), rec, h2h)
        for team, entry in today:
            entry["conf_rank"] = conf_rank[team]
            entry["league_rank"] = league_rank[team]

    return logs
