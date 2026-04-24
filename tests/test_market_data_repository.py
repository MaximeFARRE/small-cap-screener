from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.models.financial_statement import PeriodType
from src.repositories import (
    company_repository,
    financial_statement_repository,
    price_history_repository,
)
from src.repositories.market_data_repository import SyncResult, sync_company
from src.repositories.providers.base import CompanyInfo, FinancialData, PriceRecord


def _make_provider(
    name: str = "TotalEnergies SE",
    price: float = 55.0,
    prices: list[PriceRecord] | None = None,
    statements: list[FinancialData] | None = None,
) -> MagicMock:
    provider = MagicMock()
    provider.get_company_info.return_value = CompanyInfo(name=name, sector="Energy", market="PAR", currency="EUR")
    provider.get_current_price.return_value = price
    provider.get_price_history.return_value = prices or [
        PriceRecord(
            date=date(2024, 1, 2),
            open=54.0,
            high=56.0,
            low=53.5,
            close=55.0,
            adjusted_close=55.0,
            volume=200_000,
        ),
    ]
    provider.get_financial_statements.return_value = statements or [
        FinancialData(
            fiscal_year=2023,
            period_type=PeriodType.ANNUAL,
            revenue=200e6,
            ebit=20e6,
            ebitda=30e6,
            net_income=15e6,
            total_assets=500e6,
            total_equity=150e6,
            total_debt=80e6,
            net_debt=50e6,
            free_cash_flow=18e6,
            shares_outstanding=2e6,
        ),
    ]
    return provider


def test_sync_creates_company(db_session):
    result = sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    assert isinstance(result, SyncResult)
    company = company_repository.get_by_isin(db_session, "FR0000120271")
    assert company is not None
    assert company.name == "TotalEnergies SE"
    assert company.ticker == "TTE.PA"


def test_sync_stores_prices(db_session):
    result = sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    assert result.prices_added == 1
    company = company_repository.get_by_isin(db_session, "FR0000120271")
    records = price_history_repository.get_by_company(db_session, company.id)
    assert len(records) == 1
    assert records[0].close == 55.0


def test_sync_stores_financial_statements(db_session):
    result = sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    assert result.statements_added == 1
    company = company_repository.get_by_isin(db_session, "FR0000120271")
    stmts = financial_statement_repository.get_by_company(db_session, company.id)
    assert len(stmts) == 1
    assert stmts[0].fiscal_year == 2023
    assert stmts[0].revenue == pytest.approx(200e6)


def test_sync_upserts_existing_company(db_session):
    sync_company(db_session, _make_provider(name="Old Name"), "TTE.PA", "FR0000120271")
    sync_company(db_session, _make_provider(name="TotalEnergies SE"), "TTE.PA", "FR0000120271")
    companies = company_repository.get_all(db_session)
    assert len(companies) == 1
    assert companies[0].name == "TotalEnergies SE"


def test_sync_skips_duplicate_prices(db_session):
    sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    result = sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    assert result.prices_added == 0


def test_sync_skips_duplicate_statements(db_session):
    sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    result = sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    assert result.statements_added == 0


def test_sync_returns_correct_company_id(db_session):
    result = sync_company(db_session, _make_provider(), "TTE.PA", "FR0000120271")
    company = company_repository.get_by_isin(db_session, "FR0000120271")
    assert result.company_id == company.id
