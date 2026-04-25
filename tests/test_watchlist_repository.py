from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.company import Company
from src.models.watchlist_entry import (
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_WATCHING,
    WatchlistEntry,
)
from src.repositories import company_repository, watchlist_repository


def _make_company(session, *, isin: str, ticker: str) -> Company:
    return company_repository.create(
        session,
        Company(
            isin=isin,
            ticker=ticker,
            name=ticker,
            currency="EUR",
        ),
    )


def _make_entry(
    company_id: int,
    *,
    notes: str | None = "analyst note",
    status: str | None = None,
    added_at: datetime | None = None,
) -> WatchlistEntry:
    kwargs: dict[str, object] = {"company_id": company_id, "notes": notes}
    if status is not None:
        kwargs["status"] = status
    if added_at is not None:
        kwargs["added_at"] = added_at
    return WatchlistEntry(**kwargs)


def test_add_and_get_by_company_id(db_session):
    company = _make_company(db_session, isin="FR0000800001", ticker="WL1.PA")
    added = watchlist_repository.add(db_session, _make_entry(company.id, notes="watch earnings"))

    fetched = watchlist_repository.get_by_company_id(db_session, company.id)

    assert fetched is not None
    assert fetched.id == added.id
    assert fetched.notes == "watch earnings"
    assert fetched.status == WATCHLIST_STATUS_WATCHING


def test_list_all_ordered_by_added_at_desc(db_session):
    company_a = _make_company(db_session, isin="FR0000800002", ticker="WLA.PA")
    company_b = _make_company(db_session, isin="FR0000800003", ticker="WLB.PA")

    watchlist_repository.add(
        db_session,
        _make_entry(company_a.id, added_at=datetime(2024, 1, 1, 10, 0, 0)),
    )
    watchlist_repository.add(
        db_session,
        _make_entry(company_b.id, added_at=datetime(2024, 2, 1, 10, 0, 0)),
    )

    listed = watchlist_repository.list_all(db_session)

    assert [entry.company_id for entry in listed] == [company_b.id, company_a.id]


def test_remove_by_company_id(db_session):
    company = _make_company(db_session, isin="FR0000800004", ticker="WL4.PA")
    watchlist_repository.add(db_session, _make_entry(company.id))

    removed = watchlist_repository.remove_by_company_id(db_session, company.id)

    assert removed is True
    assert watchlist_repository.get_by_company_id(db_session, company.id) is None


def test_remove_by_company_id_nonexistent(db_session):
    assert watchlist_repository.remove_by_company_id(db_session, 999999) is False


def test_update_notes_by_company_id(db_session):
    company = _make_company(db_session, isin="FR0000800006", ticker="WL6.PA")
    watchlist_repository.add(db_session, _make_entry(company.id, notes="initial"))

    updated = watchlist_repository.update_notes_by_company_id(db_session, company.id, "updated note")

    assert updated is not None
    assert updated.notes == "updated note"
    stored = watchlist_repository.get_by_company_id(db_session, company.id)
    assert stored is not None
    assert stored.notes == "updated note"


def test_update_notes_by_company_id_nonexistent(db_session):
    assert watchlist_repository.update_notes_by_company_id(db_session, 999999, "new note") is None


def test_update_status_by_company_id(db_session):
    company = _make_company(db_session, isin="FR0000800007", ticker="WL7.PA")
    watchlist_repository.add(db_session, _make_entry(company.id))

    updated = watchlist_repository.update_status_by_company_id(db_session, company.id, WATCHLIST_STATUS_REVIEW)

    assert updated is not None
    assert updated.status == WATCHLIST_STATUS_REVIEW
    stored = watchlist_repository.get_by_company_id(db_session, company.id)
    assert stored is not None
    assert stored.status == WATCHLIST_STATUS_REVIEW


def test_update_status_by_company_id_nonexistent(db_session):
    assert watchlist_repository.update_status_by_company_id(db_session, 999999, WATCHLIST_STATUS_REVIEW) is None


def test_unique_constraint_company_id(db_session):
    company = _make_company(db_session, isin="FR0000800005", ticker="WL5.PA")
    watchlist_repository.add(db_session, _make_entry(company.id, notes="first"))

    with pytest.raises(IntegrityError):
        watchlist_repository.add(db_session, _make_entry(company.id, notes="duplicate"))
    db_session.rollback()
