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
class ScoreExplanation:
    total_score: float | None
    quality: float | None
    value: float | None
    growth: float | None
    risk: float | None
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    summary: str


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
_MAX_EXPLANATION_POINTS: int = 3
_STRENGTH_THRESHOLD: float = 60.0
_WEAKNESS_THRESHOLD: float = 40.0


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
        scores = _resolve_snapshot_scores(snapshot, self)
        if scores is None:
            return ScoreExplanation(
                total_score=None,
                quality=None,
                value=None,
                growth=None,
                risk=None,
                strengths=(),
                weaknesses=(),
                summary="score unavailable: no snapshot data.",
            )
        strengths = _select_strength_points(scores)
        weaknesses = _select_weakness_points(scores, strengths)
        return ScoreExplanation(
            total_score=scores.total,
            quality=scores.quality,
            value=scores.value,
            growth=scores.growth,
            risk=scores.risk,
            strengths=tuple(_format_explanation_point(name, score) for name, score in strengths),
            weaknesses=tuple(_format_explanation_point(name, score) for name, score in weaknesses),
            summary=_build_score_summary(scores, strengths, weaknesses),
        )


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


def _resolve_snapshot_scores(snapshot: KpiSnapshot | None, service: ScoringService) -> SnapshotScores | None:
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


def _format_explanation_point(name: str, score: float) -> str:
    return f"{name} ({score:.1f}/100)"


def _build_score_summary(
    scores: SnapshotScores,
    strengths: list[tuple[str, float]],
    weaknesses: list[tuple[str, float]],
) -> str:
    strength_text = ", ".join(_format_explanation_point(name, score) for name, score in strengths)
    weakness_text = ", ".join(_format_explanation_point(name, score) for name, score in weaknesses)
    return (
        f"total {scores.total:.2f}/100 | quality {scores.quality:.2f}, value {scores.value:.2f}, "
        f"growth {scores.growth:.2f}, risk {scores.risk:.2f} | strengths: {strength_text} | "
        f"weaknesses: {weakness_text}"
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


def rank_companies_by_total_score(company_scores: list[CompanyTotalScore]) -> list[RankedCompanyTotalScore]:
    return _SERVICE.rank_companies_by_total_score(company_scores)


def describe_snapshot_score(snapshot: KpiSnapshot | None) -> ScoreExplanation:
    return _SERVICE.describe_snapshot_score(snapshot)
