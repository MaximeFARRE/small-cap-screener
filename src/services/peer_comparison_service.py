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
_MAX_PEER_ROWS_DEFAULT = 8
_ZERO = 1e-9
_NEAR_RELATIVE_THRESHOLD = 0.05
_POSITION_ABOVE = "au-dessus"
_POSITION_NEAR = "proche"
_POSITION_BELOW = "en dessous"

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
    "gross_margin",
    "operating_margin",
    "revenue_growth",
    "ebitda_growth",
)
_METRIC_ORDER: tuple[tuple[str, str], ...] = (
    ("total_score", "Total score"),
    ("quality_score", "Quality"),
    ("value_score", "Value"),
    ("growth_score", "Growth"),
    ("risk_score", "Risk"),
    ("ev_ebitda", "EV/EBITDA"),
    ("pe_ratio", "P/E"),
    ("gross_margin", "Gross margin"),
    ("operating_margin", "Operating margin"),
    ("revenue_growth", "Revenue growth"),
    ("ebitda_growth", "EBITDA growth"),
    ("data_quality_score", "Data quality"),
)


@dataclass(frozen=True)
class PeerMetricComparison:
    key: str
    label: str
    company_value: float | None
    sector_median: float | None
    position: str | None


@dataclass(frozen=True)
class PeerCompanyRow:
    company_id: int
    ticker: str | None
    name: str
    sector_rank: int | None
    total_score: float | None
    quality_score: float | None
    value_score: float | None
    growth_score: float | None
    risk_score: float | None
    ev_ebitda: float | None
    pe_ratio: float | None
    operating_margin: float | None
    revenue_growth: float | None
    data_quality_score: float | None


@dataclass(frozen=True)
class PeerComparisonData:
    sector: str | None
    company_sector_rank: int | None
    sector_company_count: int
    sector_scored_count: int
    peer_count: int
    metrics: list[PeerMetricComparison]
    peer_rows: list[PeerCompanyRow]


@dataclass
class PeerComparisonService:
    session_scope_factory: SessionScopeFactory = field(default=get_session)
    screening_service: ScreeningService | None = None
    max_peer_rows: int = _MAX_PEER_ROWS_DEFAULT

    def __post_init__(self) -> None:
        if self.screening_service is None:
            self.screening_service = ScreeningService(session_scope_factory=self.session_scope_factory)

    def get_company_peer_comparison(self, company_id: int) -> PeerComparisonData:
        if self.screening_service is None:
            raise RuntimeError("screening service is not initialized")
        universe = self.screening_service.list_universe_with_scores()
        target_entry = next((entry for entry in universe if entry.company_id == company_id), None)
        if target_entry is None:
            return _empty_peer_comparison(sector=None)

        sector = _normalize_optional_text(target_entry.sector)
        if sector is None:
            return _build_peer_comparison_with_missing_sector(target_entry)

        sector_entries = [entry for entry in universe if _normalize_optional_text(entry.sector) == sector]
        peer_entries = [entry for entry in sector_entries if entry.company_id != company_id]
        snapshots_by_company_id = _load_snapshots_by_company_id(
            self.session_scope_factory,
            [company_id] + [entry.company_id for entry in peer_entries],
        )
        target_snapshot = snapshots_by_company_id.get(company_id)
        metrics = _build_metric_comparisons(target_entry, target_snapshot, peer_entries, snapshots_by_company_id)
        peer_rows = _build_peer_rows(peer_entries, snapshots_by_company_id, self.max_peer_rows)
        return PeerComparisonData(
            sector=sector,
            company_sector_rank=target_entry.sector_rank,
            sector_company_count=len(sector_entries),
            sector_scored_count=sum(1 for entry in sector_entries if entry.sector_rank is not None),
            peer_count=len(peer_entries),
            metrics=metrics,
            peer_rows=peer_rows,
        )


def _build_peer_comparison_with_missing_sector(target_entry: UniverseScreeningEntry) -> PeerComparisonData:
    metrics = _build_metric_comparisons(
        target_entry,
        None,
        peer_entries=[],
        snapshots_by_company_id={},
    )
    return PeerComparisonData(
        sector=None,
        company_sector_rank=target_entry.sector_rank,
        sector_company_count=0,
        sector_scored_count=0,
        peer_count=0,
        metrics=metrics,
        peer_rows=[],
    )


def _empty_peer_comparison(sector: str | None) -> PeerComparisonData:
    return PeerComparisonData(
        sector=sector,
        company_sector_rank=None,
        sector_company_count=0,
        sector_scored_count=0,
        peer_count=0,
        metrics=[],
        peer_rows=[],
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
    for key, label in _METRIC_ORDER:
        company_value = _metric_value(key, target_entry, target_snapshot)
        peer_values = [
            value
            for value in (
                _metric_value(key, entry, snapshots_by_company_id.get(entry.company_id)) for entry in peer_entries
            )
            if value is not None
        ]
        sector_median = float(median(peer_values)) if peer_values else None
        comparisons.append(
            PeerMetricComparison(
                key=key,
                label=label,
                company_value=company_value,
                sector_median=sector_median,
                position=_relative_position(company_value, sector_median),
            )
        )
    return comparisons


def _build_peer_rows(
    peer_entries: list[UniverseScreeningEntry],
    snapshots_by_company_id: dict[int, KpiSnapshot | None],
    max_rows: int,
) -> list[PeerCompanyRow]:
    ordered = sorted(peer_entries, key=_peer_sort_key)
    selected = ordered[:max_rows] if max_rows > 0 else []
    rows: list[PeerCompanyRow] = []
    for entry in selected:
        snapshot = snapshots_by_company_id.get(entry.company_id)
        rows.append(
            PeerCompanyRow(
                company_id=entry.company_id,
                ticker=entry.ticker,
                name=entry.name,
                sector_rank=entry.sector_rank,
                total_score=entry.total_score,
                quality_score=entry.quality_score,
                value_score=entry.value_score,
                growth_score=entry.growth_score,
                risk_score=entry.risk_score,
                ev_ebitda=_metric_value("ev_ebitda", entry, snapshot),
                pe_ratio=_metric_value("pe_ratio", entry, snapshot),
                operating_margin=_metric_value("operating_margin", entry, snapshot),
                revenue_growth=_metric_value("revenue_growth", entry, snapshot),
                data_quality_score=entry.data_quality_score,
            )
        )
    return rows


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


def _relative_position(company_value: float | None, sector_median: float | None) -> str | None:
    if company_value is None or sector_median is None:
        return None
    delta = company_value - sector_median
    if abs(sector_median) < _ZERO:
        if abs(delta) < _ZERO:
            return _POSITION_NEAR
        return _POSITION_ABOVE if delta > 0.0 else _POSITION_BELOW
    if abs(delta) / abs(sector_median) <= _NEAR_RELATIVE_THRESHOLD:
        return _POSITION_NEAR
    return _POSITION_ABOVE if delta > 0.0 else _POSITION_BELOW


def _peer_sort_key(entry: UniverseScreeningEntry) -> tuple[bool, int, bool, str, int]:
    ticker = _normalize_optional_text(entry.ticker) or ""
    rank = entry.sector_rank if entry.sector_rank is not None else 10**9
    return (entry.sector_rank is None, rank, ticker == "", ticker, entry.company_id)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized
