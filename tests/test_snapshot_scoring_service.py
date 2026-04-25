from datetime import date

import pytest

from src.models.kpi_snapshot import KpiSnapshot
from src.services.scoring_service import (
    GROWTH_SCORE_KEY,
    QUALITY_SCORE_KEY,
    RISK_SCORE_KEY,
    TOTAL_SCORE_KEY,
    VALUE_SCORE_KEY,
    CompanyTotalScore,
    ScoringService,
    apply_scores,
    compute_snapshot_scores,
    describe_snapshot_score,
    rank_companies_by_total_score,
)


def _make_snapshot(metrics: dict[str, object]) -> KpiSnapshot:
    return KpiSnapshot(
        company_id=1,
        snapshot_date=date(2025, 1, 31),
        metrics=metrics,
        source="ratio_service_v1",
    )


def test_complete_snapshot_scores_are_applied():
    snapshot = _make_snapshot(
        {
            "roe": 0.20,
            "roic": 0.15,
            "operating_margin": 0.15,
            "gross_margin": 0.35,
            "pe_ratio": 8.0,
            "pb_ratio": 0.8,
            "ev_ebitda": 5.0,
            "fcf_yield": 0.12,
            "revenue_growth": 0.15,
            "ebitda_growth": 0.12,
            "net_debt_to_ebitda": 0.5,
            "current_ratio": 1.8,
            "interest_coverage": 8.0,
        }
    )

    updated = apply_scores(snapshot)

    assert updated.metrics[QUALITY_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[VALUE_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[GROWTH_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[RISK_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[TOTAL_SCORE_KEY] == pytest.approx(100.0)


def test_missing_values_do_not_crash_and_are_penalized():
    snapshot = _make_snapshot(
        {
            "pe_ratio": 10.0,
            "irrelevant_key": "unused",
        }
    )

    scores = compute_snapshot_scores(snapshot)

    assert scores.quality == pytest.approx(0.0)
    assert scores.value == pytest.approx(100.0)
    assert scores.growth == pytest.approx(0.0)
    assert scores.risk == pytest.approx(0.0)
    assert scores.total == pytest.approx(30.0)


def test_bad_ratios_are_penalized():
    snapshot = _make_snapshot(
        {
            "roe": -0.05,
            "roic": -0.02,
            "operating_margin": -0.01,
            "gross_margin": 0.05,
            "pe_ratio": 35.0,
            "pb_ratio": 5.0,
            "ev_ebitda": 20.0,
            "fcf_yield": -0.02,
            "revenue_growth": -0.20,
            "ebitda_growth": -0.10,
            "net_debt_to_ebitda": 6.0,
            "current_ratio": 0.5,
            "interest_coverage": 0.2,
        }
    )

    scores = compute_snapshot_scores(snapshot)

    assert scores.quality == pytest.approx(0.0)
    assert scores.value == pytest.approx(0.0)
    assert scores.growth == pytest.approx(0.0)
    assert scores.risk == pytest.approx(0.0)
    assert scores.total == pytest.approx(0.0)


def test_total_score_is_deterministic():
    snapshot = _make_snapshot(
        {
            "roe": 0.11,
            "operating_margin": 0.09,
            "pe_ratio": 14.0,
            "ev_ebitda": 9.0,
            "revenue_growth": 0.07,
            "ebitda_growth": 0.05,
            "net_debt_to_ebitda": 2.0,
            "current_ratio": 1.1,
            "interest_coverage": 3.0,
        }
    )

    service = ScoringService()
    first = service.compute_snapshot_scores(snapshot)
    second = service.compute_snapshot_scores(snapshot)

    assert first == second
    assert first.total == pytest.approx(69.95)


def test_rank_companies_by_total_score_computes_sector_rank():
    ranking = rank_companies_by_total_score(
        [
            CompanyTotalScore(company_id=1, ticker="A.PA", total_score=80.0, sector="Energy"),
            CompanyTotalScore(company_id=2, ticker="B.PA", total_score=90.0, sector="Energy"),
            CompanyTotalScore(company_id=3, ticker="C.PA", total_score=85.0, sector="Tech"),
            CompanyTotalScore(company_id=4, ticker="D.PA", total_score=88.0, sector=None),
        ]
    )

    assert [entry.company_id for entry in ranking] == [2, 4, 3, 1]
    assert [entry.rank for entry in ranking] == [1, 2, 3, 4]
    assert [entry.sector_rank for entry in ranking] == [1, None, 1, 2]


def test_rank_companies_by_total_score_handles_missing_sector_or_score():
    ranking = rank_companies_by_total_score(
        [
            CompanyTotalScore(company_id=5, ticker="E.PA", total_score=70.0, sector=""),
            CompanyTotalScore(company_id=6, ticker="F.PA", total_score=None, sector="Energy"),
            CompanyTotalScore(company_id=7, ticker="G.PA", total_score=65.0, sector="Energy"),
        ]
    )

    assert [entry.company_id for entry in ranking] == [5, 7, 6]
    assert [entry.rank for entry in ranking] == [1, 2, None]
    assert [entry.sector_rank for entry in ranking] == [None, 1, None]


def test_describe_snapshot_score_is_readable_and_stable():
    scored_snapshot = apply_scores(
        _make_snapshot(
            {
                "roe": 0.20,
                "roic": 0.16,
                "operating_margin": 0.14,
                "gross_margin": 0.33,
                "pe_ratio": 8.5,
                "pb_ratio": 1.1,
                "ev_ebitda": 5.5,
                "fcf_yield": 0.10,
                "revenue_growth": 0.12,
                "ebitda_growth": 0.09,
                "net_debt_to_ebitda": 1.8,
                "current_ratio": 1.3,
                "interest_coverage": 5.0,
            }
        )
    )

    first = describe_snapshot_score(scored_snapshot)
    second = describe_snapshot_score(scored_snapshot)

    assert first == second
    assert first.total_score is not None
    assert first.quality is not None
    assert first.value is not None
    assert first.growth is not None
    assert first.risk is not None
    assert 1 <= len(first.strengths) <= 3
    assert 1 <= len(first.weaknesses) <= 3
    assert "total" in first.summary
    assert "strengths:" in first.summary
    assert "weaknesses:" in first.summary


def test_describe_snapshot_score_handles_missing_sub_scores():
    snapshot = _make_snapshot({"total_score": 78.0})

    explanation = describe_snapshot_score(snapshot)

    assert explanation.total_score == pytest.approx(78.0)
    assert explanation.quality == pytest.approx(0.0)
    assert explanation.value == pytest.approx(0.0)
    assert explanation.growth == pytest.approx(0.0)
    assert explanation.risk == pytest.approx(0.0)
    assert len(explanation.strengths) == 1
    assert 1 <= len(explanation.weaknesses) <= 3


def test_describe_snapshot_score_handles_missing_snapshot():
    explanation = describe_snapshot_score(None)

    assert explanation.total_score is None
    assert explanation.quality is None
    assert explanation.value is None
    assert explanation.growth is None
    assert explanation.risk is None
    assert explanation.strengths == ()
    assert explanation.weaknesses == ()
    assert explanation.summary == "score unavailable: no snapshot data."
