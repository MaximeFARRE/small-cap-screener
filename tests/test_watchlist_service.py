from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.models.watchlist_entry import WATCHLIST_STATUS_CONVICTION, WATCHLIST_STATUS_REVIEW, WatchlistEntry
from src.repositories import company_repository, kpi_snapshot_repository, watchlist_repository
from src.services.watchlist_service import WatchlistService


def _make_service(db_session) -> WatchlistService:
    @contextmanager
    def session_scope():
        yield db_session

    return WatchlistService(session_scope_factory=session_scope)


def _make_company(
    db_session,
    *,
    isin: str,
    ticker: str,
    name: str | None = None,
    sector: str | None = "Energy",
    market_cap: float = 200_000_000.0,
) -> Company:
    return company_repository.create(
        db_session,
        Company(
            isin=isin,
            ticker=ticker,
            name=ticker if name is None else name,
            currency="EUR",
            country="France",
            sector=sector,
            is_active=True,
            market_cap=market_cap,
            average_daily_volume=150_000.0,
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


def test_update_company_status_updates_existing_entry(db_session):
    company = _make_company(db_session, isin="FR0000810003", ticker="WS3.PA")
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=company.id, notes="status test"),
    )
    service = _make_service(db_session)

    updated = service.update_company_status(company.id, WATCHLIST_STATUS_REVIEW)

    assert updated is not None
    assert updated.status == WATCHLIST_STATUS_REVIEW
    stored = watchlist_repository.get_by_company_id(db_session, company.id)
    assert stored is not None
    assert stored.status == WATCHLIST_STATUS_REVIEW


def test_update_company_status_creates_entry_when_missing(db_session):
    company = _make_company(db_session, isin="FR0000810004", ticker="WS4.PA")
    service = _make_service(db_session)

    created = service.update_company_status(company.id, WATCHLIST_STATUS_CONVICTION)

    assert created is not None
    assert created.company_id == company.id
    assert created.status == WATCHLIST_STATUS_CONVICTION
    assert created.notes is None


def test_update_company_status_returns_none_for_unknown_company(db_session):
    service = _make_service(db_session)

    result = service.update_company_status(999999, WATCHLIST_STATUS_REVIEW)

    assert result is None
    assert service.list_entries() == []


def test_update_company_status_rejects_invalid_status(db_session):
    company = _make_company(db_session, isin="FR0000810005", ticker="WS5.PA")
    service = _make_service(db_session)

    with pytest.raises(ValueError):
        service.update_company_status(company.id, "invalid")


def test_list_watchlist_with_scores_reuses_global_ranking(db_session):
    hidden_top = _make_company(
        db_session,
        isin="FR0000810010",
        ticker="TOP.PA",
        name="Top Co",
        sector="Energy",
    )
    watch_energy = _make_company(
        db_session,
        isin="FR0000810011",
        ticker="ENR.PA",
        name="Energy Co",
        sector="Energy",
    )
    watch_tech = _make_company(
        db_session,
        isin="FR0000810012",
        ticker="TEC.PA",
        name="Tech Co",
        sector="Tech",
    )
    watch_no_score = _make_company(
        db_session,
        isin="FR0000810013",
        ticker="NOS.PA",
        name="No Score Co",
        sector="Energy",
    )

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=hidden_top.id,
            snapshot_date=date(2024, 9, 30),
            metrics={"total_score": 95.0},
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=watch_energy.id,
            snapshot_date=date(2024, 9, 30),
            metrics={"total_score": 90.0},
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=watch_tech.id,
            snapshot_date=date(2024, 9, 30),
            metrics={"total_score": 70.0},
            source="s1",
        ),
    )

    service = _make_service(db_session)
    service.add_company(watch_energy.id, notes="energy note")
    service.add_company(watch_tech.id, notes="tech note")
    service.add_company(watch_no_score.id, notes="no score note")
    service.update_company_status(watch_tech.id, WATCHLIST_STATUS_REVIEW)

    listed = service.list_watchlist_with_scores()
    by_company_id = {entry.company_id: entry for entry in listed}

    assert set(by_company_id) == {watch_energy.id, watch_tech.id, watch_no_score.id}

    energy_entry = by_company_id[watch_energy.id]
    assert energy_entry.ticker == "ENR.PA"
    assert energy_entry.name == "Energy Co"
    assert energy_entry.status == "watching"
    assert energy_entry.notes == "energy note"
    assert energy_entry.total_score == pytest.approx(90.0)
    assert energy_entry.rank == 2
    assert energy_entry.sector_rank == 2

    tech_entry = by_company_id[watch_tech.id]
    assert tech_entry.ticker == "TEC.PA"
    assert tech_entry.name == "Tech Co"
    assert tech_entry.status == WATCHLIST_STATUS_REVIEW
    assert tech_entry.notes == "tech note"
    assert tech_entry.total_score == pytest.approx(70.0)
    assert tech_entry.rank == 3
    assert tech_entry.sector_rank == 1

    no_score_entry = by_company_id[watch_no_score.id]
    assert no_score_entry.ticker == "NOS.PA"
    assert no_score_entry.name == "No Score Co"
    assert no_score_entry.notes == "no score note"
    assert no_score_entry.total_score is None
    assert no_score_entry.rank is None
    assert no_score_entry.sector_rank is None
