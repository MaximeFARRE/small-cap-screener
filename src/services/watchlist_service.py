from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.watchlist_entry import WATCHLIST_ALLOWED_STATUSES, WatchlistEntry
from src.repositories import company_repository, watchlist_repository
from src.repositories.database import get_session

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


@dataclass
class WatchlistService:
    session_scope_factory: SessionScopeFactory = get_session

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


def _normalize_status(value: str) -> str:
    return value.strip().lower()
