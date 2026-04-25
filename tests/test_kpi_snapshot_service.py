from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.price_history import PriceHistory
from src.repositories import (
    company_repository,
    financial_statement_repository,
    kpi_snapshot_repository,
    price_history_repository,
)
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.ratio_service import RatioService


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
    assert kpi_snapshot_repository.get_latest_by_company(db_session, company_a.id) is not None
    assert kpi_snapshot_repository.get_latest_by_company(db_session, company_b.id) is not None
