from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from src.models.kpi_snapshot import KpiSnapshot
from src.services.ratio_service import CompanyRatios

_ZERO: float = 1e-9


@dataclass(frozen=True)
class MetricRule:
    weight: float
    good_threshold: float
    bad_threshold: float
    lower_is_better: bool


@dataclass(frozen=True)
class SnapshotScores:
    quality: float
    value: float
    growth: float
    risk: float
    total: float


# Category weights must sum to 1.0.
SNAPSHOT_SUB_SCORE_WEIGHTS: dict[str, float] = {
    "quality": 0.35,
    "value": 0.30,
    "growth": 0.20,
    "risk": 0.15,
}

# Per-metric weights for each sub-score category.
QUALITY_METRIC_RULES: dict[str, MetricRule] = {
    "roe": MetricRule(weight=0.35, good_threshold=0.15, bad_threshold=0.0, lower_is_better=False),
    "roic": MetricRule(weight=0.25, good_threshold=0.12, bad_threshold=0.0, lower_is_better=False),
    "operating_margin": MetricRule(weight=0.25, good_threshold=0.12, bad_threshold=0.0, lower_is_better=False),
    "gross_margin": MetricRule(weight=0.15, good_threshold=0.30, bad_threshold=0.10, lower_is_better=False),
}

VALUE_METRIC_RULES: dict[str, MetricRule] = {
    "pe_ratio": MetricRule(weight=0.30, good_threshold=10.0, bad_threshold=25.0, lower_is_better=True),
    "pb_ratio": MetricRule(weight=0.20, good_threshold=1.0, bad_threshold=3.0, lower_is_better=True),
    "ev_ebitda": MetricRule(weight=0.30, good_threshold=6.0, bad_threshold=15.0, lower_is_better=True),
    "fcf_yield": MetricRule(weight=0.20, good_threshold=0.08, bad_threshold=0.0, lower_is_better=False),
}

GROWTH_METRIC_RULES: dict[str, MetricRule] = {
    "revenue_growth": MetricRule(weight=0.60, good_threshold=0.10, bad_threshold=-0.05, lower_is_better=False),
    "ebitda_growth": MetricRule(weight=0.40, good_threshold=0.10, bad_threshold=-0.05, lower_is_better=False),
}

RISK_METRIC_RULES: dict[str, MetricRule] = {
    "net_debt_to_ebitda": MetricRule(weight=0.50, good_threshold=1.0, bad_threshold=4.0, lower_is_better=True),
    "current_ratio": MetricRule(weight=0.25, good_threshold=1.5, bad_threshold=0.8, lower_is_better=False),
    "interest_coverage": MetricRule(weight=0.25, good_threshold=6.0, bad_threshold=1.0, lower_is_better=False),
}

QUALITY_SCORE_KEY: str = "quality_score"
VALUE_SCORE_KEY: str = "value_score"
GROWTH_SCORE_KEY: str = "growth_score"
RISK_SCORE_KEY: str = "risk_score"
TOTAL_SCORE_KEY: str = "total_score"


@dataclass
class ScoringService:
    def compute_snapshot_scores(self, snapshot: KpiSnapshot) -> SnapshotScores:
        return self.compute_metrics_scores(snapshot.metrics)

    def compute_metrics_scores(self, metrics: Mapping[str, object]) -> SnapshotScores:
        quality_score = _compute_sub_score(metrics, QUALITY_METRIC_RULES)
        value_score = _compute_sub_score(metrics, VALUE_METRIC_RULES)
        growth_score = _compute_sub_score(metrics, GROWTH_METRIC_RULES)
        risk_score = _compute_sub_score(metrics, RISK_METRIC_RULES)
        total_score = _compute_total_score(
            quality_score=quality_score,
            value_score=value_score,
            growth_score=growth_score,
            risk_score=risk_score,
        )
        return SnapshotScores(
            quality=quality_score,
            value=value_score,
            growth=growth_score,
            risk=risk_score,
            total=total_score,
        )

    def apply_scores(self, snapshot: KpiSnapshot) -> KpiSnapshot:
        scores = self.compute_snapshot_scores(snapshot)
        updated_metrics = dict(snapshot.metrics)
        updated_metrics.update(
            {
                QUALITY_SCORE_KEY: scores.quality,
                VALUE_SCORE_KEY: scores.value,
                GROWTH_SCORE_KEY: scores.growth,
                RISK_SCORE_KEY: scores.risk,
                TOTAL_SCORE_KEY: scores.total,
            }
        )
        snapshot.metrics = updated_metrics
        return snapshot


def _compute_sub_score(metrics: Mapping[str, object], rules: Mapping[str, MetricRule]) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for metric_name, rule in rules.items():
        raw_value = metrics.get(metric_name)
        value = _as_finite_float(raw_value)
        if value is None:
            continue
        weighted_sum += (
            _score_metric(value, rule.good_threshold, rule.bad_threshold, rule.lower_is_better) * rule.weight
        )
        total_weight += rule.weight
    if total_weight < _ZERO:
        return 0.0
    return round((weighted_sum / total_weight) * 100.0, 2)


def _compute_total_score(
    *,
    quality_score: float,
    value_score: float,
    growth_score: float,
    risk_score: float,
) -> float:
    return round(
        quality_score * SNAPSHOT_SUB_SCORE_WEIGHTS["quality"]
        + value_score * SNAPSHOT_SUB_SCORE_WEIGHTS["value"]
        + growth_score * SNAPSHOT_SUB_SCORE_WEIGHTS["growth"]
        + risk_score * SNAPSHOT_SUB_SCORE_WEIGHTS["risk"],
        2,
    )


def _as_finite_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


# Weights must sum to 1.0
_LEGACY_WEIGHTS: dict[str, float] = {
    "pe_ratio": 0.20,
    "ev_ebitda": 0.20,
    "pb_ratio": 0.10,
    "price_to_fcf": 0.10,
    "roe": 0.15,
    "net_margin": 0.10,
    "ebit_margin": 0.05,
    "net_debt_to_ebitda": 0.10,
}

# (good_threshold, bad_threshold, lower_is_better)
_LEGACY_THRESHOLDS: dict[str, tuple[float, float, bool]] = {
    "pe_ratio": (10.0, 25.0, True),
    "ev_ebitda": (6.0, 15.0, True),
    "pb_ratio": (1.0, 3.0, True),
    "price_to_fcf": (10.0, 25.0, True),
    "roe": (0.15, 0.0, False),
    "net_margin": (0.10, 0.0, False),
    "ebit_margin": (0.10, 0.0, False),
    "net_debt_to_ebitda": (1.0, 4.0, True),
}


def _score_metric(value: float, good: float, bad: float, lower_is_better: bool) -> float:
    if lower_is_better:
        if value <= good:
            return 1.0
        if value >= bad:
            return 0.0
        return 1.0 - (value - good) / (bad - good)
    else:
        if value >= good:
            return 1.0
        if value <= bad:
            return 0.0
        return (value - bad) / (good - bad)


def compute_score(ratios: CompanyRatios) -> float:
    total_weight = 0.0
    weighted_score = 0.0

    for metric, weight in _LEGACY_WEIGHTS.items():
        value: float | None = getattr(ratios, metric)
        if value is None:
            continue
        good, bad, lower_is_better = _LEGACY_THRESHOLDS[metric]
        score = _score_metric(value, good, bad, lower_is_better)
        weighted_score += score * weight
        total_weight += weight

    if total_weight < 1e-9:
        return 0.0
    return round((weighted_score / total_weight) * 100, 2)


_SERVICE = ScoringService()


def compute_snapshot_scores(snapshot: KpiSnapshot) -> SnapshotScores:
    return _SERVICE.compute_snapshot_scores(snapshot)


def apply_scores(snapshot: KpiSnapshot) -> KpiSnapshot:
    return _SERVICE.apply_scores(snapshot)
