from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.kpi_snapshot import KpiSnapshot
from src.models.price_history import PriceHistory
from src.repositories import (
    company_repository,
    financial_statement_repository,
    kpi_snapshot_repository,
    price_history_repository,
)
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.ratio_service import RatioService
from src.services.scoring_service import (
    GROWTH_SCORE_KEY,
    QUALITY_SCORE_KEY,
    RISK_SCORE_KEY,
    TOTAL_SCORE_KEY,
    VALUE_SCORE_KEY,
)


def _make_service(db_session):
    @contextmanager
    def session_scope():
        yield db_session

    return KpiSnapshotService(session_scope_factory=session_scope)


def _create_company_with_financials(db_session, isin: str = "FR0000120271", ticker: str = "TTE.PA") -> Company:
    company = company_repository.create(
        db_session,
        Company(
            isin=isin,
            ticker=ticker,
            name="TotalEnergies",
            country="France",
            sector="Energy",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=200_000.0,
        ),
    )
    financial_statement_repository.create(
        db_session,
        FinancialStatement(
            company_id=company.id,
            fiscal_year=2023,
            period_type=PeriodType.ANNUAL,
            revenue=200_000_000.0,
            ebit=20_000_000.0,
            ebitda=30_000_000.0,
            net_income=15_000_000.0,
            total_assets=500_000_000.0,
            total_equity=150_000_000.0,
            total_debt=80_000_000.0,
            net_debt=50_000_000.0,
            free_cash_flow=18_000_000.0,
            shares_outstanding=2_000_000.0,
        ),
    )
    price_history_repository.create(
        db_session,
        PriceHistory(
            company_id=company.id,
            date=date(2024, 1, 2),
            open=54.0,
            high=56.0,
            low=53.5,
            close=55.0,
            adjusted_close=55.0,
            volume=200_000,
        ),
    )
    return company


def test_create_snapshot_for_company(db_session):
    company = _create_company_with_financials(db_session)
    service = _make_service(db_session)

    result = service.compute_and_upsert_for_company(company.id, snapshot_date=date(2024, 1, 31))
    latest = kpi_snapshot_repository.get_latest_by_company(db_session, company.id)

    assert result.success is True
    assert result.snapshot_id is not None
    assert latest is not None
    assert latest.snapshot_date == date(2024, 1, 31)
    assert "pe_ratio" in latest.metrics
    assert "roe" in latest.metrics
    assert QUALITY_SCORE_KEY in latest.metrics
    assert VALUE_SCORE_KEY in latest.metrics
    assert GROWTH_SCORE_KEY in latest.metrics
    assert RISK_SCORE_KEY in latest.metrics
    assert TOTAL_SCORE_KEY in latest.metrics


def test_update_existing_snapshot(db_session):
    company = _create_company_with_financials(db_session, isin="FR0000120999", ticker="PAY.PA")
    service = _make_service(db_session)
    snapshot_date = date(2024, 2, 29)

    first = service.compute_and_upsert_for_company(company.id, snapshot_date=snapshot_date)
    second = service.compute_and_upsert_for_company(company.id, snapshot_date=snapshot_date)
    snapshots = kpi_snapshot_repository.get_by_company_id(db_session, company.id)

    assert first.success is True
    assert second.success is True
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_date == snapshot_date


def test_snapshot_fails_when_company_missing(db_session):
    service = _make_service(db_session)

    result = service.compute_and_upsert_for_company(999999, snapshot_date=date(2024, 1, 31))

    assert result.success is False
    assert result.stage == "load"
    assert result.error == "company not found"


def test_snapshot_fails_when_financial_data_missing(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000999999",
            ticker="MISS.PA",
            name="Missing Statement",
            currency="EUR",
        ),
    )
    service = _make_service(db_session)

    result = service.compute_and_upsert_for_company(company.id, snapshot_date=date(2024, 1, 31))

    assert result.success is False
    assert result.stage == "load"
    assert result.error == "no annual financial statements"
    assert kpi_snapshot_repository.get_latest_by_company(db_session, company.id) is None


def test_snapshot_fails_when_price_missing(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000888888",
            ticker="NOPRICE.PA",
            name="No Price",
            currency="EUR",
        ),
    )
    financial_statement_repository.create(
        db_session,
        FinancialStatement(
            company_id=company.id,
            fiscal_year=2023,
            period_type=PeriodType.ANNUAL,
            revenue=100.0,
            ebit=10.0,
            ebitda=12.0,
            net_income=7.0,
            total_assets=200.0,
            total_equity=80.0,
            total_debt=50.0,
            net_debt=20.0,
            free_cash_flow=8.0,
            shares_outstanding=None,
        ),
    )
    service = _make_service(db_session)

    result = service.compute_and_upsert_for_company(company.id, snapshot_date=date(2024, 1, 31))

    assert result.success is False
    assert result.stage == "load"
    assert result.error == "no usable price data"
    assert kpi_snapshot_repository.get_latest_by_company(db_session, company.id) is None


def test_snapshot_metrics_match_ratio_service(db_session):
    company = _create_company_with_financials(db_session, isin="FR0000777777", ticker="CONSIST.PA")
    service = _make_service(db_session)
    ratio_service = RatioService()

    result = service.compute_and_upsert_for_company(company.id, snapshot_date=date(2024, 1, 31))
    statement = financial_statement_repository.get_by_company(db_session, company.id)[0]
    expected = ratio_service.compute_all(company.id, statement.fiscal_year, 55.0, statement)

    assert result.success is True
    assert result.metrics["pe_ratio"] == expected.pe_ratio
    assert result.metrics["ev_ebitda"] == expected.ev_ebitda
    assert result.metrics["roe"] == expected.roe


def test_snapshot_uses_market_cap_fallback_when_price_history_missing(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000666666",
            ticker="FALLBACK.PA",
            name="Fallback Price",
            currency="EUR",
            market_cap=110_000_000.0,
        ),
    )
    financial_statement_repository.create(
        db_session,
        FinancialStatement(
            company_id=company.id,
            fiscal_year=2023,
            period_type=PeriodType.ANNUAL,
            revenue=200_000_000.0,
            ebit=20_000_000.0,
            ebitda=30_000_000.0,
            net_income=15_000_000.0,
            total_assets=500_000_000.0,
            total_equity=150_000_000.0,
            total_debt=80_000_000.0,
            net_debt=50_000_000.0,
            free_cash_flow=18_000_000.0,
            shares_outstanding=2_000_000.0,
        ),
    )
    service = _make_service(db_session)

    result = service.compute_and_upsert_for_company(company.id, snapshot_date=date(2024, 1, 31))

    assert result.success is True
    assert result.metrics["price"] == 55.0


def test_snapshot_metrics_include_growth_when_previous_statement_exists(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000555555",
            ticker="GROWTH.PA",
            name="Growth Corp",
            currency="EUR",
        ),
    )
    financial_statement_repository.create(
        db_session,
        FinancialStatement(
            company_id=company.id,
            fiscal_year=2022,
            period_type=PeriodType.ANNUAL,
            revenue=180_000_000.0,
            ebit=18_000_000.0,
            ebitda=28_000_000.0,
            net_income=13_000_000.0,
            total_assets=480_000_000.0,
            total_equity=140_000_000.0,
            total_debt=82_000_000.0,
            net_debt=55_000_000.0,
            free_cash_flow=16_000_000.0,
            shares_outstanding=2_000_000.0,
        ),
    )
    financial_statement_repository.create(
        db_session,
        FinancialStatement(
            company_id=company.id,
            fiscal_year=2023,
            period_type=PeriodType.ANNUAL,
            revenue=200_000_000.0,
            ebit=20_000_000.0,
            ebitda=30_000_000.0,
            net_income=15_000_000.0,
            total_assets=500_000_000.0,
            total_equity=150_000_000.0,
            total_debt=80_000_000.0,
            net_debt=50_000_000.0,
            free_cash_flow=18_000_000.0,
            shares_outstanding=2_000_000.0,
        ),
    )
    price_history_repository.create(
        db_session,
        PriceHistory(
            company_id=company.id,
            date=date(2024, 1, 2),
            open=54.0,
            high=56.0,
            low=53.5,
            close=55.0,
            adjusted_close=55.0,
            volume=200_000,
        ),
    )
    service = _make_service(db_session)

    result = service.compute_and_upsert_for_company(company.id, snapshot_date=date(2024, 1, 31))

    assert result.success is True
    assert result.metrics["revenue_growth"] == (200_000_000.0 - 180_000_000.0) / 180_000_000.0
    assert result.metrics["ebitda_growth"] == (30_000_000.0 - 28_000_000.0) / 28_000_000.0


def test_refresh_universe_kpi_snapshots_complete(db_session):
    company_a = _create_company_with_financials(db_session, isin="FR0000444444", ticker="U1.PA")
    company_b = _create_company_with_financials(db_session, isin="FR0000333333", ticker="U2.PA")
    service = _make_service(db_session)

    result = service.refresh_universe_kpi_snapshots(snapshot_date=date(2024, 3, 31))

    assert result.total == 2
    assert result.success_count == 2
    assert result.failed_count == 0
    assert result.errors == []
    latest_a = kpi_snapshot_repository.get_latest_by_company(db_session, company_a.id)
    latest_b = kpi_snapshot_repository.get_latest_by_company(db_session, company_b.id)
    assert latest_a is not None
    assert latest_b is not None
    assert TOTAL_SCORE_KEY in latest_a.metrics
    assert TOTAL_SCORE_KEY in latest_b.metrics


def test_refresh_universe_kpi_snapshots_partial_failure_does_not_block(db_session):
    success_company = _create_company_with_financials(db_session, isin="FR0000222222", ticker="OK.PA")
    failing_company = company_repository.create(
        db_session,
        Company(
            isin="FR0000111111",
            ticker="FAIL.PA",
            name="Failing Corp",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=250_000_000.0,
            average_daily_volume=180_000.0,
        ),
    )
    service = _make_service(db_session)

    result = service.refresh_universe_kpi_snapshots(snapshot_date=date(2024, 4, 30))

    assert result.total == 2
    assert result.success_count == 1
    assert result.failed_count == 1
    assert len(result.errors) == 1
    assert result.errors[0].company_id == failing_company.id
    assert result.errors[0].stage == "load"
    assert kpi_snapshot_repository.get_latest_by_company(db_session, success_company.id) is not None
    assert kpi_snapshot_repository.get_latest_by_company(db_session, failing_company.id) is None


def test_rank_universe_by_total_score_is_descending_and_stable(db_session):
    alpha = _create_company_with_financials(db_session, isin="FR0000210001", ticker="ALPHA.PA")
    beta = _create_company_with_financials(db_session, isin="FR0000210002", ticker="BETA.PA")
    gamma = _create_company_with_financials(db_session, isin="FR0000210003", ticker="GAMMA.PA")

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(company_id=alpha.id, snapshot_date=date(2024, 5, 31), metrics={TOTAL_SCORE_KEY: 82.5}, source="s1"),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(company_id=beta.id, snapshot_date=date(2024, 5, 31), metrics={TOTAL_SCORE_KEY: 95.0}, source="s1"),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(company_id=gamma.id, snapshot_date=date(2024, 5, 31), metrics={TOTAL_SCORE_KEY: 82.5}, source="s1"),
    )
    service = _make_service(db_session)

    first = service.rank_universe_by_total_score()
    second = service.rank_universe_by_total_score()

    assert first == second
    assert [entry.company_id for entry in first] == [beta.id, alpha.id, gamma.id]
    assert [entry.rank for entry in first] == [1, 2, 3]
    assert [entry.total_score for entry in first] == [95.0, 82.5, 82.5]


def test_rank_universe_by_total_score_handles_missing_scores(db_session):
    scored = _create_company_with_financials(db_session, isin="FR0000220001", ticker="SCORED.PA")
    missing_key = _create_company_with_financials(db_session, isin="FR0000220002", ticker="MISSING.PA")
    explicit_none = _create_company_with_financials(db_session, isin="FR0000220003", ticker="NONE.PA")
    no_snapshot = _create_company_with_financials(db_session, isin="FR0000220004", ticker="NOSNAP.PA")

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=scored.id,
            snapshot_date=date(2024, 6, 30),
            metrics={TOTAL_SCORE_KEY: 88.0},
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=missing_key.id,
            snapshot_date=date(2024, 6, 30),
            metrics={"pe_ratio": 12.0},
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=explicit_none.id,
            snapshot_date=date(2024, 6, 30),
            metrics={TOTAL_SCORE_KEY: None},
            source="s1",
        ),
    )
    service = _make_service(db_session)

    ranking = service.rank_universe_by_total_score()

    assert ranking[0].company_id == scored.id
    assert ranking[0].rank == 1
    assert ranking[0].total_score == 88.0

    tail = ranking[1:]
    expected_tail = sorted([missing_key.id, explicit_none.id, no_snapshot.id])
    assert [entry.company_id for entry in tail] == expected_tail
    assert all(entry.rank is None for entry in tail)
    assert all(entry.total_score is None for entry in tail)
