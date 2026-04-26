from __future__ import annotations

import csv
import math
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from io import BytesIO, StringIO
from typing import Literal

import pandas as pd
from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.models.screening_snapshot import ScreeningSnapshot
from src.models.watchlist_entry import WatchlistEntry
from src.repositories import (
    company_repository,
    kpi_snapshot_repository,
    screening_snapshot_repository,
    watchlist_repository,
)
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
STALE_REFRESH_DAYS = 30

UniverseScreeningSortField = Literal[
    "rank",
    "total_score",
    "quality_score",
    "value_score",
    "growth_score",
    "risk_score",
    "ticker",
]
WatchlistScopeFilter = Literal["all", "watchlist_only", "non_watchlist_only"]
WatchlistExclusionFilter = Literal["all", "excluded_only", "non_excluded_only"]
_UNIVERSE_SCREENING_EXPORT_COLUMNS: tuple[str, ...] = (
    "ticker",
    "name",
    "sector",
    "total_score",
    "quality_score",
    "value_score",
    "growth_score",
    "risk_score",
    "rank",
    "sector_rank",
)


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
    data_quality_score: float | None = None
    last_universe_refresh_at: datetime | None = None
    snapshot_date: date | None = None


@dataclass(frozen=True)
class UniverseScreeningFilters:
    sector: str | None = None
    min_total_score: float | None = None
    min_data_quality_score: float | None = None
    stale_only: bool = False
    scored_only: bool = False
    watchlist_scope: WatchlistScopeFilter = "all"
    watchlist_status: str | None = None
    exclusion_filter: WatchlistExclusionFilter | None = None
    include_excluded: bool = False
    top_n: int | None = None
    sort_by: UniverseScreeningSortField = "rank"
    descending: bool = False


@dataclass(frozen=True)
class SavedScreeningSnapshot:
    snapshot_id: int
    name: str
    created_at: datetime
    filters: dict[str, object]
    company_count: int
    company_ids: list[int]
    results: list[dict[str, object]]


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
        watchlist_entries_by_company_id = self._list_watchlist_entries_by_company_id()
        excluded_company_ids = {
            company_id for company_id, entry in watchlist_entries_by_company_id.items() if entry.is_excluded
        }
        if filters.include_excluded:
            excluded_company_ids = set()

        filtered = _apply_universe_screening_filters(
            universe,
            filters,
            watchlist_entries_by_company_id=watchlist_entries_by_company_id,
            excluded_company_ids=excluded_company_ids,
        )
        ordered = _sort_universe_screening_entries(
            filtered,
            sort_by=filters.sort_by,
            descending=filters.descending,
        )
        if filters.top_n is None:
            return ordered
        if filters.top_n <= 0:
            return []
        return ordered[: filters.top_n]

    def export_universe_with_scores_csv(
        self,
        filters: UniverseScreeningFilters,
        *,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> str:
        rows = self.filter_universe_with_scores(
            filters,
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        return _build_universe_screening_csv(rows)

    def export_universe_with_scores_excel(
        self,
        filters: UniverseScreeningFilters,
        *,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> bytes:
        rows = self.filter_universe_with_scores(
            filters,
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        return _build_universe_screening_excel(rows)

    def save_screening_snapshot(
        self,
        filters: UniverseScreeningFilters,
        *,
        name: str = "screening snapshot",
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> SavedScreeningSnapshot:
        rows = self.filter_universe_with_scores(
            filters,
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        company_ids = [row.company_id for row in rows]
        results = _build_universe_screening_export_records(rows)
        with self.session_scope_factory() as session:
            stored = screening_snapshot_repository.add(
                session,
                ScreeningSnapshot(
                    name=name,
                    filters=asdict(filters),
                    company_ids=company_ids,
                    scores={
                        "company_count": len(company_ids),
                        "results": results,
                    },
                ),
            )
            session.refresh(stored)
            return _to_saved_screening_snapshot(stored)

    def get_screening_snapshot(self, snapshot_id: int) -> SavedScreeningSnapshot | None:
        with self.session_scope_factory() as session:
            snapshot = screening_snapshot_repository.get_by_id(session, snapshot_id)
        if snapshot is None:
            return None
        return _to_saved_screening_snapshot(snapshot)

    def _list_excluded_company_ids(self) -> set[int]:
        with self.session_scope_factory() as session:
            return watchlist_repository.list_excluded_company_ids(session)

    def _list_watchlist_entries_by_company_id(self) -> dict[int, WatchlistEntry]:
        with self.session_scope_factory() as session:
            entries = watchlist_repository.list_all(session)
        return {entry.company_id: entry for entry in entries}


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
    companies_by_id: dict[int, Company],
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
                data_quality_score=_snapshot_metric_as_float(snapshot, "data_quality_score"),
                last_universe_refresh_at=company.last_universe_refresh_at,
                snapshot_date=snapshot.snapshot_date if snapshot is not None else None,
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
    *,
    watchlist_entries_by_company_id: dict[int, WatchlistEntry],
    excluded_company_ids: set[int],
) -> list[UniverseScreeningEntry]:
    target_sector = _normalize_optional_text(filters.sector)
    target_watchlist_status = _normalize_optional_text(filters.watchlist_status)
    stale_threshold = datetime.now(UTC) - timedelta(days=STALE_REFRESH_DAYS) if filters.stale_only else None
    output: list[UniverseScreeningEntry] = []
    for entry in entries:
        watchlist_entry = watchlist_entries_by_company_id.get(entry.company_id)
        is_in_watchlist = watchlist_entry is not None
        is_excluded = watchlist_entry.is_excluded if watchlist_entry is not None else False
        if filters.watchlist_scope == "watchlist_only" and not is_in_watchlist:
            continue
        if filters.watchlist_scope == "non_watchlist_only" and is_in_watchlist:
            continue
        if target_watchlist_status is not None:
            entry_status = _normalize_optional_text(watchlist_entry.status) if watchlist_entry is not None else None
            if entry_status != target_watchlist_status:
                continue
        if filters.exclusion_filter == "excluded_only":
            if not is_excluded:
                continue
        elif filters.exclusion_filter == "non_excluded_only":
            if is_excluded:
                continue
        if entry.company_id in excluded_company_ids:
            continue
        if target_sector is not None:
            sector = _normalize_optional_text(entry.sector)
            if sector != target_sector:
                continue
        if filters.scored_only and entry.total_score is None:
            continue
        if filters.min_total_score is not None:
            if entry.total_score is None or entry.total_score < filters.min_total_score:
                continue
        if filters.min_data_quality_score is not None:
            if entry.data_quality_score is None or entry.data_quality_score < filters.min_data_quality_score:
                continue
        if stale_threshold is not None:
            refresh_at = entry.last_universe_refresh_at
            if refresh_at is not None and refresh_at >= stale_threshold:
                continue
        output.append(entry)
    return output


def _sort_universe_screening_entries(
    entries: list[UniverseScreeningEntry],
    *,
    sort_by: UniverseScreeningSortField,
    descending: bool,
) -> list[UniverseScreeningEntry]:
    by_ticker = sorted(entries, key=_ticker_fallback_key)
    if sort_by == "ticker":
        return _sort_entries_by_ticker(by_ticker, descending=descending)
    return _sort_entries_by_numeric_field(
        by_ticker,
        sort_by=sort_by,
        descending=descending,
    )


def _sort_entries_by_ticker(
    entries: list[UniverseScreeningEntry],
    *,
    descending: bool,
) -> list[UniverseScreeningEntry]:
    with_ticker: list[UniverseScreeningEntry] = []
    without_ticker: list[UniverseScreeningEntry] = []
    for entry in entries:
        if _normalize_optional_text(entry.ticker) is None:
            without_ticker.append(entry)
            continue
        with_ticker.append(entry)
    return sorted(with_ticker, key=_ticker_text_key, reverse=descending) + without_ticker


def _sort_entries_by_numeric_field(
    entries: list[UniverseScreeningEntry],
    *,
    sort_by: UniverseScreeningSortField,
    descending: bool,
) -> list[UniverseScreeningEntry]:
    with_value: list[tuple[UniverseScreeningEntry, float]] = []
    without_value: list[UniverseScreeningEntry] = []
    for entry in entries:
        value = _entry_numeric_value(entry, sort_by)
        if value is None:
            without_value.append(entry)
            continue
        with_value.append((entry, value))
    with_value.sort(key=lambda item: item[1], reverse=descending)
    return [entry for entry, _ in with_value] + without_value


def _entry_numeric_value(entry: UniverseScreeningEntry, sort_by: UniverseScreeningSortField) -> float | None:
    if sort_by == "rank":
        if entry.rank is None:
            return None
        return float(entry.rank)
    if sort_by == "total_score":
        return entry.total_score
    if sort_by == "quality_score":
        return entry.quality_score
    if sort_by == "value_score":
        return entry.value_score
    if sort_by == "growth_score":
        return entry.growth_score
    if sort_by == "risk_score":
        return entry.risk_score
    raise ValueError(f"unsupported sort field: {sort_by}")


def _ticker_fallback_key(entry: UniverseScreeningEntry) -> tuple[bool, str, int]:
    ticker = _normalize_optional_text(entry.ticker)
    return (ticker is None, ticker or "", entry.company_id)


def _ticker_text_key(entry: UniverseScreeningEntry) -> str:
    ticker = _normalize_optional_text(entry.ticker)
    if ticker is None:
        return ""
    return ticker


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return normalized


def _build_universe_screening_csv(entries: list[UniverseScreeningEntry]) -> str:
    records = _build_universe_screening_export_records(entries)
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(_UNIVERSE_SCREENING_EXPORT_COLUMNS),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def _build_universe_screening_excel(entries: list[UniverseScreeningEntry]) -> bytes:
    records = _build_universe_screening_export_records(entries)
    dataframe = pd.DataFrame(records, columns=list(_UNIVERSE_SCREENING_EXPORT_COLUMNS))
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Screening")
    return buffer.getvalue()


def _build_universe_screening_export_records(entries: list[UniverseScreeningEntry]) -> list[dict[str, object]]:
    return [_serialize_universe_screening_entry(entry) for entry in entries]


def _serialize_universe_screening_entry(entry: UniverseScreeningEntry) -> dict[str, object]:
    return {
        "ticker": _export_value(entry.ticker),
        "name": _export_value(entry.name),
        "sector": _export_value(entry.sector),
        "total_score": _export_value(entry.total_score),
        "quality_score": _export_value(entry.quality_score),
        "value_score": _export_value(entry.value_score),
        "growth_score": _export_value(entry.growth_score),
        "risk_score": _export_value(entry.risk_score),
        "rank": _export_value(entry.rank),
        "sector_rank": _export_value(entry.sector_rank),
    }


def _export_value(value: object) -> object:
    if value is None:
        return ""
    return value


def _to_saved_screening_snapshot(snapshot: ScreeningSnapshot) -> SavedScreeningSnapshot:
    if snapshot.created_at is None:
        raise RuntimeError("screening snapshot is missing created_at")
    filters = snapshot.filters if isinstance(snapshot.filters, dict) else {}
    company_ids = snapshot.company_ids if isinstance(snapshot.company_ids, list) else []
    scores = snapshot.scores if isinstance(snapshot.scores, dict) else {}
    company_count = scores.get("company_count")
    if not isinstance(company_count, int):
        company_count = len(company_ids)
    results = _normalize_snapshot_results(scores.get("results"))
    return SavedScreeningSnapshot(
        snapshot_id=snapshot.id,
        name=snapshot.name,
        created_at=snapshot.created_at,
        filters={str(key): value for key, value in filters.items()},
        company_count=company_count,
        company_ids=[company_id for company_id in company_ids if isinstance(company_id, int)],
        results=results,
    )


def _normalize_snapshot_results(raw_results: object) -> list[dict[str, object]]:
    if not isinstance(raw_results, list):
        return []
    normalized: list[dict[str, object]] = []
    for row in raw_results:
        if not isinstance(row, dict):
            continue
        normalized.append({column: row.get(column, "") for column in _UNIVERSE_SCREENING_EXPORT_COLUMNS})
    return normalized
