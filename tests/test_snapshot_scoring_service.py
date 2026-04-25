from datetime import date

import pytest

from src.models.kpi_snapshot import KpiSnapshot
from src.services.scoring_service import (
    GROWTH_SCORE_KEY,
    QUALITY_SCORE_KEY,
    RISK_SCORE_KEY,
    TOTAL_SCORE_KEY,
    VALUE_SCORE_KEY,
    ScoringService,
    apply_scores,
    compute_snapshot_scores,
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
