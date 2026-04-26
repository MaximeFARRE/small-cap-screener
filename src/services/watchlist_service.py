from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.models.watchlist_entry import WATCHLIST_ALLOWED_STATUSES, WatchlistEntry
from src.repositories import company_repository, kpi_snapshot_repository, watchlist_repository
from src.repositories.database import get_session
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.scoring_service import RankedCompanyTotalScore, ScoreExplanation, ScoringService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_MEMO_SUMMARY_MAX_LEN = 180


@dataclass(frozen=True)
class WatchlistEntryWithScore:
    company_id: int
    ticker: str | None
    name: str
    status: str
    notes: str | None
    total_score: float | None
    rank: int | None
    sector_rank: int | None


@dataclass(frozen=True)
class CompanyAnalystDetail:
    watchlist_status: str | None
    watchlist_notes: str | None
    watchlist_is_excluded: bool
    next_review_at: datetime | None
    analyst_memo: AnalystMemo
    quality_score: float | None
    value_score: float | None
    growth_score: float | None
    risk_score: float | None
    total_score: float | None
    rank: int | None
    sector_rank: int | None
    score_explanation: ScoreExplanation


@dataclass(frozen=True)
class AnalystMemo:
    investment_thesis: str | None = None
    key_risks: str | None = None
    catalysts: str | None = None
    valuation_notes: str | None = None
    next_action: str | None = None


@dataclass(frozen=True)
class WatchlistWorkflowEntry:
    company_id: int
    ticker: str | None
    name: str
    status: str
    notes: str | None
    memo_summary: str | None
    is_excluded: bool
    total_score: float | None
    rank: int | None
    sector_rank: int | None
    data_quality_score: float | None
    last_universe_refresh_at: datetime | None
    next_review_at: datetime | None


@dataclass(frozen=True)
class WatchlistActionQueue:
    overdue_reviews: list[WatchlistWorkflowEntry]
    high_priority_statuses: list[WatchlistWorkflowEntry]


@dataclass
class WatchlistService:
    session_scope_factory: SessionScopeFactory = get_session
    scoring_service: ScoringService = field(default_factory=ScoringService)
    kpi_snapshot_service: KpiSnapshotService | None = None

    def __post_init__(self) -> None:
        if self.kpi_snapshot_service is None:
            self.kpi_snapshot_service = KpiSnapshotService(
                session_scope_factory=self.session_scope_factory,
                scoring_service=self.scoring_service,
            )

    def add_company(self, company_id: int, notes: str | None = None) -> WatchlistEntry | None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                return None

            existing = watchlist_repository.get_by_company_id(session, company_id)
            if existing is not None:
                existing.notes = notes
                session.flush()
                return existing

            return watchlist_repository.add(
                session,
                WatchlistEntry(
                    company_id=company_id,
                    notes=notes,
                ),
            )

    def remove_company(self, company_id: int) -> bool:
        with self.session_scope_factory() as session:
            return watchlist_repository.remove_by_company_id(session, company_id)

    def list_entries(self) -> list[WatchlistEntry]:
        with self.session_scope_factory() as session:
            return watchlist_repository.list_all(session)

    def get_company_analyst_detail(self, company_id: int) -> CompanyAnalystDetail:
        with self.session_scope_factory() as session:
            watchlist_entry = watchlist_repository.get_by_company_id(session, company_id)
            snapshot = kpi_snapshot_repository.get_latest_by_company(session, company_id)
        if self.kpi_snapshot_service is None:
            raise RuntimeError("kpi snapshot service is not initialized")
        ranking = self.kpi_snapshot_service.rank_universe_by_total_score()
        ranking_entry = next((item for item in ranking if item.company_id == company_id), None)
        explanation = self.scoring_service.describe_snapshot_score(snapshot)
        return CompanyAnalystDetail(
            watchlist_status=watchlist_entry.status if watchlist_entry is not None else None,
            watchlist_notes=watchlist_entry.notes if watchlist_entry is not None else None,
            watchlist_is_excluded=watchlist_entry.is_excluded if watchlist_entry is not None else False,
            next_review_at=watchlist_entry.next_review_at if watchlist_entry is not None else None,
            analyst_memo=_memo_from_entry(watchlist_entry),
            quality_score=explanation.quality,
            value_score=explanation.value,
            growth_score=explanation.growth,
            risk_score=explanation.risk,
            total_score=explanation.total_score,
            rank=ranking_entry.rank if ranking_entry is not None else None,
            sector_rank=ranking_entry.sector_rank if ranking_entry is not None else None,
            score_explanation=explanation,
        )

    def update_company_notes(self, company_id: int, notes: str | None) -> WatchlistEntry | None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                return None

            updated = watchlist_repository.update_notes_by_company_id(session, company_id, notes)
            if updated is not None:
                return updated

            return watchlist_repository.add(
                session,
                WatchlistEntry(
                    company_id=company_id,
                    notes=notes,
                ),
            )

    def update_company_status(self, company_id: int, status: str) -> WatchlistEntry | None:
        normalized_status = _normalize_status(status)
        if normalized_status not in WATCHLIST_ALLOWED_STATUSES:
            raise ValueError(f"invalid watchlist status: {status}")

        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                return None

            updated = watchlist_repository.update_status_by_company_id(session, company_id, normalized_status)
            if updated is not None:
                return updated

            return watchlist_repository.add(
                session,
                WatchlistEntry(
                    company_id=company_id,
                    status=normalized_status,
                ),
            )

    def update_company_exclusion(self, company_id: int, is_excluded: bool) -> WatchlistEntry | None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                return None

            updated = watchlist_repository.update_excluded_by_company_id(session, company_id, is_excluded)
            if updated is not None:
                return updated

            return watchlist_repository.add(
                session,
                WatchlistEntry(
                    company_id=company_id,
                    is_excluded=is_excluded,
                ),
            )

    def update_company_memo(self, company_id: int, memo: AnalystMemo) -> WatchlistEntry | None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                return None

            normalized_memo = _normalize_memo(memo)
            updated = watchlist_repository.update_memo_by_company_id(
                session,
                company_id,
                investment_thesis=normalized_memo.investment_thesis,
                key_risks=normalized_memo.key_risks,
                catalysts=normalized_memo.catalysts,
                valuation_notes=normalized_memo.valuation_notes,
                next_action=normalized_memo.next_action,
            )
            if updated is not None:
                return updated

            return watchlist_repository.add(
                session,
                WatchlistEntry(
                    company_id=company_id,
                    investment_thesis=normalized_memo.investment_thesis,
                    key_risks=normalized_memo.key_risks,
                    catalysts=normalized_memo.catalysts,
                    valuation_notes=normalized_memo.valuation_notes,
                    next_action=normalized_memo.next_action,
                ),
            )

    def update_company_next_review(self, company_id: int, next_review_at: datetime | None) -> WatchlistEntry | None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                return None

            updated = watchlist_repository.update_next_review_by_company_id(session, company_id, next_review_at)
            if updated is not None:
                return updated

            return watchlist_repository.add(
                session,
                WatchlistEntry(
                    company_id=company_id,
                    next_review_at=next_review_at,
                ),
            )

    def list_watchlist_with_scores(
        self,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> list[WatchlistEntryWithScore]:
        with self.session_scope_factory() as session:
            entries = watchlist_repository.list_all(session)
            companies_by_id = {
                entry.company_id: company_repository.get_by_id(session, entry.company_id) for entry in entries
            }
            total_scores_by_company_id = {
                entry.company_id: self.scoring_service.get_snapshot_total_score(
                    kpi_snapshot_repository.get_latest_by_company(session, entry.company_id)
                )
                for entry in entries
            }

        if self.kpi_snapshot_service is None:
            raise RuntimeError("kpi snapshot service is not initialized")
        ranking = self.kpi_snapshot_service.rank_universe_by_total_score(
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        ranking_by_company_id = {item.company_id: item for item in ranking}

        return _build_watchlist_with_scores(
            entries=entries,
            companies_by_id=companies_by_id,
            total_scores_by_company_id=total_scores_by_company_id,
            ranking_by_company_id=ranking_by_company_id,
        )

    def list_watchlist_workflow(
        self,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> list[WatchlistWorkflowEntry]:
        with self.session_scope_factory() as session:
            entries = watchlist_repository.list_all(session)
            companies_by_id = {
                entry.company_id: company_repository.get_by_id(session, entry.company_id) for entry in entries
            }
            snapshots_by_company_id = {
                entry.company_id: kpi_snapshot_repository.get_latest_by_company(session, entry.company_id)
                for entry in entries
            }

        ranking_by_company_id = _ranking_by_company_id(
            self,
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        return _build_watchlist_workflow_entries(
            entries=entries,
            companies_by_id=companies_by_id,
            snapshots_by_company_id=snapshots_by_company_id,
            ranking_by_company_id=ranking_by_company_id,
        )

    def list_action_queue(
        self,
        *,
        reference_time: datetime | None = None,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> WatchlistActionQueue:
        workflow_entries = self.list_watchlist_workflow(
            max_market_cap=max_market_cap,
            min_average_daily_volume=min_average_daily_volume,
            country=country,
        )
        now = reference_time if reference_time is not None else datetime.now(UTC)
        overdue_reviews = [entry for entry in workflow_entries if _is_overdue_review(entry.next_review_at, now)]
        overdue_reviews.sort(
            key=lambda item: (_as_utc(item.next_review_at) if item.next_review_at else now, item.company_id)
        )
        high_priority_statuses = [entry for entry in workflow_entries if entry.status in ("review", "conviction")]
        high_priority_statuses.sort(key=lambda item: (_status_priority(item.status), item.company_id))
        return WatchlistActionQueue(
            overdue_reviews=overdue_reviews,
            high_priority_statuses=high_priority_statuses,
        )


def _normalize_status(value: str) -> str:
    return value.strip().lower()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _normalize_memo(memo: AnalystMemo) -> AnalystMemo:
    return AnalystMemo(
        investment_thesis=_normalize_optional_text(memo.investment_thesis),
        key_risks=_normalize_optional_text(memo.key_risks),
        catalysts=_normalize_optional_text(memo.catalysts),
        valuation_notes=_normalize_optional_text(memo.valuation_notes),
        next_action=_normalize_optional_text(memo.next_action),
    )


def _memo_from_entry(entry: WatchlistEntry | None) -> AnalystMemo:
    if entry is None:
        return AnalystMemo()
    return AnalystMemo(
        investment_thesis=entry.investment_thesis,
        key_risks=entry.key_risks,
        catalysts=entry.catalysts,
        valuation_notes=entry.valuation_notes,
        next_action=entry.next_action,
    )


def _memo_summary(memo: AnalystMemo) -> str | None:
    snippets = [
        _normalize_optional_text(memo.investment_thesis),
        _normalize_optional_text(memo.key_risks),
        _normalize_optional_text(memo.catalysts),
        _normalize_optional_text(memo.valuation_notes),
        _normalize_optional_text(memo.next_action),
    ]
    available = [snippet for snippet in snippets if snippet is not None]
    if not available:
        return None
    summary = " | ".join(available)
    if len(summary) <= _MEMO_SUMMARY_MAX_LEN:
        return summary
    return summary[: _MEMO_SUMMARY_MAX_LEN - 3] + "..."


def _ranking_by_company_id(
    service: WatchlistService,
    *,
    max_market_cap: float | None,
    min_average_daily_volume: float | None,
    country: str | None,
) -> dict[int, RankedCompanyTotalScore]:
    if service.kpi_snapshot_service is None:
        raise RuntimeError("kpi snapshot service is not initialized")
    ranking = service.kpi_snapshot_service.rank_universe_by_total_score(
        max_market_cap=max_market_cap,
        min_average_daily_volume=min_average_daily_volume,
        country=country,
    )
    return {item.company_id: item for item in ranking}


def _build_watchlist_workflow_entries(
    *,
    entries: list[WatchlistEntry],
    companies_by_id: dict[int, object],
    snapshots_by_company_id: dict[int, object],
    ranking_by_company_id: dict[int, RankedCompanyTotalScore],
) -> list[WatchlistWorkflowEntry]:
    workflow: list[WatchlistWorkflowEntry] = []
    for entry in entries:
        company = companies_by_id.get(entry.company_id)
        snapshot = snapshots_by_company_id.get(entry.company_id)
        ranking = ranking_by_company_id.get(entry.company_id)
        memo = _memo_from_entry(entry)
        workflow.append(
            WatchlistWorkflowEntry(
                company_id=entry.company_id,
                ticker=company.ticker if company is not None else None,
                name=company.name if company is not None else "",
                status=entry.status,
                notes=entry.notes,
                memo_summary=_memo_summary(memo),
                is_excluded=entry.is_excluded,
                total_score=_snapshot_metric_as_float(snapshot, "total_score"),
                rank=ranking.rank if ranking is not None else None,
                sector_rank=ranking.sector_rank if ranking is not None else None,
                data_quality_score=_snapshot_metric_as_float(snapshot, "data_quality_score"),
                last_universe_refresh_at=company.last_universe_refresh_at if company is not None else None,
                next_review_at=entry.next_review_at,
            )
        )
    return workflow


def _snapshot_metric_as_float(snapshot: object, key: str) -> float | None:
    if snapshot is None:
        return None
    metrics = getattr(snapshot, "metrics", None)
    if not isinstance(metrics, dict):
        return None
    value = metrics.get(key)
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_overdue_review(next_review_at: datetime | None, reference_time: datetime) -> bool:
    if next_review_at is None:
        return False
    left = _as_utc(next_review_at)
    right = _as_utc(reference_time)
    return left <= right


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _status_priority(status: str) -> int:
    if status == "review":
        return 0
    if status == "conviction":
        return 1
    return 2


def _build_watchlist_with_scores(
    *,
    entries: list[WatchlistEntry],
    companies_by_id: dict[int, object],
    total_scores_by_company_id: dict[int, float | None],
    ranking_by_company_id: dict[int, RankedCompanyTotalScore],
) -> list[WatchlistEntryWithScore]:
    enriched: list[WatchlistEntryWithScore] = []
    for entry in entries:
        company = companies_by_id.get(entry.company_id)
        ranking = ranking_by_company_id.get(entry.company_id)
        enriched.append(
            WatchlistEntryWithScore(
                company_id=entry.company_id,
                ticker=company.ticker if company is not None else None,
                name=company.name if company is not None else "",
                status=entry.status,
                notes=entry.notes,
                total_score=total_scores_by_company_id.get(entry.company_id),
                rank=ranking.rank if ranking is not None else None,
                sector_rank=ranking.sector_rank if ranking is not None else None,
            )
        )
    return enriched
