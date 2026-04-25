from __future__ import annotations

from contextlib import contextmanager

from src.models.company import Company
from src.models.watchlist_entry import WatchlistEntry
from src.repositories import company_repository, watchlist_repository
from src.services.watchlist_service import WatchlistService


def _make_service(db_session) -> WatchlistService:
    @contextmanager
    def session_scope():
        yield db_session

    return WatchlistService(session_scope_factory=session_scope)


def _make_company(db_session, *, isin: str, ticker: str) -> Company:
    return company_repository.create(
        db_session,
        Company(
            isin=isin,
            ticker=ticker,
            name=ticker,
            currency="EUR",
        ),
    )


def test_update_company_notes_updates_existing_entry(db_session):
    company = _make_company(db_session, isin="FR0000810001", ticker="WS1.PA")
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=company.id, notes="initial note"),
    )
    service = _make_service(db_session)

    updated = service.update_company_notes(company.id, "updated note")

    assert updated is not None
    assert updated.notes == "updated note"
    stored = watchlist_repository.get_by_company_id(db_session, company.id)
    assert stored is not None
    assert stored.notes == "updated note"


def test_update_company_notes_creates_entry_when_missing(db_session):
    company = _make_company(db_session, isin="FR0000810002", ticker="WS2.PA")
    service = _make_service(db_session)

    created = service.update_company_notes(company.id, "new analyst note")

    assert created is not None
    assert created.company_id == company.id
    assert created.notes == "new analyst note"
    listed = service.list_entries()
    assert [entry.company_id for entry in listed] == [company.id]


def test_update_company_notes_returns_none_for_unknown_company(db_session):
    service = _make_service(db_session)

    result = service.update_company_notes(999999, "unused")

    assert result is None
    assert service.list_entries() == []
