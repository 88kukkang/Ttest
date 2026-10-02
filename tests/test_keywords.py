from moisdb.analysis.keywords import (
    Doc,
    cooccurring,
    distinctive_by_period,
    period_of,
    term_trend,
    top_terms,
)


def _docs():
    june = [Doc(i, f"2025-06-{10 + i:02d}", "A과", f"6월{i}", ["소비쿠폰", "지급", "지자체"]) for i in range(5)]
    july = [Doc(10 + i, f"2025-07-{10 + i:02d}", "B과", f"7월{i}", ["호우", "피해", "지자체", "복구"]) for i in range(5)]
    july.append(Doc(20, "2025-07-20", "B과", "7월x", ["소비쿠폰", "지급", "지급"]))
    return june + july


def test_top_terms_counts_documents_not_repeats():
    rows = {r["term"]: r for r in top_terms(_docs())}
    assert rows["지자체"]["df"] == 10
    assert rows["지급"]["df"] == 6 and rows["지급"]["tf"] == 7


def test_term_trend_share_by_month():
    rows = term_trend(_docs(), ["소비쿠폰"])
    assert rows == [
        {"period": "2025-06", "term": "소비쿠폰", "docs": 5, "total": 5, "share": 1.0},
        {"period": "2025-07", "term": "소비쿠폰", "docs": 1, "total": 6, "share": 0.1667},
    ]


def test_distinctive_by_period_finds_monthly_issue():
    rows = distinctive_by_period(_docs(), n=2)
    top = {r["period"]: r["term"] for r in rows if r["rank"] == 1}
    assert top["2025-06"] in ("소비쿠폰", "지급")
    assert top["2025-07"] in ("호우", "피해", "복구")
    # 모든 달에 고르게 나온 단어는 특징어가 아니다
    assert all(r["term"] != "지자체" for r in rows)


def test_cooccurring():
    rows = cooccurring(_docs(), "호우", min_co=1)
    terms = [r["term"] for r in rows]
    assert terms[:2] == ["피해", "복구"] or terms[:2] == ["복구", "피해"]
    assert "소비쿠폰" not in terms


def test_period_of():
    assert period_of("2025-06-04") == "2025-06"
    assert period_of("2025-06-04", "week") == "2025-W23"
    assert period_of("2025-11-30", "quarter") == "2025-Q4"
