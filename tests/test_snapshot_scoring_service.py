from datetime import date

import pytest

from src.models.kpi_snapshot import KpiSnapshot
from src.services.scoring_config import SnapshotSubScoreWeights
from src.services.scoring_service import (
    GROWTH_SCORE_KEY,
    PROFILE_LABEL_KEY,
    QUALITY_SCORE_KEY,
    RISK_SCORE_KEY,
    SCORE_WEIGHT_GROWTH_KEY,
    SCORE_WEIGHT_QUALITY_KEY,
    SCORE_WEIGHT_RISK_KEY,
    SCORE_WEIGHT_VALUE_KEY,
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


def _all_good_metrics() -> dict[str, object]:
    return {
        "gross_margin": 0.45,
        "roic": 0.18,
        "roce": 0.18,
        "asset_turnover": 1.2,
        "gross_profit_growth": 0.20,
        "revenue_growth": 0.15,
        "revenue_cagr_3y": 0.12,
        "ebitda_growth": 0.20,
        "gross_profitability": 0.35,
        "roa": 0.10,
        "ebit_margin": 0.15,
        "ronic": 0.20,
        "capex_to_revenue": 0.02,
        "shares_growth": -0.02,
        "net_debt_to_ebitda": 0.5,
        "interest_coverage": 8.0,
        "current_ratio": 2.0,
        "debt_to_equity": 0.3,
        "cfo_to_net_income": 1.3,
        "cfo_to_ebit": 1.1,
        "fcf_margin": 0.10,
        "cfo_margin": 0.10,
        "cfo_streak_negative": 0,
        "accrual_ratio": -0.08,
        "ev_ebit": 6.0,
        "ev_fcf": 10.0,
        "ev_sales": 0.8,
        "pb_ratio": 0.8,
        "altman_z_proxy": 4.0,
        "beta": 0.6,
    }


def _all_bad_metrics() -> dict[str, object]:
    return {
        "gross_margin": 0.10,
        "roic": -0.01,
        "roce": -0.01,
        "asset_turnover": 0.2,
        "gross_profit_growth": -0.10,
        "revenue_growth": -0.10,
        "revenue_cagr_3y": -0.05,
        "ebitda_growth": -0.15,
        "gross_profitability": 0.02,
        "roa": -0.02,
        "ebit_margin": -0.03,
        "ronic": -0.05,
        "capex_to_revenue": 0.20,
        "shares_growth": 0.10,
        "net_debt_to_ebitda": 6.0,
        "interest_coverage": 0.5,
        "current_ratio": 0.5,
        "debt_to_equity": 3.0,
        "cfo_to_net_income": 0.3,
        "cfo_to_ebit": 0.2,
        "fcf_margin": -0.05,
        "cfo_margin": -0.05,
        "cfo_streak_negative": 2,
        "accrual_ratio": 0.15,
        "ev_ebit": 25.0,
        "ev_fcf": 40.0,
        "ev_sales": 5.0,
        "pb_ratio": 4.0,
        "altman_z_proxy": 0.8,
        "beta": 2.0,
    }


def test_complete_snapshot_scores_are_applied():
    snapshot = _make_snapshot(_all_good_metrics())
    updated = apply_scores(snapshot)

    assert updated.metrics[QUALITY_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[VALUE_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[GROWTH_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[RISK_SCORE_KEY] == pytest.approx(100.0)
    assert updated.metrics[TOTAL_SCORE_KEY] == pytest.approx(100.0)


def test_missing_values_do_not_crash_and_are_penalized():
    snapshot = _make_snapshot(
        {
            "ev_ebit": 8.0,
            "irrelevant_key": "unused",
        }
    )

    scores = compute_snapshot_scores(snapshot)

    assert scores.quality == pytest.approx(0.0)
    assert scores.value == pytest.approx(100.0)
    assert scores.growth == pytest.approx(0.0)
    assert scores.risk == pytest.approx(0.0)
    assert scores.total < 50.0
    assert scores.total > 0.0


def test_bad_ratios_are_penalized():
    snapshot = _make_snapshot(_all_bad_metrics())
    scores = compute_snapshot_scores(snapshot)

    assert scores.quality == pytest.approx(0.0)
    assert scores.value == pytest.approx(0.0)
    assert scores.growth == pytest.approx(0.0)
    assert scores.risk == pytest.approx(0.0)
    assert scores.total == pytest.approx(0.0)


def test_total_score_is_deterministic():
    snapshot = _make_snapshot(
        {
            "roic": 0.10,
            "gross_margin": 0.30,
            "revenue_growth": 0.07,
            "ebitda_growth": 0.05,
            "ebit_margin": 0.09,
            "net_debt_to_ebitda": 2.0,
            "current_ratio": 1.1,
            "interest_coverage": 3.0,
            "ev_ebit": 12.0,
            "pb_ratio": 1.5,
        }
    )

    service = ScoringService()
    first = service.compute_snapshot_scores(snapshot)
    second = service.compute_snapshot_scores(snapshot)

    assert first == second
    assert 0.0 < first.total < 100.0


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
    scored_snapshot = apply_scores(_make_snapshot(_all_good_metrics()))

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


def test_apply_scores_persists_weight_configuration():
    service = ScoringService(
        sub_score_weights=SnapshotSubScoreWeights(
            quality_weight=0.40,
            value_weight=0.30,
            growth_weight=0.20,
            risk_weight=0.10,
        )
    )
    snapshot = _make_snapshot({"roic": 0.2, "ev_ebit": 8.0})

    updated = service.apply_scores(snapshot)

    assert updated.metrics[SCORE_WEIGHT_QUALITY_KEY] == pytest.approx(0.40)
    assert updated.metrics[SCORE_WEIGHT_VALUE_KEY] == pytest.approx(0.30)
    assert updated.metrics[SCORE_WEIGHT_GROWTH_KEY] == pytest.approx(0.20)
    assert updated.metrics[SCORE_WEIGHT_RISK_KEY] == pytest.approx(0.10)


def test_describe_snapshot_score_exposes_deterministic_breakdown_and_drivers():
    metrics = _all_good_metrics()
    metrics["ev_ebit"] = 16.0
    metrics["ev_fcf"] = 25.0
    metrics["ev_sales"] = 3.0
    metrics["pb_ratio"] = 2.5
    snapshot = _make_snapshot(metrics)
    scored_snapshot = apply_scores(snapshot)

    first = describe_snapshot_score(scored_snapshot)
    second = describe_snapshot_score(scored_snapshot)

    assert first == second
    assert len(first.weights) == 4
    assert len(first.category_contributions) == 4
    assert first.total_score is not None
    total_from_contributions = sum(item.weighted_points for item in first.category_contributions)
    assert total_from_contributions == pytest.approx(first.total_score, abs=15.0)
    assert "construction:" in first.summary
    assert "positive drivers:" in first.summary
    assert "negative drivers:" in first.summary


def test_weight_change_modifies_ranking_and_stays_deterministic():
    metrics_quality_heavy = {
        "roic": 0.20,
        "gross_margin": 0.50,
        "roce": 0.20,
        "asset_turnover": 1.5,
        "ebit_margin": 0.18,
        "roa": 0.12,
        "gross_profitability": 0.40,
        "cfo_to_net_income": 1.4,
        "cfo_to_ebit": 1.2,
        "fcf_margin": 0.12,
        "accrual_ratio": -0.10,
        "ev_ebit": 25.0,
        "ev_fcf": 35.0,
        "ev_sales": 5.0,
        "pb_ratio": 4.0,
    }
    metrics_value_heavy = {
        "roic": -0.02,
        "gross_margin": 0.10,
        "roce": -0.01,
        "asset_turnover": 0.2,
        "ebit_margin": -0.02,
        "roa": -0.01,
        "gross_profitability": 0.03,
        "ev_ebit": 6.0,
        "ev_fcf": 8.0,
        "ev_sales": 0.5,
        "pb_ratio": 0.6,
    }

    quality_service = ScoringService(
        sub_score_weights=SnapshotSubScoreWeights(
            quality_weight=0.70,
            value_weight=0.10,
            growth_weight=0.10,
            risk_weight=0.10,
        )
    )
    value_service = ScoringService(
        sub_score_weights=SnapshotSubScoreWeights(
            quality_weight=0.10,
            value_weight=0.70,
            growth_weight=0.10,
            risk_weight=0.10,
        )
    )

    quality_a = quality_service.compute_metrics_scores(metrics_quality_heavy).total
    quality_b = quality_service.compute_metrics_scores(metrics_value_heavy).total
    value_a = value_service.compute_metrics_scores(metrics_quality_heavy).total
    value_b = value_service.compute_metrics_scores(metrics_value_heavy).total

    assert quality_a > quality_b

    ranking_value_first = value_service.rank_companies_by_total_score(
        [
            CompanyTotalScore(company_id=1, ticker="Q.PA", total_score=value_a, sector="Tech"),
            CompanyTotalScore(company_id=2, ticker="V.PA", total_score=value_b, sector="Tech"),
        ]
    )
    ranking_value_second = value_service.rank_companies_by_total_score(
        [
            CompanyTotalScore(company_id=1, ticker="Q.PA", total_score=value_a, sector="Tech"),
            CompanyTotalScore(company_id=2, ticker="V.PA", total_score=value_b, sector="Tech"),
        ]
    )
    assert [entry.company_id for entry in ranking_value_first] == [2, 1]
    assert ranking_value_first == ranking_value_second


def test_caps_limit_score_for_distressed_companies():
    metrics = _all_good_metrics()
    metrics["net_debt_to_ebitda"] = 6.0
    metrics["interest_coverage"] = 1.0
    metrics["current_ratio"] = 0.6
    snapshot = _make_snapshot(metrics)

    scores = compute_snapshot_scores(snapshot)

    assert scores.total <= 35.0


def test_caps_limit_score_for_value_trap():
    metrics = _all_good_metrics()
    metrics["revenue_growth"] = -0.10
    metrics["ebitda_growth"] = -0.10
    snapshot = _make_snapshot(metrics)

    scores = compute_snapshot_scores(snapshot)

    assert scores.total <= 45.0


def test_dangerous_debt_caps_score():
    metrics = _all_good_metrics()
    metrics["net_debt_to_ebitda"] = 5.0
    snapshot = _make_snapshot(metrics)

    scores = compute_snapshot_scores(snapshot)

    assert scores.total <= 45.0


def test_valuation_is_bridled_when_quality_is_poor():
    metrics = {
        "gross_margin": 0.10,
        "roic": -0.01,
        "roce": -0.01,
        "roa": -0.02,
        "ebit_margin": -0.03,
        "gross_profitability": 0.02,
        "ev_ebit": 5.0,
        "ev_fcf": 8.0,
        "ev_sales": 0.6,
        "pb_ratio": 0.5,
    }
    snapshot = _make_snapshot(metrics)

    scores = compute_snapshot_scores(snapshot)

    assert scores.value <= 50.0


def test_compensation_penalty_prevents_extreme_imbalance():
    metrics = {
        "gross_margin": 0.50,
        "roic": 0.20,
        "roce": 0.20,
        "asset_turnover": 1.5,
        "net_debt_to_ebitda": 6.0,
        "interest_coverage": 0.5,
        "current_ratio": 0.5,
        "debt_to_equity": 3.0,
    }
    snapshot = _make_snapshot(metrics)

    scores = compute_snapshot_scores(snapshot)

    assert scores.total < scores.quality * 0.35 + scores.risk * 0.15


def test_context_adjustment_reinvestment_phase():
    metrics = _all_good_metrics()
    metrics["revenue_growth"] = 0.25
    metrics["fcf_margin"] = -0.01
    metrics["gross_margin"] = 0.40
    snapshot = _make_snapshot(metrics)

    scores = compute_snapshot_scores(snapshot)

    assert scores.total > 0.0


def test_all_blocs_produce_score():
    metrics = _all_good_metrics()
    snapshot = _make_snapshot(metrics)
    service = ScoringService()
    scores = service.compute_snapshot_scores(snapshot)

    assert scores.quality > 0.0
    assert scores.value > 0.0
    assert scores.growth > 0.0
    assert scores.risk > 0.0
    assert scores.total > 0.0


def test_apply_scores_stores_profile_label():
    snapshot = _make_snapshot(_all_good_metrics())
    updated = apply_scores(snapshot)

    assert PROFILE_LABEL_KEY in updated.metrics
    assert isinstance(updated.metrics[PROFILE_LABEL_KEY], str)
    assert updated.metrics[PROFILE_LABEL_KEY] != ""


def test_profile_label_is_distressed_when_highly_leveraged():
    metrics = _all_good_metrics()
    metrics["net_debt_to_ebitda"] = 6.0
    metrics["interest_coverage"] = 1.0
    snapshot = _make_snapshot(metrics)
    updated = apply_scores(snapshot)

    assert updated.metrics[PROFILE_LABEL_KEY] == "distressed"


def test_profile_label_is_compounder_when_quality_and_growth():
    metrics = _all_good_metrics()
    metrics["roic"] = 0.20
    metrics["gross_margin"] = 0.45
    metrics["revenue_growth"] = 0.12
    # ensure not distressed or value_trap
    metrics["net_debt_to_ebitda"] = 0.5
    metrics["interest_coverage"] = 10.0
    snapshot = _make_snapshot(metrics)
    updated = apply_scores(snapshot)

    assert updated.metrics[PROFILE_LABEL_KEY] == "compounder"
