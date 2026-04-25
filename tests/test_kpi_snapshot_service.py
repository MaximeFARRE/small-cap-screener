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
