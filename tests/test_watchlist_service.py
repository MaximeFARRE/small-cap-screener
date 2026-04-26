from __future__ import annotations

from contextlib import contextmanager
from datetime import date

import pytest

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.models.watchlist_entry import (
    WATCHLIST_STATUS_CONVICTION,
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_WATCHING,
    WatchlistEntry,
)
from src.repositories import company_repository, kpi_snapshot_repository, watchlist_repository
from src.services.watchlist_service import AnalystMemo, WatchlistService


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


def test_update_company_exclusion_updates_existing_entry(db_session):
    company = _make_company(db_session, isin="FR0000810006", ticker="WS6.PA")
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=company.id, notes="keep notes", status=WATCHLIST_STATUS_REVIEW),
    )
    service = _make_service(db_session)

    updated = service.update_company_exclusion(company.id, True)

    assert updated is not None
    assert updated.is_excluded is True
    assert updated.notes == "keep notes"
    assert updated.status == WATCHLIST_STATUS_REVIEW
    stored = watchlist_repository.get_by_company_id(db_session, company.id)
    assert stored is not None
    assert stored.is_excluded is True
    assert stored.notes == "keep notes"
    assert stored.status == WATCHLIST_STATUS_REVIEW


def test_update_company_exclusion_creates_entry_when_missing(db_session):
    company = _make_company(db_session, isin="FR0000810007", ticker="WS7.PA")
    service = _make_service(db_session)

    created = service.update_company_exclusion(company.id, True)

    assert created is not None
    assert created.company_id == company.id
    assert created.is_excluded is True
    assert created.notes is None
    assert created.status == WATCHLIST_STATUS_WATCHING


def test_update_company_exclusion_returns_none_for_unknown_company(db_session):
    service = _make_service(db_session)

    result = service.update_company_exclusion(999999, True)

    assert result is None
    assert service.list_entries() == []


def test_update_company_exclusion_can_reintegrate_company(db_session):
    company = _make_company(db_session, isin="FR0000810008", ticker="WS8.PA")
    watchlist_repository.add(
        db_session,
        WatchlistEntry(company_id=company.id, notes="notes", is_excluded=True),
    )
    service = _make_service(db_session)

    updated = service.update_company_exclusion(company.id, False)

    assert updated is not None
    assert updated.is_excluded is False


def test_update_company_memo_creates_entry_when_missing(db_session):
    company = _make_company(db_session, isin="FR0000810009", ticker="WS9.PA")
    service = _make_service(db_session)
    memo = AnalystMemo(
        investment_thesis="structural margin expansion over three years",
        key_risks="execution delay on plant commissioning",
        catalysts="new contract pipeline conversion",
        valuation_notes="discount to sector median EV/EBITDA",
        next_action="reassess after next quarterly release",
    )

    created = service.update_company_memo(company.id, memo)

    assert created is not None
    assert created.company_id == company.id
    assert created.status == WATCHLIST_STATUS_WATCHING
    assert created.notes is None
    assert created.investment_thesis == memo.investment_thesis
    assert created.key_risks == memo.key_risks
    assert created.catalysts == memo.catalysts
    assert created.valuation_notes == memo.valuation_notes
    assert created.next_action == memo.next_action


def test_update_company_memo_updates_existing_entry_without_overwriting_watchlist_fields(db_session):
    company = _make_company(db_session, isin="FR0000810014", ticker="WM1.PA")
    watchlist_repository.add(
        db_session,
        WatchlistEntry(
            company_id=company.id,
            notes="keep base note",
            status=WATCHLIST_STATUS_REVIEW,
            is_excluded=True,
            investment_thesis="old thesis",
        ),
    )
    service = _make_service(db_session)
    memo = AnalystMemo(
        investment_thesis="updated thesis",
        key_risks="updated risks",
        catalysts="updated catalysts",
        valuation_notes="updated valuation",
        next_action="updated action",
    )

    updated = service.update_company_memo(company.id, memo)

    assert updated is not None
    assert updated.notes == "keep base note"
    assert updated.status == WATCHLIST_STATUS_REVIEW
    assert updated.is_excluded is True
    assert updated.investment_thesis == "updated thesis"
    assert updated.key_risks == "updated risks"
    assert updated.catalysts == "updated catalysts"
    assert updated.valuation_notes == "updated valuation"
    assert updated.next_action == "updated action"


def test_get_company_analyst_detail_returns_empty_memo_for_company_without_memo(db_session):
    company = _make_company(db_session, isin="FR0000810015", ticker="WM2.PA")
    service = _make_service(db_session)

    detail = service.get_company_analyst_detail(company.id)

    assert detail.analyst_memo.investment_thesis is None
    assert detail.analyst_memo.key_risks is None
    assert detail.analyst_memo.catalysts is None
    assert detail.analyst_memo.valuation_notes is None
    assert detail.analyst_memo.next_action is None


def test_analyst_memo_persists_after_snapshot_refresh(db_session):
    company = _make_company(db_session, isin="FR0000810016", ticker="WM3.PA")
    service = _make_service(db_session)
    memo = AnalystMemo(
        investment_thesis="long term compounder under-covered by market",
        key_risks="working capital volatility",
        catalysts="margin normalization",
        valuation_notes="target multiple can re-rate",
        next_action="prepare investment committee note",
    )
    service.update_company_memo(company.id, memo)
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=company.id,
            snapshot_date=date(2024, 12, 31),
            metrics={"total_score": 60.0},
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=company.id,
            snapshot_date=date(2025, 1, 31),
            metrics={"total_score": 75.0},
            source="s2",
        ),
    )

    detail = service.get_company_analyst_detail(company.id)

    assert detail.total_score == pytest.approx(75.0)
    assert detail.analyst_memo.investment_thesis == memo.investment_thesis
    assert detail.analyst_memo.key_risks == memo.key_risks
    assert detail.analyst_memo.catalysts == memo.catalysts
    assert detail.analyst_memo.valuation_notes == memo.valuation_notes
    assert detail.analyst_memo.next_action == memo.next_action


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


def test_get_company_analyst_detail_returns_unified_watchlist_and_scoring_data(db_session):
    company = _make_company(db_session, isin="FR0000810100", ticker="DET.PA", name="Detail Co")
    watchlist_repository.add(
        db_session, WatchlistEntry(company_id=company.id, notes="analyst note", status=WATCHLIST_STATUS_REVIEW)
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=company.id,
            snapshot_date=date(2024, 10, 31),
            metrics={
                "quality_score": 81.0,
                "value_score": 74.0,
                "growth_score": 69.0,
                "risk_score": 66.0,
                "total_score": 74.95,
            },
            source="s1",
        ),
    )
    service = _make_service(db_session)

    detail = service.get_company_analyst_detail(company.id)

    assert detail.watchlist_status == WATCHLIST_STATUS_REVIEW
    assert detail.watchlist_notes == "analyst note"
    assert detail.watchlist_is_excluded is False
    assert detail.total_score == pytest.approx(74.95)
    assert detail.quality_score == pytest.approx(81.0)
    assert detail.value_score == pytest.approx(74.0)
    assert detail.growth_score == pytest.approx(69.0)
    assert detail.risk_score == pytest.approx(66.0)
    assert detail.rank == 1
    assert detail.sector_rank == 1
    assert detail.score_explanation.total_score == pytest.approx(74.95)
    assert detail.score_explanation.quality == pytest.approx(81.0)
    assert detail.score_explanation.value == pytest.approx(74.0)
    assert detail.score_explanation.growth == pytest.approx(69.0)
    assert detail.score_explanation.risk == pytest.approx(66.0)
    assert "total 74.95/100" in detail.score_explanation.summary


def test_get_company_analyst_detail_handles_non_scored_company(db_session):
    company = _make_company(db_session, isin="FR0000810101", ticker="MSS.PA", name="Missing Data Co")
    service = _make_service(db_session)

    detail = service.get_company_analyst_detail(company.id)

    assert detail.watchlist_status is None
    assert detail.watchlist_notes is None
    assert detail.watchlist_is_excluded is False
    assert detail.total_score is None
    assert detail.quality_score is None
    assert detail.value_score is None
    assert detail.growth_score is None
    assert detail.risk_score is None
    assert detail.rank is None
    assert detail.sector_rank is None
    assert detail.score_explanation.total_score is None
    assert detail.score_explanation.quality is None
    assert detail.score_explanation.value is None
    assert detail.score_explanation.growth is None
    assert detail.score_explanation.risk is None
    assert detail.score_explanation.summary == "score unavailable: no snapshot data."


def test_get_company_analyst_detail_keeps_excluded_flag_with_scoring_data(db_session):
    company = _make_company(db_session, isin="FR0000810102", ticker="EXC.PA", name="Excluded Co", sector="Tech")
    watchlist_repository.add(
        db_session,
        WatchlistEntry(
            company_id=company.id,
            notes="exclude for governance issue",
            status=WATCHLIST_STATUS_CONVICTION,
            is_excluded=True,
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=company.id,
            snapshot_date=date(2024, 11, 30),
            metrics={
                "quality_score": 70.0,
                "value_score": 72.0,
                "growth_score": 60.0,
                "risk_score": 55.0,
                "total_score": 66.25,
            },
            source="s1",
        ),
    )
    service = _make_service(db_session)

    detail = service.get_company_analyst_detail(company.id)

    assert detail.watchlist_status == WATCHLIST_STATUS_CONVICTION
    assert detail.watchlist_notes == "exclude for governance issue"
    assert detail.watchlist_is_excluded is True
    assert detail.total_score == pytest.approx(66.25)
    assert detail.rank == 1
    assert detail.sector_rank == 1
    assert "total 66.25/100" in detail.score_explanation.summary
