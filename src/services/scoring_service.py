from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from src.models.kpi_snapshot import KpiSnapshot
from src.services.ratio_service import CompanyRatios
from src.services.scoring_config import (
    DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS,
    SnapshotSubScoreWeights,
    validate_snapshot_sub_score_weights,
)

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


@dataclass(frozen=True)
class CompanyTotalScore:
    company_id: int
    ticker: str | None
    total_score: float | None
    sector: str | None = None


@dataclass(frozen=True)
class RankedCompanyTotalScore:
    company_id: int
    ticker: str | None
    total_score: float | None
    rank: int | None
    sector_rank: int | None
    sector: str | None = None


@dataclass(frozen=True)
class ScoreWeightEntry:
    category: str
    weight: float


@dataclass(frozen=True)
class ScoreCategoryContribution:
    category: str
    sub_score: float
    weight: float
    weighted_points: float


@dataclass(frozen=True)
class ScoreMetricDriver:
    category: str
    metric: str
    raw_value: float
    metric_score: float
    weighted_points: float
    impact_points: float


@dataclass(frozen=True)
class ScoreExplanation:
    total_score: float | None
    quality: float | None
    value: float | None
    growth: float | None
    risk: float | None
    weights: tuple[ScoreWeightEntry, ...]
    category_contributions: tuple[ScoreCategoryContribution, ...]
    positive_drivers: tuple[ScoreMetricDriver, ...]
    negative_drivers: tuple[ScoreMetricDriver, ...]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class _MetricContribution:
    category: str
    metric: str
    raw_value: float
    metric_score: float
    weighted_points: float
    impact_points: float


@dataclass(frozen=True)
class _SubScoreComputation:
    score: float
    metric_contributions: tuple[_MetricContribution, ...]


@dataclass(frozen=True)
class _ScoreComputation:
    scores: SnapshotScores
    metric_contributions: tuple[_MetricContribution, ...]


_CATEGORY_ORDER: tuple[str, ...] = ("quality", "value", "growth", "risk")

# Backward-compatible constant; source of truth is now in scoring_config.
SNAPSHOT_SUB_SCORE_WEIGHTS: dict[str, float] = DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS.as_dict()

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
SCORE_WEIGHT_QUALITY_KEY: str = "score_weight_quality"
SCORE_WEIGHT_VALUE_KEY: str = "score_weight_value"
SCORE_WEIGHT_GROWTH_KEY: str = "score_weight_growth"
SCORE_WEIGHT_RISK_KEY: str = "score_weight_risk"
_MAX_EXPLANATION_POINTS: int = 3
_STRENGTH_THRESHOLD: float = 60.0
_WEAKNESS_THRESHOLD: float = 40.0


@dataclass
class ScoringService:
    sub_score_weights: SnapshotSubScoreWeights = field(default_factory=lambda: DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS)

    def __post_init__(self) -> None:
        validate_snapshot_sub_score_weights(self.sub_score_weights)

    def compute_snapshot_scores(self, snapshot: KpiSnapshot) -> SnapshotScores:
        return self.compute_metrics_scores(snapshot.metrics)

    def compute_metrics_scores(self, metrics: Mapping[str, object]) -> SnapshotScores:
        return _compute_score_components(metrics, self.sub_score_weights.as_dict()).scores

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
                SCORE_WEIGHT_QUALITY_KEY: self.sub_score_weights.quality_weight,
                SCORE_WEIGHT_VALUE_KEY: self.sub_score_weights.value_weight,
                SCORE_WEIGHT_GROWTH_KEY: self.sub_score_weights.growth_weight,
                SCORE_WEIGHT_RISK_KEY: self.sub_score_weights.risk_weight,
            }
        )
        snapshot.metrics = updated_metrics
        return snapshot

    def rank_companies_by_total_score(self, company_scores: list[CompanyTotalScore]) -> list[RankedCompanyTotalScore]:
        scored = [item for item in company_scores if _as_finite_float(item.total_score) is not None]
        unscored = [item for item in company_scores if _as_finite_float(item.total_score) is None]

        ranked_scored = _rank_scored_companies(scored)
        ranked_unscored = [
            RankedCompanyTotalScore(
                company_id=item.company_id,
                ticker=item.ticker,
                total_score=None,
                rank=None,
                sector_rank=None,
                sector=_normalize_sector(item.sector),
            )
            for item in sorted(
                unscored, key=lambda x: (x.company_id, x.ticker or "", _normalize_sector(x.sector) or "")
            )
        ]
        return ranked_scored + ranked_unscored

    def get_snapshot_total_score(self, snapshot: KpiSnapshot | None) -> float | None:
        if snapshot is None:
            return None
        return _as_finite_float(snapshot.metrics.get(TOTAL_SCORE_KEY))

    def describe_snapshot_score(self, snapshot: KpiSnapshot | None) -> ScoreExplanation:
        if snapshot is None:
            return ScoreExplanation(
                total_score=None,
                quality=None,
                value=None,
                growth=None,
                risk=None,
                weights=(),
                category_contributions=(),
                positive_drivers=(),
                negative_drivers=(),
                strengths=(),
                weaknesses=(),
                summary="score unavailable: no snapshot data.",
            )

        weights = _resolve_snapshot_weights(snapshot.metrics, self.sub_score_weights)
        weights_map = weights.as_dict()
        scores = _resolve_snapshot_scores(snapshot, self, weights_map)
        if scores is None:
            return ScoreExplanation(
                total_score=None,
                quality=None,
                value=None,
                growth=None,
                risk=None,
                weights=(),
                category_contributions=(),
                positive_drivers=(),
                negative_drivers=(),
                strengths=(),
                weaknesses=(),
                summary="score unavailable: no snapshot data.",
            )

        computation = _compute_score_components(snapshot.metrics, weights_map)
        category_contributions = _build_category_contributions(scores, weights_map)
        positive_drivers = _select_positive_drivers(computation.metric_contributions)
        negative_drivers = _select_negative_drivers(computation.metric_contributions)
        strengths = _select_strength_points(scores)
        weaknesses = _select_weakness_points(scores, strengths)

        return ScoreExplanation(
            total_score=scores.total,
            quality=scores.quality,
            value=scores.value,
            growth=scores.growth,
            risk=scores.risk,
            weights=tuple(
                ScoreWeightEntry(category=category, weight=weights_map[category]) for category in _CATEGORY_ORDER
            ),
            category_contributions=category_contributions,
            positive_drivers=positive_drivers,
            negative_drivers=negative_drivers,
            strengths=tuple(_format_explanation_point(name, score) for name, score in strengths),
            weaknesses=tuple(_format_explanation_point(name, score) for name, score in weaknesses),
            summary=_build_score_summary(
                scores,
                category_contributions,
                positive_drivers,
                negative_drivers,
                strengths,
                weaknesses,
            ),
        )


def _compute_score_components(
    metrics: Mapping[str, object],
    weights: Mapping[str, float],
) -> _ScoreComputation:
    quality = _compute_sub_score(metrics, QUALITY_METRIC_RULES, category="quality", category_weight=weights["quality"])
    value = _compute_sub_score(metrics, VALUE_METRIC_RULES, category="value", category_weight=weights["value"])
    growth = _compute_sub_score(metrics, GROWTH_METRIC_RULES, category="growth", category_weight=weights["growth"])
    risk = _compute_sub_score(metrics, RISK_METRIC_RULES, category="risk", category_weight=weights["risk"])

    scores = SnapshotScores(
        quality=quality.score,
        value=value.score,
        growth=growth.score,
        risk=risk.score,
        total=_compute_total_score(
            quality_score=quality.score,
            value_score=value.score,
            growth_score=growth.score,
            risk_score=risk.score,
            weights=weights,
        ),
    )
    metric_contributions = (
        quality.metric_contributions
        + value.metric_contributions
        + growth.metric_contributions
        + risk.metric_contributions
    )
    return _ScoreComputation(scores=scores, metric_contributions=metric_contributions)


def _compute_sub_score(
    metrics: Mapping[str, object],
    rules: Mapping[str, MetricRule],
    *,
    category: str,
    category_weight: float,
) -> _SubScoreComputation:
    available: list[tuple[str, MetricRule, float]] = []
    for metric_name, rule in rules.items():
        raw_value = metrics.get(metric_name)
        value = _as_finite_float(raw_value)
        if value is None:
            continue
        available.append((metric_name, rule, value))

    total_weight = sum(rule.weight for _, rule, _ in available)
    if total_weight < _ZERO:
        return _SubScoreComputation(score=0.0, metric_contributions=())

    weighted_sum = 0.0
    metric_contributions: list[_MetricContribution] = []
    for metric_name, rule, value in available:
        metric_score = _score_metric(value, rule.good_threshold, rule.bad_threshold, rule.lower_is_better) * 100.0
        normalized_metric_weight = rule.weight / total_weight
        weighted_points = metric_score * category_weight * normalized_metric_weight
        neutral_points = 50.0 * category_weight * normalized_metric_weight
        weighted_sum += (metric_score / 100.0) * rule.weight
        metric_contributions.append(
            _MetricContribution(
                category=category,
                metric=metric_name,
                raw_value=value,
                metric_score=round(metric_score, 2),
                weighted_points=round(weighted_points, 4),
                impact_points=round(weighted_points - neutral_points, 4),
            )
        )

    sub_score = round((weighted_sum / total_weight) * 100.0, 2)
    return _SubScoreComputation(score=sub_score, metric_contributions=tuple(metric_contributions))


def _build_category_contributions(
    scores: SnapshotScores,
    weights: Mapping[str, float],
) -> tuple[ScoreCategoryContribution, ...]:
    score_by_category = {
        "quality": scores.quality,
        "value": scores.value,
        "growth": scores.growth,
        "risk": scores.risk,
    }
    return tuple(
        ScoreCategoryContribution(
            category=category,
            sub_score=score_by_category[category],
            weight=weights[category],
            weighted_points=round(score_by_category[category] * weights[category], 2),
        )
        for category in _CATEGORY_ORDER
    )


def _compute_total_score(
    *,
    quality_score: float,
    value_score: float,
    growth_score: float,
    risk_score: float,
    weights: Mapping[str, float],
) -> float:
    return round(
        quality_score * weights["quality"]
        + value_score * weights["value"]
        + growth_score * weights["growth"]
        + risk_score * weights["risk"],
        2,
    )


def _resolve_snapshot_weights(
    metrics: Mapping[str, object],
    default_weights: SnapshotSubScoreWeights,
) -> SnapshotSubScoreWeights:
    quality_weight = _as_finite_float(metrics.get(SCORE_WEIGHT_QUALITY_KEY))
    value_weight = _as_finite_float(metrics.get(SCORE_WEIGHT_VALUE_KEY))
    growth_weight = _as_finite_float(metrics.get(SCORE_WEIGHT_GROWTH_KEY))
    risk_weight = _as_finite_float(metrics.get(SCORE_WEIGHT_RISK_KEY))

    if None in (quality_weight, value_weight, growth_weight, risk_weight):
        return default_weights

    candidate = SnapshotSubScoreWeights(
        quality_weight=float(quality_weight),
        value_weight=float(value_weight),
        growth_weight=float(growth_weight),
        risk_weight=float(risk_weight),
    )
    try:
        validate_snapshot_sub_score_weights(candidate)
    except ValueError:
        return default_weights
    return candidate


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


def _rank_scored_companies(scored: list[CompanyTotalScore]) -> list[RankedCompanyTotalScore]:
    ranked: list[RankedCompanyTotalScore] = []
    ordered = sorted(scored, key=lambda x: (-float(x.total_score), x.company_id, x.ticker or ""))
    sector_ranks = _compute_sector_ranks(scored)
    for index, item in enumerate(ordered, start=1):
        ranked.append(
            RankedCompanyTotalScore(
                company_id=item.company_id,
                ticker=item.ticker,
                total_score=float(item.total_score),
                rank=index,
                sector_rank=sector_ranks.get(item.company_id),
                sector=_normalize_sector(item.sector),
            )
        )
    return ranked


def _compute_sector_ranks(scored: list[CompanyTotalScore]) -> dict[int, int]:
    by_sector: dict[str, list[CompanyTotalScore]] = {}
    for item in scored:
        sector = _normalize_sector(item.sector)
        if sector is None:
            continue
        bucket = by_sector.setdefault(sector, [])
        bucket.append(item)

    ranks_by_company_id: dict[int, int] = {}
    for items in by_sector.values():
        ordered = sorted(items, key=lambda x: (-float(x.total_score), x.company_id, x.ticker or ""))
        for index, item in enumerate(ordered, start=1):
            ranks_by_company_id[item.company_id] = index
    return ranks_by_company_id


def _normalize_sector(value: str | None) -> str | None:
    if value is None:
        return None
    sector = value.strip()
    if not sector:
        return None
    return sector


def _resolve_snapshot_scores(
    snapshot: KpiSnapshot | None,
    service: ScoringService,
    weights: Mapping[str, float],
) -> SnapshotScores | None:
    if snapshot is None:
        return None
    metrics = snapshot.metrics
    quality_score = _as_finite_float(metrics.get(QUALITY_SCORE_KEY))
    value_score = _as_finite_float(metrics.get(VALUE_SCORE_KEY))
    growth_score = _as_finite_float(metrics.get(GROWTH_SCORE_KEY))
    risk_score = _as_finite_float(metrics.get(RISK_SCORE_KEY))
    total_score = _as_finite_float(metrics.get(TOTAL_SCORE_KEY))

    if None in (quality_score, value_score, growth_score, risk_score):
        computed = service.compute_metrics_scores(metrics)
        quality_score = computed.quality if quality_score is None else quality_score
        value_score = computed.value if value_score is None else value_score
        growth_score = computed.growth if growth_score is None else growth_score
        risk_score = computed.risk if risk_score is None else risk_score

    if total_score is None:
        total_score = _compute_total_score(
            quality_score=quality_score or 0.0,
            value_score=value_score or 0.0,
            growth_score=growth_score or 0.0,
            risk_score=risk_score or 0.0,
            weights=weights,
        )
    return SnapshotScores(
        quality=float(quality_score or 0.0),
        value=float(value_score or 0.0),
        growth=float(growth_score or 0.0),
        risk=float(risk_score or 0.0),
        total=float(total_score),
    )


def _score_dimensions(scores: SnapshotScores) -> list[tuple[str, float]]:
    return [
        ("quality", scores.quality),
        ("value", scores.value),
        ("growth", scores.growth),
        ("risk", scores.risk),
    ]


def _select_strength_points(scores: SnapshotScores) -> list[tuple[str, float]]:
    ordered_desc = sorted(_score_dimensions(scores), key=lambda x: (-x[1], x[0]))
    selected = [item for item in ordered_desc if item[1] >= _STRENGTH_THRESHOLD][:_MAX_EXPLANATION_POINTS]
    if selected:
        return selected
    return ordered_desc[:1]


def _select_weakness_points(
    scores: SnapshotScores,
    strengths: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    ordered_asc = sorted(_score_dimensions(scores), key=lambda x: (x[1], x[0]))
    selected_names = {name for name, _ in strengths}
    selected = [item for item in ordered_asc if item[1] <= _WEAKNESS_THRESHOLD and item[0] not in selected_names][
        :_MAX_EXPLANATION_POINTS
    ]
    if selected:
        return selected
    fallback = [item for item in ordered_asc if item[0] not in selected_names]
    if fallback:
        return fallback[:1]
    return ordered_asc[:1]


def _select_positive_drivers(contributions: tuple[_MetricContribution, ...]) -> tuple[ScoreMetricDriver, ...]:
    positives = [item for item in contributions if item.impact_points > 0.0]
    positives.sort(key=lambda x: (-x.impact_points, -x.weighted_points, x.category, x.metric))
    return tuple(_to_driver(item) for item in positives[:_MAX_EXPLANATION_POINTS])


def _select_negative_drivers(contributions: tuple[_MetricContribution, ...]) -> tuple[ScoreMetricDriver, ...]:
    negatives = [item for item in contributions if item.impact_points < 0.0]
    negatives.sort(key=lambda x: (x.impact_points, -x.weighted_points, x.category, x.metric))
    return tuple(_to_driver(item) for item in negatives[:_MAX_EXPLANATION_POINTS])


def _to_driver(item: _MetricContribution) -> ScoreMetricDriver:
    return ScoreMetricDriver(
        category=item.category,
        metric=item.metric,
        raw_value=item.raw_value,
        metric_score=item.metric_score,
        weighted_points=round(item.weighted_points, 2),
        impact_points=round(item.impact_points, 2),
    )


def _format_explanation_point(name: str, score: float) -> str:
    return f"{name} ({score:.1f}/100)"


def _format_driver(driver: ScoreMetricDriver) -> str:
    return (
        f"{driver.category}.{driver.metric} "
        f"(impact {driver.impact_points:+.2f} pts, metric {driver.metric_score:.1f}/100)"
    )


def _build_score_summary(
    scores: SnapshotScores,
    category_contributions: tuple[ScoreCategoryContribution, ...],
    positive_drivers: tuple[ScoreMetricDriver, ...],
    negative_drivers: tuple[ScoreMetricDriver, ...],
    strengths: list[tuple[str, float]],
    weaknesses: list[tuple[str, float]],
) -> str:
    construction = " + ".join(
        f"{item.category} {item.sub_score:.2f}*{item.weight:.2f}={item.weighted_points:.2f}"
        for item in category_contributions
    )
    strength_text = ", ".join(_format_explanation_point(name, score) for name, score in strengths)
    weakness_text = ", ".join(_format_explanation_point(name, score) for name, score in weaknesses)
    positive_text = ", ".join(_format_driver(driver) for driver in positive_drivers) if positive_drivers else "none"
    negative_text = ", ".join(_format_driver(driver) for driver in negative_drivers) if negative_drivers else "none"
    return (
        f"total {scores.total:.2f}/100 | construction: {construction} | "
        f"positive drivers: {positive_text} | negative drivers: {negative_text} | "
        f"strengths: {strength_text} | weaknesses: {weakness_text}"
    )


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


def rank_companies_by_total_score(company_scores: list[CompanyTotalScore]) -> list[RankedCompanyTotalScore]:
    return _SERVICE.rank_companies_by_total_score(company_scores)


def describe_snapshot_score(snapshot: KpiSnapshot | None) -> ScoreExplanation:
    return _SERVICE.describe_snapshot_score(snapshot)
