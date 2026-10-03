"""키워드 분석: 상위 키워드, 기간별 추이, 기간별 특징어, 연관어.

빈도는 기본적으로 '문서 빈도(DF, 그 단어가 나온 보도자료 수)'를 쓴다.
한 보도자료 안에서 같은 단어가 수십 번 반복돼도 1건으로 세므로, '얼마나 자주 다뤄졌나'를 보기에 적합하다.
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date


@dataclass
class Doc:
    id: int
    date: str  # YYYY-MM-DD
    department: str | None
    title: str
    tokens: list[str]

    @property
    def vocab(self) -> set[str]:
        return set(self.tokens)


def load_corpus(
    conn: sqlite3.Connection,
    start: str | None = None,
    end: str | None = None,
    department: str | None = None,
    source: str = "mois",
) -> list[Doc]:
    sql = """SELECT r.id, r.published_date, r.department, r.title, t.tokens
             FROM releases r JOIN doc_tokens t ON t.release_id = r.id
             WHERE r.source = ? AND r.published_date IS NOT NULL"""
    params: list = [source]
    if start:
        sql += " AND r.published_date >= ?"
        params.append(start)
    if end:
        sql += " AND r.published_date <= ?"
        params.append(end)
    if department:
        sql += " AND r.department LIKE ?"
        params.append(f"%{department}%")
    sql += " ORDER BY r.published_date, r.id"
    return [
        Doc(row["id"], row["published_date"], row["department"], row["title"] or "", row["tokens"].split())
        for row in conn.execute(sql, params)
    ]


def period_of(day: str, freq: str = "month") -> str:
    if freq == "month":
        return day[:7]
    if freq == "week":
        y, w, _ = date.fromisoformat(day).isocalendar()
        return f"{y}-W{w:02d}"
    if freq == "quarter":
        return f"{day[:4]}-Q{(int(day[5:7]) - 1) // 3 + 1}"
    raise ValueError(f"지원하지 않는 단위: {freq}")


def doc_freq(docs: list[Doc]) -> Counter:
    df: Counter = Counter()
    for d in docs:
        df.update(d.vocab)
    return df


def top_terms(docs: list[Doc], n: int = 50) -> list[dict]:
    tf: Counter = Counter()
    for d in docs:
        tf.update(d.tokens)
    df = doc_freq(docs)
    total = len(docs) or 1
    return [
        {"term": term, "df": cnt, "df_ratio": round(cnt / total, 4), "tf": tf[term]}
        for term, cnt in df.most_common(n)
    ]


def term_trend(docs: list[Doc], terms: list[str], freq: str = "month") -> list[dict]:
    """기간별로 각 단어가 나온 문서 수와 비율(그 기간 전체 보도자료 대비)."""
    by_period: dict[str, list[Doc]] = defaultdict(list)
    for d in docs:
        by_period[period_of(d.date, freq)].append(d)
    rows = []
    for period in sorted(by_period):
        group = by_period[period]
        for term in terms:
            hits = sum(1 for d in group if term in d.vocab)
            rows.append({"period": period, "term": term, "docs": hits, "total": len(group),
                         "share": round(hits / len(group), 4)})
    return rows


def log_odds(target: Counter, reference: Counter, prior_total: float = 500.0) -> dict[str, tuple[float, float]]:
    """정보적 디리클레 사전분포를 쓴 로그오즈비 (Monroe et al., 2008).

    두 집단의 단어 빈도를 비교해 target 쪽에 유난히 많이 나온 단어일수록 z 값이 크다.
    빈도가 낮은 단어가 과대평가되지 않도록 전체 빈도에 비례하는 사전값으로 보정한다.
    반환: {단어: (z, delta)}
    """
    pooled = target + reference
    pooled_total = sum(pooled.values()) or 1
    n_t, n_r = sum(target.values()), sum(reference.values())
    out = {}
    for term, cnt in pooled.items():
        a = prior_total * cnt / pooled_total
        y_t, y_r = target.get(term, 0), reference.get(term, 0)
        delta = (math.log((y_t + a) / (n_t + prior_total - y_t - a))
                 - math.log((y_r + a) / (n_r + prior_total - y_r - a)))
        var = 1 / (y_t + a) + 1 / (y_r + a)
        out[term] = (delta / math.sqrt(var), delta)
    return out


def distinctive_terms(target_docs: list[Doc], ref_docs: list[Doc], n: int = 20, min_df: int = 2) -> list[dict]:
    t_df, r_df = doc_freq(target_docs), doc_freq(ref_docs)
    scores = log_odds(t_df, r_df)
    ranked = sorted(  # 점수가 같으면 문서 수가 많은 말, 그다음 가나다순 (실행마다 순서가 같게)
        ((term, z, d) for term, (z, d) in scores.items() if t_df.get(term, 0) >= min_df),
        key=lambda x: (-x[1], -t_df[x[0]], x[0]),
    )
    return [{"term": term, "z": round(z, 2), "df": t_df[term], "ref_df": r_df.get(term, 0)}
            for term, z, _ in ranked[:n]]


def distinctive_by_period(docs: list[Doc], freq: str = "month", n: int = 15, min_df: int = 2) -> list[dict]:
    """기간마다 '그 기간 vs 나머지 전체'로 특징어를 뽑는다 → 월별 이슈 키워드."""
    by_period: dict[str, list[Doc]] = defaultdict(list)
    for d in docs:
        by_period[period_of(d.date, freq)].append(d)
    rows = []
    for period in sorted(by_period):
        target = by_period[period]
        ref = [d for d in docs if period_of(d.date, freq) != period]
        for rank, item in enumerate(distinctive_terms(target, ref, n=n, min_df=min_df), start=1):
            rows.append({"period": period, "rank": rank, "n_docs": len(target), **item})
    return rows


def cooccurring(docs: list[Doc], term: str, n: int = 30, min_co: int = 2) -> list[dict]:
    """term 이 나온 보도자료에 함께 나온 단어. lift = P(단어|term 포함 문서) / P(단어)."""
    with_term = [d for d in docs if term in d.vocab]
    if not with_term:
        return []
    co = doc_freq(with_term)
    df = doc_freq(docs)
    total, k = len(docs), len(with_term)
    rows = []
    for other, c in co.items():
        if other == term or c < min_co:
            continue
        lift = (c / k) / (df[other] / total)
        rows.append({"term": other, "co_docs": c, "docs": df[other], "lift": round(lift, 2)})
    rows.sort(key=lambda r: (r["co_docs"] * math.log1p(r["lift"])), reverse=True)
    return rows[:n]
