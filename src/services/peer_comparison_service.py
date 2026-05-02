from __future__ import annotations

import math
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from statistics import median

from sqlalchemy.orm import Session

from src.models.kpi_snapshot import KpiSnapshot
from src.repositories import kpi_snapshot_repository
from src.repositories.database import get_session
from src.services.screening_service import ScreeningService, UniverseScreeningEntry

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_MAX_PEER_ROWS_DEFAULT = 10
_ZERO = 1e-9
_NEAR_RELATIVE_THRESHOLD = 0.05
_DEFAULT_MARKET_CAP = 0.0

_SCORE_KEYS: tuple[str, ...] = (
    "total_score",
    "quality_score",
    "value_score",
    "growth_score",
    "risk_score",
    "data_quality_score",
)
_SNAPSHOT_KEYS: tuple[str, ...] = (
    "ev_ebitda",
    "pe_ratio",
    "fcf_yield",
    "revenue_growth",
    "ebitda_margin",
    "roic",
    "roe",
    "net_debt_to_ebitda",
)
_METRIC_ORDER: tuple[tuple[str, str, bool], ...] = (
    ("ev_ebitda", "EV/EBITDA", True),
    ("pe_ratio", "P/E", True),
    ("fcf_yield", "FCF Yield", False),
    ("revenue_growth", "Revenue Growth", False),
    ("ebitda_margin", "EBITDA Margin", False),
    ("roic", "ROIC", False),
    ("roe", "ROE", False),
    ("net_debt_to_ebitda", "Net Debt / EBITDA", True),
)


@dataclass(frozen=True)
class PeerMetricComparison:
    key: str
    label: str
    company_value: float | None
    sector_median: float | None
    percentile_rank: float | None
    premium_discount_vs_peers: float | None
    is_lower_better: bool


@dataclass(frozen=True)
class PeerCompanyRow:
    company_id: int
    ticker: str | None
    name: str
    sector_rank: int | None
    total_score: float | None
    market_cap: float | None
    ev_ebitda: float | None
    pe_ratio: float | None
    fcf_yield: float | None
    revenue_growth: float | None
    ebitda_margin: float | None
    roic: float | None
    roe: float | None
    net_debt_to_ebitda: float | None
    similarity_score: float | None
    peer_rank: int | None
    score_percentile: float | None


@dataclass(frozen=True)
class PeerAnalystAssessment:
    cheaper_than_peers: bool | None
    higher_quality_than_peers: bool | None
    growth_premium_justified: bool | None
    balance_sheet_weaker: bool | None


@dataclass(frozen=True)
class PeerComparisonData:
    sector: str | None
    market: str | None
    market_cap_bucket: str | None
    company_sector_rank: int | None
    sector_company_count: int
    sector_scored_count: int
    peer_count: int
    metrics: list[PeerMetricComparison]
    peer_rows: list[PeerCompanyRow]
    analyst_assessment: PeerAnalystAssessment


@dataclass
class PeerComparisonService:
    session_scope_factory: SessionScopeFactory = field(default=get_session)
    screening_service: ScreeningService | None = None
    max_peer_rows: int = _MAX_PEER_ROWS_DEFAULT
    min_peers_for_market_constraint: int = 3

    def __post_init__(self) -> None:
        if self.screening_service is None:
            self.screening_service = ScreeningService(session_scope_factory=self.session_scope_factory)

    def get_company_peer_comparison(self, company_id: int) -> PeerComparisonData:
        if self.screening_service is None:
            raise RuntimeError("screening service is not initialized")
        universe = self.screening_service.list_universe_with_scores()
        target_entry = next((entry for entry in universe if entry.company_id == company_id), None)
        if target_entry is None:
            return _empty_peer_comparison()

        sector = _normalize_optional_text(target_entry.sector)
        if sector is None:
            return _empty_peer_comparison()

        same_sector_entries = [entry for entry in universe if _normalize_optional_text(entry.sector) == sector]
        target_bucket = _market_cap_bucket(target_entry.market_cap)
        bucket_filtered = [
            entry
            for entry in same_sector_entries
            if entry.company_id != target_entry.company_id and _market_cap_bucket(entry.market_cap) == target_bucket
        ]

        target_market = _normalize_optional_text(target_entry.market)
        market_filtered = [
            entry for entry in bucket_filtered if _normalize_optional_text(entry.market) == target_market
        ]
        if target_market is not None and len(market_filtered) >= self.min_peers_for_market_constraint:
            peer_entries = market_filtered
        else:
            peer_entries = bucket_filtered

        snapshots_by_company_id = _load_snapshots_by_company_id(
            self.session_scope_factory,
            [company_id] + [entry.company_id for entry in peer_entries],
        )
        target_snapshot = snapshots_by_company_id.get(company_id)
        metrics = _build_metric_comparisons(target_entry, target_snapshot, peer_entries, snapshots_by_company_id)
        peer_rows = _build_peer_rows(
            target_entry=target_entry,
            peer_entries=peer_entries,
            snapshots_by_company_id=snapshots_by_company_id,
            max_rows=self.max_peer_rows,
        )
        return PeerComparisonData(
            sector=sector,
            market=target_market,
            market_cap_bucket=target_bucket,
            company_sector_rank=target_entry.sector_rank,
            sector_company_count=len(same_sector_entries),
            sector_scored_count=sum(1 for entry in same_sector_entries if entry.sector_rank is not None),
            peer_count=len(peer_entries),
            metrics=metrics,
            peer_rows=peer_rows,
            analyst_assessment=_build_analyst_assessment(metrics),
        )


def _empty_peer_comparison() -> PeerComparisonData:
    return PeerComparisonData(
        sector=None,
        market=None,
        market_cap_bucket=None,
        company_sector_rank=None,
        sector_company_count=0,
        sector_scored_count=0,
        peer_count=0,
        metrics=[],
        peer_rows=[],
        analyst_assessment=PeerAnalystAssessment(None, None, None, None),
    )


def _load_snapshots_by_company_id(
    session_scope_factory: SessionScopeFactory,
    company_ids: list[int],
) -> dict[int, KpiSnapshot | None]:
    unique_ids = sorted(set(company_ids))
    if not unique_ids:
        return {}
    with session_scope_factory() as session:
        return {
            company_id: kpi_snapshot_repository.get_latest_by_company(session, company_id) for company_id in unique_ids
        }


def _build_metric_comparisons(
    target_entry: UniverseScreeningEntry,
    target_snapshot: KpiSnapshot | None,
    peer_entries: list[UniverseScreeningEntry],
    snapshots_by_company_id: dict[int, KpiSnapshot | None],
) -> list[PeerMetricComparison]:
    comparisons: list[PeerMetricComparison] = []
    for key, label, is_lower_better in _METRIC_ORDER:
        company_value = _metric_value(key, target_entry, target_snapshot)
        peer_values = [
            value
            for value in (
                _metric_value(key, entry, snapshots_by_company_id.get(entry.company_id)) for entry in peer_entries
            )
            if value is not None
        ]
        sector_median = float(median(peer_values)) if peer_values else None
        percentile_rank = _percentile_rank(company_value, peer_values, is_lower_better=is_lower_better)
        premium_discount = _premium_discount(company_value, sector_median)
        comparisons.append(
            PeerMetricComparison(
                key=key,
                label=label,
                company_value=company_value,
                sector_median=sector_median,
                percentile_rank=percentile_rank,
                premium_discount_vs_peers=premium_discount,
                is_lower_better=is_lower_better,
            )
        )
    return comparisons


def _build_peer_rows(
    *,
    target_entry: UniverseScreeningEntry,
    peer_entries: list[UniverseScreeningEntry],
    snapshots_by_company_id: dict[int, KpiSnapshot | None],
    max_rows: int,
) -> list[PeerCompanyRow]:
    ordered = sorted(
        peer_entries,
        key=lambda entry: _peer_distance(target_entry, entry, snapshots_by_company_id) + _peer_sort_tie_breaker(entry),
    )
    selected = ordered[:max_rows] if max_rows > 0 else []
    ranked_entries = compute_peer_ranking(selected)
    rows: list[PeerCompanyRow] = []
    for entry in selected:
        snapshot = snapshots_by_company_id.get(entry.company_id)
        rank_info = ranked_entries.get(entry.company_id)
        rows.append(
            PeerCompanyRow(
                company_id=entry.company_id,
                ticker=entry.ticker,
                name=entry.name,
                sector_rank=entry.sector_rank,
                total_score=entry.total_score,
                market_cap=entry.market_cap,
                ev_ebitda=_metric_value("ev_ebitda", entry, snapshot),
                pe_ratio=_metric_value("pe_ratio", entry, snapshot),
                fcf_yield=_metric_value("fcf_yield", entry, snapshot),
                revenue_growth=_metric_value("revenue_growth", entry, snapshot),
                ebitda_margin=_metric_value("ebitda_margin", entry, snapshot),
                roic=_metric_value("roic", entry, snapshot),
                roe=_metric_value("roe", entry, snapshot),
                net_debt_to_ebitda=_metric_value("net_debt_to_ebitda", entry, snapshot),
                similarity_score=_similarity_score(target_entry, entry, snapshots_by_company_id),
                peer_rank=rank_info[0] if rank_info is not None else None,
                score_percentile=rank_info[1] if rank_info is not None else None,
            )
        )
    return rows


def compute_peer_ranking(entries: list[UniverseScreeningEntry]) -> dict[int, tuple[int, float]]:
    scored = [entry for entry in entries if entry.total_score is not None]
    ordered = sorted(scored, key=lambda entry: (-(entry.total_score or 0.0), entry.company_id))
    total = len(ordered)
    ranked: dict[int, tuple[int, float]] = {}
    if total == 0:
        return ranked
    for index, entry in enumerate(ordered, start=1):
        percentile = ((total - index + 1) / total) * 100.0
        ranked[entry.company_id] = (index, percentile)
    return ranked


def _metric_value(key: str, entry: UniverseScreeningEntry, snapshot: KpiSnapshot | None) -> float | None:
    if key in _SCORE_KEYS:
        return getattr(entry, key)
    if key in _SNAPSHOT_KEYS:
        return _snapshot_metric(snapshot, key)
    return None


def _snapshot_metric(snapshot: KpiSnapshot | None, key: str) -> float | None:
    if snapshot is None:
        return None
    return _as_finite_float(snapshot.metrics.get(key))


def _as_finite_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _percentile_rank(value: float | None, peers: list[float], *, is_lower_better: bool) -> float | None:
    if value is None or not peers:
        return None
    better_count = sum(1 for peer_value in peers if (value <= peer_value if is_lower_better else value >= peer_value))
    return (better_count / len(peers)) * 100.0


def _premium_discount(value: float | None, median_value: float | None) -> float | None:
    if value is None or median_value is None:
        return None
    if abs(median_value) < _ZERO:
        return None
    return ((value - median_value) / abs(median_value)) * 100.0


def _build_analyst_assessment(metrics: list[PeerMetricComparison]) -> PeerAnalystAssessment:
    metric_by_key = {metric.key: metric for metric in metrics}
    ev = metric_by_key.get("ev_ebitda")
    pe = metric_by_key.get("pe_ratio")
    quality = metric_by_key.get("roic")
    growth = metric_by_key.get("revenue_growth")
    debt = metric_by_key.get("net_debt_to_ebitda")

    cheaper_than_peers = _both_true(
        _is_better_than_median(ev, lower_is_better=True),
        _is_better_than_median(pe, lower_is_better=True),
    )
    higher_quality_than_peers = _is_better_than_median(quality, lower_is_better=False)
    growth_premium_justified = _growth_premium_justified(growth, ev, pe)
    balance_sheet_weaker = _is_worse_than_median(debt, lower_is_better=True)
    return PeerAnalystAssessment(
        cheaper_than_peers=cheaper_than_peers,
        higher_quality_than_peers=higher_quality_than_peers,
        growth_premium_justified=growth_premium_justified,
        balance_sheet_weaker=balance_sheet_weaker,
    )


def _is_better_than_median(metric: PeerMetricComparison | None, *, lower_is_better: bool) -> bool | None:
    if metric is None or metric.company_value is None or metric.sector_median is None:
        return None
    if lower_is_better:
        return metric.company_value < metric.sector_median
    return metric.company_value > metric.sector_median


def _is_worse_than_median(metric: PeerMetricComparison | None, *, lower_is_better: bool) -> bool | None:
    better = _is_better_than_median(metric, lower_is_better=lower_is_better)
    if better is None:
        return None
    return not better


def _both_true(left: bool | None, right: bool | None) -> bool | None:
    if left is None or right is None:
        return None
    return left and right


def _growth_premium_justified(
    growth_metric: PeerMetricComparison | None,
    ev_metric: PeerMetricComparison | None,
    pe_metric: PeerMetricComparison | None,
) -> bool | None:
    if growth_metric is None or growth_metric.company_value is None or growth_metric.sector_median is None:
        return None
    growth_above = growth_metric.company_value > growth_metric.sector_median
    valuation_above = False
    has_valuation = False
    for valuation_metric in (ev_metric, pe_metric):
        if valuation_metric is None or valuation_metric.company_value is None or valuation_metric.sector_median is None:
            continue
        has_valuation = True
        if valuation_metric.company_value > valuation_metric.sector_median:
            valuation_above = True
    if not has_valuation:
        return None
    if not valuation_above:
        return True
    return growth_above


def _peer_distance(
    target: UniverseScreeningEntry,
    peer: UniverseScreeningEntry,
    snapshots_by_company_id: dict[int, KpiSnapshot | None],
) -> tuple[bool, float]:
    target_snapshot = snapshots_by_company_id.get(target.company_id)
    peer_snapshot = snapshots_by_company_id.get(peer.company_id)
    target_vector = _metric_vector(target, target_snapshot)
    peer_vector = _metric_vector(peer, peer_snapshot)
    common_keys = sorted(set(target_vector) & set(peer_vector))
    if not common_keys:
        return (True, float("inf"))
    distance = 0.0
    for key in common_keys:
        distance += abs(target_vector[key] - peer_vector[key])
    return (False, distance)


def _similarity_score(
    target: UniverseScreeningEntry,
    peer: UniverseScreeningEntry,
    snapshots_by_company_id: dict[int, KpiSnapshot | None],
) -> float | None:
    missing, distance = _peer_distance(target, peer, snapshots_by_company_id)
    if missing:
        return None
    return max(0.0, 100.0 - min(distance, 100.0))


def _metric_vector(entry: UniverseScreeningEntry, snapshot: KpiSnapshot | None) -> dict[str, float]:
    vector: dict[str, float] = {}
    if entry.total_score is not None:
        vector["total_score"] = entry.total_score
    for key in ("ev_ebitda", "pe_ratio", "fcf_yield", "revenue_growth", "ebitda_margin", "roic", "roe"):
        value = _metric_value(key, entry, snapshot)
        if value is None:
            continue
        vector[key] = value
    return vector


def _peer_sort_tie_breaker(entry: UniverseScreeningEntry) -> tuple[bool, int, bool, str, int]:
    ticker = _normalize_optional_text(entry.ticker) or ""
    rank = entry.sector_rank if entry.sector_rank is not None else 10**9
    return (entry.sector_rank is None, rank, ticker == "", ticker, entry.company_id)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized


def _market_cap_bucket(market_cap: float | None) -> str:
    value = market_cap if market_cap is not None else _DEFAULT_MARKET_CAP
    if value < 300_000_000:
        return "small"
    if value < 2_000_000_000:
        return "mid"
    return "large"
