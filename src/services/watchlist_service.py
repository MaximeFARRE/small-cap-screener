from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.watchlist_entry import WatchlistEntry
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
