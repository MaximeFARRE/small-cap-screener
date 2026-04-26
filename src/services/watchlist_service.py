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
    watchlist_is_excluded: bool
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
