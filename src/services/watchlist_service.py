from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.models.watchlist_entry import WATCHLIST_ALLOWED_STATUSES, WatchlistEntry
from src.repositories import company_repository, kpi_snapshot_repository, watchlist_repository
from src.repositories.database import get_session
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.scoring_service import RankedCompanyTotalScore, ScoreExplanation, ScoringService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


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
    score_explanation: ScoreExplanation


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
        return CompanyAnalystDetail(
            watchlist_status=watchlist_entry.status if watchlist_entry is not None else None,
            watchlist_notes=watchlist_entry.notes if watchlist_entry is not None else None,
            score_explanation=self.scoring_service.describe_snapshot_score(snapshot),
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


def _normalize_status(value: str) -> str:
    return value.strip().lower()


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
