from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from src.models.kpi_snapshot import KpiSnapshot
from src.services.ratio_service import CompanyRatios
from src.services.scoring_config import (
    BLOC_DEFS,
    BLOC_TO_LEGACY,
    CAP_DANGEROUS_DEBT,
    CAP_DISTRESSED,
    CAP_UNCONFIRMED_TURNAROUND,
    CAP_VALUE_TRAP,
    COMPENSATION_FACTOR,
    COMPENSATION_FLOOR,
    DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS,
    LEGACY_GROWTH_BLOCS,
    LEGACY_QUALITY_BLOCS,
    LEGACY_RISK_BLOCS,
    LEGACY_VALUE_BLOCS,
    VALUATION_BRIDLE_CAP,
    VALUATION_BRIDLE_THRESHOLD,
    BlocDef,
    MetricDef,
    SnapshotSubScoreWeights,
    validate_snapshot_sub_score_weights,
)

_ZERO: float = 1e-9

QUALITY_SCORE_KEY: str = "quality_score"
VALUE_SCORE_KEY: str = "value_score"
GROWTH_SCORE_KEY: str = "growth_score"
RISK_SCORE_KEY: str = "risk_score"
TOTAL_SCORE_KEY: str = "total_score"
SCORE_WEIGHT_QUALITY_KEY: str = "score_weight_quality"
SCORE_WEIGHT_VALUE_KEY: str = "score_weight_value"
SCORE_WEIGHT_GROWTH_KEY: str = "score_weight_growth"
SCORE_WEIGHT_RISK_KEY: str = "score_weight_risk"
PROFILE_LABEL_KEY: str = "profile_label"

_PROFILE_DISTRESSED: str = "distressed"
_PROFILE_VALUE_TRAP: str = "value_trap"
_PROFILE_TURNAROUND: str = "turnaround"
_PROFILE_COMPOUNDER: str = "compounder"
_PROFILE_REINVESTMENT: str = "reinvestment_phase"
_PROFILE_CYCLICAL: str = "cyclical"
_PROFILE_LOW_VISIBILITY: str = "low_visibility"
_PROFILE_STANDARD: str = "standard"

_CFQ_REINVESTMENT_FLOOR: float = 35.0
_CFQ_REINVESTMENT_MAX_LIFT: float = 20.0

_MAX_EXPLANATION_POINTS: int = 3
_STRENGTH_THRESHOLD: float = 60.0
_WEAKNESS_THRESHOLD: float = 40.0

_CATEGORY_ORDER: tuple[str, ...] = ("quality", "value", "growth", "risk")

SNAPSHOT_SUB_SCORE_WEIGHTS: dict[str, float] = DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS.as_dict()


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Internal dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _MetricContribution:
    category: str
    metric: str
    raw_value: float
    metric_score: float
    weighted_points: float
    impact_points: float


@dataclass(frozen=True)
class _BlocResult:
    name: str
    score: float
    available_metrics: int
    total_metrics: int
    contributions: tuple[_MetricContribution, ...]


@dataclass(frozen=True)
class _AdvancedResult:
    scores: SnapshotScores
    all_contributions: tuple[_MetricContribution, ...]
    profile_label: str = _PROFILE_STANDARD


# ---------------------------------------------------------------------------
# ScoringService
# ---------------------------------------------------------------------------


@dataclass
class ScoringService:
    sub_score_weights: SnapshotSubScoreWeights = field(
        default_factory=lambda: DEFAULT_SNAPSHOT_SUB_SCORE_WEIGHTS,
    )

    def __post_init__(self) -> None:
        validate_snapshot_sub_score_weights(self.sub_score_weights)

    def compute_snapshot_scores(self, snapshot: KpiSnapshot) -> SnapshotScores:
        return self.compute_metrics_scores(snapshot.metrics)

    def compute_metrics_scores(self, metrics: Mapping[str, object]) -> SnapshotScores:
        return _compute_advanced(metrics, self.sub_score_weights.as_dict()).scores

    def apply_scores(self, snapshot: KpiSnapshot) -> KpiSnapshot:
        result = _compute_advanced(snapshot.metrics, self.sub_score_weights.as_dict())
        scores = result.scores
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
                PROFILE_LABEL_KEY: result.profile_label,
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
                unscored,
                key=lambda x: (x.company_id, x.ticker or "", _normalize_sector(x.sector) or ""),
            )
        ]
        return ranked_scored + ranked_unscored

    def get_snapshot_total_score(self, snapshot: KpiSnapshot | None) -> float | None:
        if snapshot is None:
            return None
        return _as_finite_float(snapshot.metrics.get(TOTAL_SCORE_KEY))

    def describe_snapshot_score(self, snapshot: KpiSnapshot | None) -> ScoreExplanation:
        if snapshot is None:
            return _empty_explanation()

        weights = _resolve_snapshot_weights(snapshot.metrics, self.sub_score_weights)
        weights_map = weights.as_dict()
        result = _compute_advanced(snapshot.metrics, weights_map)
        scores = result.scores

        scores = _overlay_stored_scores(snapshot.metrics, scores)

        category_contributions = _build_category_contributions(scores, weights_map)
        positive_drivers = _select_positive_drivers(result.all_contributions)
        negative_drivers = _select_negative_drivers(result.all_contributions)
        strengths = _select_strength_points(scores)
        weaknesses = _select_weakness_points(scores, strengths)

        return ScoreExplanation(
            total_score=scores.total,
            quality=scores.quality,
            value=scores.value,
            growth=scores.growth,
            risk=scores.risk,
            weights=tuple(ScoreWeightEntry(category=cat, weight=weights_map[cat]) for cat in _CATEGORY_ORDER),
            category_contributions=category_contributions,
            positive_drivers=positive_drivers,
            negative_drivers=negative_drivers,
            strengths=tuple(_format_explanation_point(n, s) for n, s in strengths),
            weaknesses=tuple(_format_explanation_point(n, s) for n, s in weaknesses),
            summary=_build_score_summary(
                scores, category_contributions, positive_drivers, negative_drivers, strengths, weaknesses
            ),
        )


# ---------------------------------------------------------------------------
# 8-bloc scoring engine
# ---------------------------------------------------------------------------


def _compute_advanced(
    metrics: Mapping[str, object],
    weights: Mapping[str, float],
) -> _AdvancedResult:
    bloc_results = _compute_all_blocs(metrics, weights)
    bloc_results = _bridle_valuation(bloc_results)
    bloc_results = _apply_reinvestment_cfq_relief(metrics, bloc_results)

    quality = _legacy_category_score(bloc_results, LEGACY_QUALITY_BLOCS)
    value = _legacy_category_score(bloc_results, LEGACY_VALUE_BLOCS)
    growth = _legacy_category_score(bloc_results, LEGACY_GROWTH_BLOCS)
    risk = _legacy_category_score(bloc_results, LEGACY_RISK_BLOCS)

    raw_total = (
        quality * weights["quality"] + value * weights["value"] + growth * weights["growth"] + risk * weights["risk"]
    )

    penalty = _compensation_penalty(bloc_results)
    raw_total = max(0.0, raw_total - penalty)

    ctx_adj = _context_adjustment(metrics, bloc_results)
    cap = _detect_cap(metrics, bloc_results)

    total = min(cap, raw_total + ctx_adj)
    total = max(0.0, min(100.0, round(total, 2)))

    all_contributions = tuple(c for br in bloc_results.values() for c in br.contributions)
    profile_label = _detect_profile(metrics, bloc_results)

    return _AdvancedResult(
        scores=SnapshotScores(
            quality=round(quality, 2),
            value=round(value, 2),
            growth=round(growth, 2),
            risk=round(risk, 2),
            total=total,
        ),
        all_contributions=all_contributions,
        profile_label=profile_label,
    )


def _compute_all_blocs(
    metrics: Mapping[str, object],
    weights: Mapping[str, float],
) -> dict[str, _BlocResult]:
    results: dict[str, _BlocResult] = {}
    for bloc_def in BLOC_DEFS:
        results[bloc_def.name] = _compute_bloc(metrics, bloc_def, weights)
    return results


def _compute_bloc(
    metrics: Mapping[str, object],
    bloc_def: BlocDef,
    weights: Mapping[str, float],
) -> _BlocResult:
    available: list[tuple[str, MetricDef, float]] = []
    for metric_name, metric_def in bloc_def.metrics:
        value = _as_finite_float(metrics.get(metric_name))
        if value is not None:
            available.append((metric_name, metric_def, value))

    total_metrics = len(bloc_def.metrics)
    if not available:
        return _BlocResult(
            name=bloc_def.name,
            score=0.0,
            available_metrics=0,
            total_metrics=total_metrics,
            contributions=(),
        )

    total_weight = sum(md.weight for _, md, _ in available)
    legacy_cat = BLOC_TO_LEGACY.get(bloc_def.name, bloc_def.name)
    cat_weight = weights.get(legacy_cat, 0.0)
    sum_bloc_w_in_cat = _sum_bloc_weights_for_category(legacy_cat)

    weighted_sum = 0.0
    contributions: list[_MetricContribution] = []
    for metric_name, metric_def, value in available:
        score_01 = _score_metric(value, metric_def.good, metric_def.bad, metric_def.lower_is_better)
        metric_score = score_01 * 100.0
        norm_w = metric_def.weight / total_weight

        eff_weight = norm_w * (bloc_def.weight / max(sum_bloc_w_in_cat, _ZERO)) * cat_weight
        w_pts = metric_score * eff_weight
        n_pts = 50.0 * eff_weight

        weighted_sum += score_01 * metric_def.weight
        contributions.append(
            _MetricContribution(
                category=bloc_def.name,
                metric=metric_name,
                raw_value=value,
                metric_score=round(metric_score, 2),
                weighted_points=round(w_pts, 4),
                impact_points=round(w_pts - n_pts, 4),
            )
        )

    bloc_score = round((weighted_sum / total_weight) * 100.0, 2)
    return _BlocResult(
        name=bloc_def.name,
        score=bloc_score,
        available_metrics=len(available),
        total_metrics=total_metrics,
        contributions=tuple(contributions),
    )


def _sum_bloc_weights_for_category(legacy_cat: str) -> float:
    return sum(b.weight for b in BLOC_DEFS if BLOC_TO_LEGACY.get(b.name) == legacy_cat)


def _legacy_category_score(
    bloc_results: dict[str, _BlocResult],
    bloc_names: tuple[str, ...],
) -> float:
    total_w = 0.0
    weighted_sum = 0.0
    for name in bloc_names:
        br = bloc_results.get(name)
        if br is None or br.available_metrics == 0:
            continue
        bloc_def = _bloc_def_by_name(name)
        if bloc_def is None:
            continue
        weighted_sum += br.score * bloc_def.weight
        total_w += bloc_def.weight
    if total_w < _ZERO:
        return 0.0
    return weighted_sum / total_w


def _bloc_def_by_name(name: str) -> BlocDef | None:
    for b in BLOC_DEFS:
        if b.name == name:
            return b
    return None


# ---------------------------------------------------------------------------
# Valuation bridling
# ---------------------------------------------------------------------------


def _bridle_valuation(bloc_results: dict[str, _BlocResult]) -> dict[str, _BlocResult]:
    val = bloc_results.get("valuation")
    if val is None or val.available_metrics == 0:
        return bloc_results

    quality_scores = [
        bloc_results[b].score
        for b in LEGACY_QUALITY_BLOCS
        if b in bloc_results and bloc_results[b].available_metrics > 0
    ]
    risk_scores = [
        bloc_results[b].score for b in LEGACY_RISK_BLOCS if b in bloc_results and bloc_results[b].available_metrics > 0
    ]

    quality_avg = sum(quality_scores) / len(quality_scores) if quality_scores else None
    risk_avg = sum(risk_scores) / len(risk_scores) if risk_scores else None

    bridle_cap = 100.0
    if quality_avg is not None and quality_avg < VALUATION_BRIDLE_THRESHOLD:
        bridle_cap = min(bridle_cap, VALUATION_BRIDLE_CAP)
    if risk_avg is not None and risk_avg < VALUATION_BRIDLE_THRESHOLD:
        bridle_cap = min(bridle_cap, VALUATION_BRIDLE_CAP)

    if val.score > bridle_cap:
        bloc_results = dict(bloc_results)
        bloc_results["valuation"] = _BlocResult(
            name=val.name,
            score=bridle_cap,
            available_metrics=val.available_metrics,
            total_metrics=val.total_metrics,
            contributions=val.contributions,
        )

    return bloc_results


# ---------------------------------------------------------------------------
# Anti-compensation penalty
# ---------------------------------------------------------------------------


def _compensation_penalty(bloc_results: dict[str, _BlocResult]) -> float:
    scores = [br.score for br in bloc_results.values() if br.available_metrics > 0]
    if not scores:
        return 0.0
    min_score = min(scores)
    if min_score < COMPENSATION_FLOOR:
        return (COMPENSATION_FLOOR - min_score) * COMPENSATION_FACTOR
    return 0.0


# ---------------------------------------------------------------------------
# Context adjustment
# ---------------------------------------------------------------------------


def _context_adjustment(
    metrics: Mapping[str, object],
    bloc_results: dict[str, _BlocResult],
) -> float:
    if _is_distressed(metrics):
        return -11.0
    if _is_value_trap(metrics, bloc_results):
        return -10.0
    turnaround = _detect_turnaround(metrics)
    if turnaround is not None:
        return turnaround
    if _is_cyclical(metrics):
        return 5.0
    if _is_reinvestment_phase(metrics):
        return 6.0
    return 0.0


def _is_distressed(metrics: Mapping[str, object]) -> bool:
    debt = _get(metrics, "net_debt_to_ebitda")
    coverage = _get(metrics, "interest_coverage")
    curr = _get(metrics, "current_ratio")
    if debt is not None and debt > 5.0 and coverage is not None and coverage < 1.5:
        return True
    if coverage is not None and coverage < 1.0 and curr is not None and curr < 0.7:
        return True
    return False


def _is_value_trap(
    metrics: Mapping[str, object],
    bloc_results: dict[str, _BlocResult],
) -> bool:
    rev_g = _get(metrics, "revenue_growth")
    ebitda_g = _get(metrics, "ebitda_growth")
    val = bloc_results.get("valuation")
    if (
        rev_g is not None
        and rev_g < -0.05
        and ebitda_g is not None
        and ebitda_g < -0.05
        and val is not None
        and val.available_metrics > 0
        and val.score > 60.0
    ):
        return True
    return False


def _detect_turnaround(metrics: Mapping[str, object]) -> float | None:
    ebit_margin = _get(metrics, "ebit_margin")
    rev_g = _get(metrics, "revenue_growth")
    if ebit_margin is None or rev_g is None:
        return None
    if ebit_margin < 0.0 and rev_g > 0.10:
        return 2.0
    if ebit_margin < 0.0 and rev_g > 0.0:
        return -2.0
    return None


def _is_cyclical(metrics: Mapping[str, object]) -> bool:
    beta = _get(metrics, "beta")
    return beta is not None and beta > 1.5


def _is_reinvestment_phase(metrics: Mapping[str, object]) -> bool:
    rev_g = _get(metrics, "revenue_growth")
    fcf_m = _get(metrics, "fcf_margin")
    gm = _get(metrics, "gross_margin")
    return rev_g is not None and rev_g > 0.15 and fcf_m is not None and fcf_m < 0.02 and gm is not None and gm > 0.20


def _is_compounder(metrics: Mapping[str, object]) -> bool:
    roic = _get(metrics, "roic")
    gm = _get(metrics, "gross_margin")
    rev_g = _get(metrics, "revenue_growth")
    return roic is not None and roic >= 0.15 and gm is not None and gm >= 0.30 and rev_g is not None and rev_g > 0.0


def _is_low_visibility(metrics: Mapping[str, object]) -> bool:
    keys = ("roic", "revenue_growth", "ebit_margin", "net_debt_to_ebitda")
    available = sum(1 for k in keys if _get(metrics, k) is not None)
    return available < 2


def _detect_profile(
    metrics: Mapping[str, object],
    bloc_results: dict[str, _BlocResult],
) -> str:
    if _is_distressed(metrics):
        return _PROFILE_DISTRESSED
    if _is_value_trap(metrics, bloc_results):
        return _PROFILE_VALUE_TRAP
    if _detect_turnaround(metrics) is not None:
        return _PROFILE_TURNAROUND
    if _is_compounder(metrics):
        return _PROFILE_COMPOUNDER
    if _is_reinvestment_phase(metrics):
        return _PROFILE_REINVESTMENT
    if _is_cyclical(metrics):
        return _PROFILE_CYCLICAL
    if _is_low_visibility(metrics):
        return _PROFILE_LOW_VISIBILITY
    return _PROFILE_STANDARD


def _apply_reinvestment_cfq_relief(
    metrics: Mapping[str, object],
    bloc_results: dict[str, _BlocResult],
) -> dict[str, _BlocResult]:
    if not _is_reinvestment_phase(metrics):
        return bloc_results
    cfq = bloc_results.get("cash_flow_quality")
    if cfq is None or cfq.available_metrics == 0:
        return bloc_results
    if cfq.score >= _CFQ_REINVESTMENT_FLOOR:
        return bloc_results
    lift = min(_CFQ_REINVESTMENT_FLOOR - cfq.score, _CFQ_REINVESTMENT_MAX_LIFT)
    new_score = cfq.score + lift
    bloc_results = dict(bloc_results)
    bloc_results["cash_flow_quality"] = _BlocResult(
        name=cfq.name,
        score=round(new_score, 2),
        available_metrics=cfq.available_metrics,
        total_metrics=cfq.total_metrics,
        contributions=cfq.contributions,
    )
    return bloc_results


# ---------------------------------------------------------------------------
# Red flag caps
# ---------------------------------------------------------------------------


def _detect_cap(
    metrics: Mapping[str, object],
    bloc_results: dict[str, _BlocResult],
) -> float:
    cap = 100.0

    if _is_distressed(metrics):
        cap = min(cap, CAP_DISTRESSED)

    if _is_value_trap(metrics, bloc_results):
        cap = min(cap, CAP_VALUE_TRAP)

    if _has_dangerous_debt(metrics):
        cap = min(cap, CAP_DANGEROUS_DEBT)

    turnaround = _detect_turnaround(metrics)
    if turnaround is not None and turnaround < 0:
        cap = min(cap, CAP_UNCONFIRMED_TURNAROUND)

    return cap


def _has_dangerous_debt(metrics: Mapping[str, object]) -> bool:
    debt = _get(metrics, "net_debt_to_ebitda")
    coverage = _get(metrics, "interest_coverage")
    if debt is not None and debt > 4.0:
        return True
    if coverage is not None and coverage < 1.5 and coverage > 0:
        return True
    return False


# ---------------------------------------------------------------------------
# Metric scoring
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get(metrics: Mapping[str, object], key: str) -> float | None:
    return _as_finite_float(metrics.get(key))


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


def _normalize_sector(value: str | None) -> str | None:
    if value is None:
        return None
    sector = value.strip()
    return sector if sector else None


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


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
        by_sector.setdefault(sector, []).append(item)

    ranks: dict[int, int] = {}
    for items in by_sector.values():
        ordered = sorted(items, key=lambda x: (-float(x.total_score), x.company_id, x.ticker or ""))
        for index, item in enumerate(ordered, start=1):
            ranks[item.company_id] = index
    return ranks


# ---------------------------------------------------------------------------
# Explanation helpers
# ---------------------------------------------------------------------------


def _overlay_stored_scores(
    metrics: Mapping[str, object],
    computed: SnapshotScores,
) -> SnapshotScores:
    sq = _as_finite_float(metrics.get(QUALITY_SCORE_KEY))
    sv = _as_finite_float(metrics.get(VALUE_SCORE_KEY))
    sg = _as_finite_float(metrics.get(GROWTH_SCORE_KEY))
    sr = _as_finite_float(metrics.get(RISK_SCORE_KEY))
    st = _as_finite_float(metrics.get(TOTAL_SCORE_KEY))
    if sq is None and sv is None and sg is None and sr is None and st is None:
        return computed
    return SnapshotScores(
        quality=sq if sq is not None else computed.quality,
        value=sv if sv is not None else computed.value,
        growth=sg if sg is not None else computed.growth,
        risk=sr if sr is not None else computed.risk,
        total=st if st is not None else computed.total,
    )


def _empty_explanation() -> ScoreExplanation:
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


def _resolve_snapshot_weights(
    metrics: Mapping[str, object],
    default_weights: SnapshotSubScoreWeights,
) -> SnapshotSubScoreWeights:
    qw = _as_finite_float(metrics.get(SCORE_WEIGHT_QUALITY_KEY))
    vw = _as_finite_float(metrics.get(SCORE_WEIGHT_VALUE_KEY))
    gw = _as_finite_float(metrics.get(SCORE_WEIGHT_GROWTH_KEY))
    rw = _as_finite_float(metrics.get(SCORE_WEIGHT_RISK_KEY))
    if None in (qw, vw, gw, rw):
        return default_weights
    candidate = SnapshotSubScoreWeights(
        quality_weight=float(qw),
        value_weight=float(vw),
        growth_weight=float(gw),
        risk_weight=float(rw),
    )
    try:
        validate_snapshot_sub_score_weights(candidate)
    except ValueError:
        return default_weights
    return candidate


def _build_category_contributions(
    scores: SnapshotScores,
    weights: Mapping[str, float],
) -> tuple[ScoreCategoryContribution, ...]:
    score_map = {
        "quality": scores.quality,
        "value": scores.value,
        "growth": scores.growth,
        "risk": scores.risk,
    }
    return tuple(
        ScoreCategoryContribution(
            category=cat,
            sub_score=score_map[cat],
            weight=weights[cat],
            weighted_points=round(score_map[cat] * weights[cat], 2),
        )
        for cat in _CATEGORY_ORDER
    )


def _score_dimensions(scores: SnapshotScores) -> list[tuple[str, float]]:
    return [
        ("quality", scores.quality),
        ("value", scores.value),
        ("growth", scores.growth),
        ("risk", scores.risk),
    ]


def _select_strength_points(scores: SnapshotScores) -> list[tuple[str, float]]:
    ordered = sorted(_score_dimensions(scores), key=lambda x: (-x[1], x[0]))
    selected = [item for item in ordered if item[1] >= _STRENGTH_THRESHOLD][:_MAX_EXPLANATION_POINTS]
    return selected if selected else ordered[:1]


def _select_weakness_points(
    scores: SnapshotScores,
    strengths: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    ordered = sorted(_score_dimensions(scores), key=lambda x: (x[1], x[0]))
    strength_names = {name for name, _ in strengths}
    selected = [item for item in ordered if item[1] <= _WEAKNESS_THRESHOLD and item[0] not in strength_names][
        :_MAX_EXPLANATION_POINTS
    ]
    if selected:
        return selected
    fallback = [item for item in ordered if item[0] not in strength_names]
    return fallback[:1] if fallback else ordered[:1]


def _select_positive_drivers(
    contributions: tuple[_MetricContribution, ...],
) -> tuple[ScoreMetricDriver, ...]:
    positives = [c for c in contributions if c.impact_points > 0.0]
    positives.sort(key=lambda x: (-x.impact_points, -x.weighted_points, x.category, x.metric))
    return tuple(_to_driver(c) for c in positives[:_MAX_EXPLANATION_POINTS])


def _select_negative_drivers(
    contributions: tuple[_MetricContribution, ...],
) -> tuple[ScoreMetricDriver, ...]:
    negatives = [c for c in contributions if c.impact_points < 0.0]
    negatives.sort(key=lambda x: (x.impact_points, -x.weighted_points, x.category, x.metric))
    return tuple(_to_driver(c) for c in negatives[:_MAX_EXPLANATION_POINTS])


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
        f"{c.category} {c.sub_score:.2f}*{c.weight:.2f}={c.weighted_points:.2f}" for c in category_contributions
    )
    strength_text = ", ".join(_format_explanation_point(n, s) for n, s in strengths)
    weakness_text = ", ".join(_format_explanation_point(n, s) for n, s in weaknesses)
    positive_text = ", ".join(_format_driver(d) for d in positive_drivers) if positive_drivers else "none"
    negative_text = ", ".join(_format_driver(d) for d in negative_drivers) if negative_drivers else "none"
    return (
        f"total {scores.total:.2f}/100 | construction: {construction} | "
        f"positive drivers: {positive_text} | negative drivers: {negative_text} | "
        f"strengths: {strength_text} | weaknesses: {weakness_text}"
    )


# ---------------------------------------------------------------------------
# Legacy standalone scoring (kept for backward compatibility)
# ---------------------------------------------------------------------------

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
    if total_weight < _ZERO:
        return 0.0
    return round((weighted_score / total_weight) * 100, 2)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

_SERVICE = ScoringService()


def compute_snapshot_scores(snapshot: KpiSnapshot) -> SnapshotScores:
    return _SERVICE.compute_snapshot_scores(snapshot)


def apply_scores(snapshot: KpiSnapshot) -> KpiSnapshot:
    return _SERVICE.apply_scores(snapshot)


def rank_companies_by_total_score(company_scores: list[CompanyTotalScore]) -> list[RankedCompanyTotalScore]:
    return _SERVICE.rank_companies_by_total_score(company_scores)


def describe_snapshot_score(snapshot: KpiSnapshot | None) -> ScoreExplanation:
    return _SERVICE.describe_snapshot_score(snapshot)
