from __future__ import annotations

import math
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.models.kpi_snapshot import KpiSnapshot
from src.repositories import company_repository, kpi_snapshot_repository
from src.repositories.database import get_session
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.ratio_service import CompanyRatios
from src.services.scoring_service import (
    GROWTH_SCORE_KEY,
    QUALITY_SCORE_KEY,
    RISK_SCORE_KEY,
    TOTAL_SCORE_KEY,
    VALUE_SCORE_KEY,
    RankedCompanyTotalScore,
    ScoringService,
    compute_score,
)

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


@dataclass
class ScreeningCriteria:
    max_pe: float | None = None
    max_pb: float | None = None
    max_ev_ebitda: float | None = None
    min_roe: float | None = None
    min_net_margin: float | None = None
    max_debt_to_equity: float | None = None
    max_net_debt_to_ebitda: float | None = None
    min_ebit_margin: float | None = None


@dataclass
class ScreeningResult:
    ratios: CompanyRatios
    score: float


@dataclass(frozen=True)
class UniverseScreeningEntry:
    company_id: int
    ticker: str | None
    name: str
    sector: str | None
    total_score: float | None
    quality_score: float | None
    value_score: float | None
    growth_score: float | None
    risk_score: float | None
    rank: int | None
    sector_rank: int | None


@dataclass(frozen=True)
class UniverseScreeningFilters:
    sector: str | None = None
    min_total_score: float | None = None
    scored_only: bool = False
    top_n: int | None = None


@dataclass
class ScreeningService:
    session_scope_factory: SessionScopeFactory = get_session
    scoring_service: ScoringService = field(default_factory=ScoringService)
    kpi_snapshot_service: KpiSnapshotService | None = None
    default_country: str = "France"
    default_max_market_cap: float = 2_000_000_000.0
    default_min_average_daily_volume: float | None = None

    def __post_init__(self) -> None:
        if self.kpi_snapshot_service is None:
            self.kpi_snapshot_service = KpiSnapshotService(
                session_scope_factory=self.session_scope_factory,
                scoring_service=self.scoring_service,
                default_country=self.default_country,
                default_max_market_cap=self.default_max_market_cap,
                default_min_average_daily_volume=self.default_min_average_daily_volume,
            )

    def list_universe_with_scores(
        self,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> list[UniverseScreeningEntry]:
        target_max_market_cap = self.default_max_market_cap if max_market_cap is None else max_market_cap
        target_min_avg_daily_volume = (
            self.default_min_average_daily_volume if min_average_daily_volume is None else min_average_daily_volume
        )
        target_country = self.default_country if country is None else country

        with self.session_scope_factory() as session:
            investable = company_repository.get_investable_universe(
                session,
                max_market_cap=target_max_market_cap,
                min_average_daily_volume=target_min_avg_daily_volume,
                country=target_country,
            )
            companies_by_id = {company.id: company for company in investable}
            snapshots_by_company_id = {
                company.id: kpi_snapshot_repository.get_latest_by_company(session, company.id) for company in investable
            }

        if self.kpi_snapshot_service is None:
            raise RuntimeError("kpi snapshot service is not initialized")

        ranking = self.kpi_snapshot_service.rank_universe_by_total_score(
            max_market_cap=target_max_market_cap,
            min_average_daily_volume=target_min_avg_daily_volume,
            country=target_country,
        )
        return _build_universe_screening_entries(
            ranking=ranking,
            companies_by_id=companies_by_id,
            snapshots_by_company_id=snapshots_by_company_id,
        )

    def filter_universe_with_scores(
        self,
        filters: UniverseScreeningFilters,
        *,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> list[UniverseScreeningEntry]:
        universe = self.list_universe_with_scores(
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        filtered = _apply_universe_screening_filters(universe, filters)
        ordered = _sort_universe_screening_entries(filtered)
        if filters.top_n is None:
            return ordered
        if filters.top_n <= 0:
            return []
        return ordered[: filters.top_n]


def _passes(ratios: CompanyRatios, criteria: ScreeningCriteria) -> bool:
    checks: list[tuple[float | None, float | None, bool]] = [
        (ratios.pe_ratio, criteria.max_pe, True),
        (ratios.pb_ratio, criteria.max_pb, True),
        (ratios.ev_ebitda, criteria.max_ev_ebitda, True),
        (ratios.roe, criteria.min_roe, False),
        (ratios.net_margin, criteria.min_net_margin, False),
        (ratios.debt_to_equity, criteria.max_debt_to_equity, True),
        (ratios.net_debt_to_ebitda, criteria.max_net_debt_to_ebitda, True),
        (ratios.ebit_margin, criteria.min_ebit_margin, False),
    ]
    for value, threshold, is_max in checks:
        if threshold is None or value is None:
            continue
        if is_max and value > threshold:
            return False
        if not is_max and value < threshold:
            return False
    return True


def apply_filters(
    candidates: list[CompanyRatios],
    criteria: ScreeningCriteria,
) -> list[ScreeningResult]:
    results = [ScreeningResult(ratios=r, score=compute_score(r)) for r in candidates if _passes(r, criteria)]
    return sorted(results, key=lambda x: x.score, reverse=True)


def _build_universe_screening_entries(
    *,
    ranking: list[RankedCompanyTotalScore],
    companies_by_id: dict[int, object],
    snapshots_by_company_id: dict[int, KpiSnapshot | None],
) -> list[UniverseScreeningEntry]:
    entries: list[UniverseScreeningEntry] = []
    for ranked in ranking:
        company = companies_by_id.get(ranked.company_id)
        if company is None:
            continue
        snapshot = snapshots_by_company_id.get(ranked.company_id)
        entries.append(
            UniverseScreeningEntry(
                company_id=company.id,
                ticker=company.ticker,
                name=company.name,
                sector=company.sector,
                total_score=_snapshot_metric_as_float(snapshot, TOTAL_SCORE_KEY),
                quality_score=_snapshot_metric_as_float(snapshot, QUALITY_SCORE_KEY),
                value_score=_snapshot_metric_as_float(snapshot, VALUE_SCORE_KEY),
                growth_score=_snapshot_metric_as_float(snapshot, GROWTH_SCORE_KEY),
                risk_score=_snapshot_metric_as_float(snapshot, RISK_SCORE_KEY),
                rank=ranked.rank,
                sector_rank=ranked.sector_rank,
            )
        )
    return entries


def _snapshot_metric_as_float(snapshot: KpiSnapshot | None, metric_key: str) -> float | None:
    if snapshot is None:
        return None
    raw = snapshot.metrics.get(metric_key)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return value


def _apply_universe_screening_filters(
    entries: list[UniverseScreeningEntry],
    filters: UniverseScreeningFilters,
) -> list[UniverseScreeningEntry]:
    target_sector = _normalize_optional_text(filters.sector)
    output: list[UniverseScreeningEntry] = []
    for entry in entries:
        if target_sector is not None:
            sector = _normalize_optional_text(entry.sector)
            if sector != target_sector:
                continue
        if filters.scored_only and entry.total_score is None:
            continue
        if filters.min_total_score is not None:
            if entry.total_score is None or entry.total_score < filters.min_total_score:
                continue
        output.append(entry)
    return output


def _sort_universe_screening_entries(entries: list[UniverseScreeningEntry]) -> list[UniverseScreeningEntry]:
    return sorted(entries, key=_universe_screening_sort_key)


def _universe_screening_sort_key(entry: UniverseScreeningEntry) -> tuple[bool, float, bool, str, int]:
    rank = float(entry.rank) if entry.rank is not None else math.inf
    ticker = entry.ticker or ""
    return (entry.rank is None, rank, entry.ticker is None, ticker, entry.company_id)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized
