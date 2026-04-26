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
    "rank",
    "sector_rank",
    "quality_score",
    "value_score",
    "growth_score",
    "risk_score",
    "data_quality_score",
    "last_universe_refresh_at",
    "snapshot_date",
    "watchlist_status",
    "is_excluded",
    "next_review_at",
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
    pe_ratio: float | None = None
    revenue_growth: float | None = None
    operating_margin: float | None = None
    market_cap: float | None = None
    data_quality_score: float | None = None
    last_universe_refresh_at: datetime | None = None
    snapshot_date: date | None = None


@dataclass(frozen=True)
class UniverseScreeningFilters:
    sector: str | None = None
    min_total_score: float | None = None
    min_data_quality_score: float | None = None
    max_pe: float | None = None
    min_growth: float | None = None
    min_margin: float | None = None
    min_market_cap: float | None = None
    max_market_cap: float | None = None
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


@dataclass(frozen=True)
class ScreeningSnapshotSummary:
    snapshot_id: int
    name: str
    created_at: datetime
    company_count: int
    filters: dict[str, object]
    filters_summary: str


@dataclass(frozen=True)
class ScreeningSnapshotRow:
    company_id: int | None
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
class ScreeningSnapshotView:
    summary: ScreeningSnapshotSummary
    rows: list[ScreeningSnapshotRow]


@dataclass(frozen=True)
class ScreeningSnapshotComparisonRow:
    company_id: int | None
    ticker: str | None
    name: str
    sector: str | None
    snapshot_rank: int | None
    current_rank: int | None
    rank_change: int | None
    snapshot_total_score: float | None
    current_total_score: float | None
    total_score_change: float | None


@dataclass(frozen=True)
class ScreeningExportMetadata:
    export_date: datetime
    filters: dict[str, object]
    sort: str
    company_count: int
    scoring_version: str | None


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
        watchlist_entries_by_company_id = self._list_watchlist_entries_by_company_id()
        records = _build_universe_screening_export_records(rows, watchlist_entries_by_company_id)
        return _build_universe_screening_csv(records)

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
        watchlist_entries_by_company_id = self._list_watchlist_entries_by_company_id()
        records = _build_universe_screening_export_records(rows, watchlist_entries_by_company_id)
        metadata = _build_export_metadata(filters=filters, company_count=len(rows))
        return _build_universe_screening_excel(records, metadata)

    def export_watchlist_with_scores_csv(
        self,
        filters: UniverseScreeningFilters | None = None,
        *,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> str:
        target_filters = filters or UniverseScreeningFilters()
        watchlist_filters = _with_watchlist_scope(target_filters)
        rows = self.filter_universe_with_scores(
            watchlist_filters,
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        watchlist_entries_by_company_id = self._list_watchlist_entries_by_company_id()
        records = _build_universe_screening_export_records(rows, watchlist_entries_by_company_id)
        return _build_universe_screening_csv(records)

    def export_watchlist_with_scores_excel(
        self,
        filters: UniverseScreeningFilters | None = None,
        *,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> bytes:
        target_filters = filters or UniverseScreeningFilters()
        watchlist_filters = _with_watchlist_scope(target_filters)
        rows = self.filter_universe_with_scores(
            watchlist_filters,
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        watchlist_entries_by_company_id = self._list_watchlist_entries_by_company_id()
        records = _build_universe_screening_export_records(rows, watchlist_entries_by_company_id)
        metadata = _build_export_metadata(filters=watchlist_filters, company_count=len(rows))
        return _build_universe_screening_excel(records, metadata)

    def export_screening_snapshot_csv(self, snapshot_id: int) -> str:
        snapshot = self.get_screening_snapshot(snapshot_id)
        if snapshot is None:
            return _build_universe_screening_csv([])
        records = _normalize_snapshot_results(snapshot.results)
        return _build_universe_screening_csv(records)

    def export_screening_snapshot_excel(self, snapshot_id: int) -> bytes:
        snapshot = self.get_screening_snapshot(snapshot_id)
        if snapshot is None:
            metadata = _build_export_metadata(filters=UniverseScreeningFilters(), company_count=0)
            return _build_universe_screening_excel([], metadata)
        filters = _filters_from_snapshot_dict(snapshot.filters)
        metadata = _build_export_metadata(filters=filters, company_count=snapshot.company_count)
        records = _normalize_snapshot_results(snapshot.results)
        return _build_universe_screening_excel(records, metadata)

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
        watchlist_entries_by_company_id = self._list_watchlist_entries_by_company_id()
        company_ids = [row.company_id for row in rows]
        results = _build_universe_screening_export_records(rows, watchlist_entries_by_company_id)
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

    def list_recent_screening_snapshots(self, limit: int = 20) -> list[ScreeningSnapshotSummary]:
        with self.session_scope_factory() as session:
            snapshots = screening_snapshot_repository.list_recent(session, limit=limit)
        return [_to_screening_snapshot_summary(_to_saved_screening_snapshot(snapshot)) for snapshot in snapshots]

    def get_screening_snapshot_view(self, snapshot_id: int) -> ScreeningSnapshotView | None:
        snapshot = self.get_screening_snapshot(snapshot_id)
        if snapshot is None:
            return None
        return ScreeningSnapshotView(
            summary=_to_screening_snapshot_summary(snapshot),
            rows=_to_screening_snapshot_rows(snapshot),
        )

    def compare_snapshot_to_current(
        self,
        snapshot_id: int,
        current_filters: UniverseScreeningFilters,
        *,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> list[ScreeningSnapshotComparisonRow]:
        snapshot_view = self.get_screening_snapshot_view(snapshot_id)
        if snapshot_view is None:
            return []
        current_rows = self.filter_universe_with_scores(
            current_filters,
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        return _build_screening_snapshot_comparison_rows(snapshot_view.rows, current_rows)

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
                pe_ratio=_snapshot_metric_as_float(snapshot, "pe_ratio"),
                revenue_growth=_snapshot_metric_as_float(snapshot, "revenue_growth"),
                operating_margin=_snapshot_metric_as_float(snapshot, "operating_margin"),
                market_cap=_snapshot_metric_as_float(snapshot, "market_cap"),
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
        if filters.max_pe is not None:
            if entry.pe_ratio is None or entry.pe_ratio > filters.max_pe:
                continue
        if filters.min_growth is not None:
            if entry.revenue_growth is None or entry.revenue_growth < filters.min_growth:
                continue
        if filters.min_margin is not None:
            if entry.operating_margin is None or entry.operating_margin < filters.min_margin:
                continue
        if filters.min_market_cap is not None:
            if entry.market_cap is None or entry.market_cap < filters.min_market_cap:
                continue
        if filters.max_market_cap is not None:
            if entry.market_cap is None or entry.market_cap > filters.max_market_cap:
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


def _build_universe_screening_csv(records: list[dict[str, object]]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(_UNIVERSE_SCREENING_EXPORT_COLUMNS),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def _build_universe_screening_excel(
    records: list[dict[str, object]],
    metadata: ScreeningExportMetadata,
) -> bytes:
    dataframe = pd.DataFrame(records, columns=list(_UNIVERSE_SCREENING_EXPORT_COLUMNS))
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Screening")
        metadata_rows = _metadata_rows(metadata)
        metadata_frame = pd.DataFrame(metadata_rows, columns=["field", "value"])
        metadata_frame.to_excel(writer, index=False, sheet_name="Metadata")
    return buffer.getvalue()


def _build_universe_screening_export_records(
    entries: list[UniverseScreeningEntry],
    watchlist_entries_by_company_id: dict[int, WatchlistEntry],
) -> list[dict[str, object]]:
    return [
        _serialize_universe_screening_entry(entry, watchlist_entries_by_company_id.get(entry.company_id))
        for entry in entries
    ]


def _serialize_universe_screening_entry(
    entry: UniverseScreeningEntry,
    watchlist_entry: WatchlistEntry | None,
) -> dict[str, object]:
    return {
        "ticker": _export_value(entry.ticker),
        "name": _export_value(entry.name),
        "sector": _export_value(entry.sector),
        "total_score": _export_value(entry.total_score),
        "rank": _export_value(entry.rank),
        "sector_rank": _export_value(entry.sector_rank),
        "quality_score": _export_value(entry.quality_score),
        "value_score": _export_value(entry.value_score),
        "growth_score": _export_value(entry.growth_score),
        "risk_score": _export_value(entry.risk_score),
        "data_quality_score": _export_value(entry.data_quality_score),
        "last_universe_refresh_at": _export_value(entry.last_universe_refresh_at),
        "snapshot_date": _export_value(entry.snapshot_date),
        "watchlist_status": _export_value(watchlist_entry.status if watchlist_entry is not None else None),
        "is_excluded": _export_value(watchlist_entry.is_excluded if watchlist_entry is not None else None),
        "next_review_at": _export_value(watchlist_entry.next_review_at if watchlist_entry is not None else None),
    }


def _export_value(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _with_watchlist_scope(filters: UniverseScreeningFilters) -> UniverseScreeningFilters:
    return UniverseScreeningFilters(
        sector=filters.sector,
        min_total_score=filters.min_total_score,
        min_data_quality_score=filters.min_data_quality_score,
        max_pe=filters.max_pe,
        min_growth=filters.min_growth,
        min_margin=filters.min_margin,
        min_market_cap=filters.min_market_cap,
        max_market_cap=filters.max_market_cap,
        stale_only=filters.stale_only,
        scored_only=filters.scored_only,
        watchlist_scope="watchlist_only",
        watchlist_status=filters.watchlist_status,
        exclusion_filter=filters.exclusion_filter,
        include_excluded=filters.include_excluded,
        top_n=filters.top_n,
        sort_by=filters.sort_by,
        descending=filters.descending,
    )


def _build_export_metadata(*, filters: UniverseScreeningFilters, company_count: int) -> ScreeningExportMetadata:
    sort_direction = "desc" if filters.descending else "asc"
    sort_text = f"{filters.sort_by} {sort_direction}"
    return ScreeningExportMetadata(
        export_date=datetime.now(UTC),
        filters=asdict(filters),
        sort=sort_text,
        company_count=company_count,
        scoring_version=None,
    )


def _metadata_rows(metadata: ScreeningExportMetadata) -> list[dict[str, str]]:
    return [
        {"field": "export_date", "value": metadata.export_date.isoformat()},
        {"field": "active_filters", "value": _format_snapshot_filters_summary(metadata.filters)},
        {"field": "active_sort", "value": metadata.sort},
        {"field": "company_count", "value": str(metadata.company_count)},
        {"field": "scoring_version", "value": metadata.scoring_version or "N/A"},
    ]


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


def _filters_from_snapshot_dict(raw_filters: dict[str, object]) -> UniverseScreeningFilters:
    sort_by = _row_text(raw_filters.get("sort_by")) or "rank"
    if sort_by not in ("rank", "total_score", "quality_score", "value_score", "growth_score", "risk_score", "ticker"):
        sort_by = "rank"
    watchlist_scope = _row_text(raw_filters.get("watchlist_scope")) or "all"
    if watchlist_scope not in ("all", "watchlist_only", "non_watchlist_only"):
        watchlist_scope = "all"
    exclusion_filter = _row_text(raw_filters.get("exclusion_filter"))
    if exclusion_filter not in ("all", "excluded_only", "non_excluded_only"):
        exclusion_filter = None
    return UniverseScreeningFilters(
        sector=_row_text(raw_filters.get("sector")),
        min_total_score=_row_float(raw_filters.get("min_total_score")),
        min_data_quality_score=_row_float(raw_filters.get("min_data_quality_score")),
        stale_only=raw_filters.get("stale_only") is True,
        scored_only=raw_filters.get("scored_only") is True,
        watchlist_scope=watchlist_scope,
        watchlist_status=_row_text(raw_filters.get("watchlist_status")),
        exclusion_filter=exclusion_filter,
        include_excluded=raw_filters.get("include_excluded") is True,
        top_n=_row_int(raw_filters.get("top_n")),
        sort_by=sort_by,
        descending=raw_filters.get("descending") is True,
    )


def _to_screening_snapshot_summary(snapshot: SavedScreeningSnapshot) -> ScreeningSnapshotSummary:
    return ScreeningSnapshotSummary(
        snapshot_id=snapshot.snapshot_id,
        name=snapshot.name,
        created_at=snapshot.created_at,
        company_count=snapshot.company_count,
        filters=snapshot.filters,
        filters_summary=_format_snapshot_filters_summary(snapshot.filters),
    )


def _to_screening_snapshot_rows(snapshot: SavedScreeningSnapshot) -> list[ScreeningSnapshotRow]:
    rows: list[ScreeningSnapshotRow] = []
    for index, raw_row in enumerate(snapshot.results):
        company_id = snapshot.company_ids[index] if index < len(snapshot.company_ids) else None
        rows.append(
            ScreeningSnapshotRow(
                company_id=company_id,
                ticker=_row_text(raw_row.get("ticker")),
                name=_row_text(raw_row.get("name")) or "",
                sector=_row_text(raw_row.get("sector")),
                total_score=_row_float(raw_row.get("total_score")),
                quality_score=_row_float(raw_row.get("quality_score")),
                value_score=_row_float(raw_row.get("value_score")),
                growth_score=_row_float(raw_row.get("growth_score")),
                risk_score=_row_float(raw_row.get("risk_score")),
                rank=_row_int(raw_row.get("rank")),
                sector_rank=_row_int(raw_row.get("sector_rank")),
            )
        )
    return rows


def _build_screening_snapshot_comparison_rows(
    snapshot_rows: list[ScreeningSnapshotRow],
    current_rows: list[UniverseScreeningEntry],
) -> list[ScreeningSnapshotComparisonRow]:
    snapshot_by_key = {_comparison_key(row.company_id, row.ticker): row for row in snapshot_rows}
    current_by_key = {_comparison_key(row.company_id, row.ticker): row for row in current_rows}
    keys = set(snapshot_by_key) | set(current_by_key)
    comparisons: list[ScreeningSnapshotComparisonRow] = []
    for key in keys:
        snapshot_row = snapshot_by_key.get(key)
        current_row = current_by_key.get(key)
        company_id = current_row.company_id if current_row is not None else None
        if company_id is None and snapshot_row is not None:
            company_id = snapshot_row.company_id
        ticker = current_row.ticker if current_row is not None else None
        if ticker is None and snapshot_row is not None:
            ticker = snapshot_row.ticker
        name = current_row.name if current_row is not None else ""
        if not name and snapshot_row is not None:
            name = snapshot_row.name
        sector = current_row.sector if current_row is not None else None
        if sector is None and snapshot_row is not None:
            sector = snapshot_row.sector
        snapshot_rank = snapshot_row.rank if snapshot_row is not None else None
        current_rank = current_row.rank if current_row is not None else None
        snapshot_total_score = snapshot_row.total_score if snapshot_row is not None else None
        current_total_score = current_row.total_score if current_row is not None else None
        comparisons.append(
            ScreeningSnapshotComparisonRow(
                company_id=company_id,
                ticker=ticker,
                name=name,
                sector=sector,
                snapshot_rank=snapshot_rank,
                current_rank=current_rank,
                rank_change=_rank_change(snapshot_rank, current_rank),
                snapshot_total_score=snapshot_total_score,
                current_total_score=current_total_score,
                total_score_change=_score_change(snapshot_total_score, current_total_score),
            )
        )
    comparisons.sort(key=_comparison_sort_key)
    return comparisons


def _comparison_key(company_id: int | None, ticker: str | None) -> tuple[str, str]:
    if company_id is not None:
        return ("company_id", str(company_id))
    normalized_ticker = _normalize_optional_text(ticker)
    if normalized_ticker is not None:
        return ("ticker", normalized_ticker)
    return ("ticker", "")


def _comparison_sort_key(row: ScreeningSnapshotComparisonRow) -> tuple[bool, int, bool, int, str]:
    current_rank = row.current_rank if row.current_rank is not None else 10**9
    snapshot_rank = row.snapshot_rank if row.snapshot_rank is not None else 10**9
    ticker = _normalize_optional_text(row.ticker) or ""
    return (row.current_rank is None, current_rank, row.snapshot_rank is None, snapshot_rank, ticker)


def _rank_change(snapshot_rank: int | None, current_rank: int | None) -> int | None:
    if snapshot_rank is None or current_rank is None:
        return None
    return snapshot_rank - current_rank


def _score_change(snapshot_score: float | None, current_score: float | None) -> float | None:
    if snapshot_score is None or current_score is None:
        return None
    return current_score - snapshot_score


def _row_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _row_float(value: object) -> float | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _row_int(value: object) -> int | None:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_snapshot_filters_summary(filters: dict[str, object]) -> str:
    parts: list[str] = []
    if _row_text(filters.get("sector")) is not None:
        parts.append(f"sector={filters['sector']}")
    if _row_float(filters.get("min_total_score")) is not None:
        parts.append(f"min score={_row_float(filters.get('min_total_score')):.2f}")
    if _row_float(filters.get("min_data_quality_score")) is not None:
        parts.append(f"min quality={_row_float(filters.get('min_data_quality_score')):.2f}")
    if filters.get("stale_only") is True:
        parts.append("stale only")
    if filters.get("scored_only") is True:
        parts.append("scored only")
    if _row_text(filters.get("watchlist_scope")) not in (None, "all"):
        parts.append(f"watchlist={filters['watchlist_scope']}")
    if _row_text(filters.get("watchlist_status")) is not None:
        parts.append(f"status={filters['watchlist_status']}")
    if _row_text(filters.get("exclusion_filter")) not in (None, "all"):
        parts.append(f"exclusion={filters['exclusion_filter']}")
    if filters.get("include_excluded") is True:
        parts.append("include excluded")
    if _row_int(filters.get("top_n")) is not None:
        parts.append(f"top_n={_row_int(filters.get('top_n'))}")
    sort_by = _row_text(filters.get("sort_by"))
    if sort_by is not None:
        order = "desc" if filters.get("descending") is True else "asc"
        parts.append(f"sort={sort_by} {order}")
    if not parts:
        return "default filters"
    return ", ".join(parts)
