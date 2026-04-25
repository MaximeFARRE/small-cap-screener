from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock

from src.models.company import Company
from src.repositories import company_repository, financial_statement_repository, price_history_repository
from src.repositories.providers.base import (
    CompanyInfo,
    CompanyProfile,
    DataFetchError,
    FinancialData,
    MarketData,
    PriceHistory,
)
from src.services.financial_data_service import FinancialDataService


def _make_service(db_session, provider):
    @contextmanager
    def session_scope():
        yield db_session

    return FinancialDataService(provider=provider, session_scope_factory=session_scope)


def _make_provider(failing_ticker: str | None = None) -> MagicMock:
    provider = MagicMock()

    def _company_info(ticker: str) -> CompanyInfo:
        return CompanyInfo(name=f"{ticker} Corp", sector="Industrial", market="PAR", currency="EUR")

    def _company_profile(ticker: str) -> CompanyProfile:
        return CompanyProfile(
            ticker=ticker,
            name=f"{ticker} Corp",
            sector="Industrial",
            industry="Capital Goods",
            market="PAR",
            country="France",
            currency="EUR",
            website=None,
            source="mock-provider",
        )

    def _market_data(ticker: str) -> MarketData:
        return MarketData(
            ticker=ticker,
            current_price=25.0,
            previous_close=24.5,
            open=24.7,
            day_high=25.4,
            day_low=24.4,
            volume=250_000,
            market_cap=400_000_000.0,
            currency="EUR",
            source="mock-provider",
        )

    def _price_history(ticker: str, period: str = "5y") -> list[PriceHistory]:
        if failing_ticker is not None and ticker == failing_ticker:
            raise DataFetchError("simulated provider outage")
        return [
            PriceHistory(
                date=date(2024, 1, 2),
                open=20.0,
                high=21.0,
                low=19.8,
                close=20.7,
                adjusted_close=20.7,
                volume=180_000,
                source="mock-provider",
            )
        ]

    def _financial_statements(ticker: str, years: int = 5) -> list[FinancialData]:
        return [
            FinancialData(
                fiscal_year=2023,
                period_type="annual",
                revenue=120_000_000.0,
                ebit=16_000_000.0,
                ebitda=20_000_000.0,
                net_income=11_000_000.0,
                total_assets=200_000_000.0,
                total_equity=90_000_000.0,
                total_debt=30_000_000.0,
                net_debt=15_000_000.0,
                free_cash_flow=9_000_000.0,
                shares_outstanding=15_000_000.0,
            )
        ]

    provider.get_company_info.side_effect = _company_info
    provider.get_company_profile.side_effect = _company_profile
    provider.get_current_market_data.side_effect = _market_data
    provider.get_price_history.side_effect = _price_history
    provider.get_financial_statements.side_effect = _financial_statements
    provider.get_dividends.return_value = []
    provider.get_splits.return_value = []
    return provider


def test_fetch_company_data_single_company(db_session):
    service = _make_service(db_session, _make_provider())

    fetched = service.fetch_company_data("tte.pa")

    assert fetched.ticker == "TTE.PA"
    assert fetched.profile is not None
    assert fetched.market_data is not None
    assert len(fetched.price_history) == 1
    assert len(fetched.financial_statements) == 1


def test_refresh_company_data_existing_company(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000005001",
            ticker="ALPHA.PA",
            name="Alpha",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=350_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider())

    result = service.refresh_company_data(company.id)

    assert result.success is True
    assert result.prices_added == 1
    assert result.statements_added == 1
    updated = company_repository.get_by_id(db_session, company.id)
    assert updated is not None
    assert updated.market_cap == 400_000_000.0
    assert updated.average_daily_volume == 250_000
    assert len(price_history_repository.get_by_company(db_session, company.id)) == 1
    assert len(financial_statement_repository.get_by_company(db_session, company.id)) == 1


def test_refresh_universe_data_simple(db_session):
    company_repository.create(
        db_session,
        Company(
            isin="FR0000006001",
            ticker="ALPHA.PA",
            name="Alpha",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=320_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    company_repository.create(
        db_session,
        Company(
            isin="FR0000006002",
            ticker="BETA.PA",
            name="Beta",
            country="France",
            sector="Retail",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=450_000_000.0,
            average_daily_volume=150_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider())

    result = service.refresh_universe_data()

    assert result.total_companies == 2
    assert result.refreshed_count == 2
    assert result.failed_count == 0
    assert all(item.success for item in result.results)


def test_refresh_company_data_handles_provider_error(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007001",
            ticker="FAIL.PA",
            name="Fail",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider(failing_ticker="FAIL.PA"))

    result = service.refresh_company_data(company.id)

    assert result.success is False
    assert result.stage == "fetch"
    assert result.error is not None
    assert "simulated provider outage" in result.error
