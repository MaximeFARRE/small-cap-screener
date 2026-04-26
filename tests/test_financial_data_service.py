from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock

from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.price_history import PriceHistory as PriceHistoryModel
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


def _make_service(
    db_session,
    provider,
    *,
    provider_call_max_attempts: int = 3,
    provider_retry_delay_seconds: float = 0.0,
    offline_mode: bool = False,
):
    @contextmanager
    def session_scope():
        yield db_session

    return FinancialDataService(
        provider=provider,
        session_scope_factory=session_scope,
        provider_call_max_attempts=provider_call_max_attempts,
        provider_retry_delay_seconds=provider_retry_delay_seconds,
        offline_mode=offline_mode,
    )


def _make_provider(
    failing_ticker: str | None = None,
    negative_price_ticker: str | None = None,
    duplicate_date_ticker: str | None = None,
    currency_alias_ticker: str | None = None,
) -> MagicMock:
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
        currency = "euro" if currency_alias_ticker is not None and ticker == currency_alias_ticker else "EUR"
        return MarketData(
            ticker=ticker,
            current_price=25.0,
            previous_close=24.5,
            open=24.7,
            day_high=25.4,
            day_low=24.4,
            volume=250_000,
            market_cap=400_000_000.0,
            currency=currency,
            source="mock-provider",
        )

    def _price_history(ticker: str, period: str = "5y") -> list[PriceHistory]:
        if failing_ticker is not None and ticker == failing_ticker:
            raise DataFetchError("simulated provider outage")
        if duplicate_date_ticker is not None and ticker == duplicate_date_ticker:
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
                ),
                PriceHistory(
                    date=date(2024, 1, 2),
                    open=20.1,
                    high=21.1,
                    low=19.9,
                    close=20.8,
                    adjusted_close=20.8,
                    volume=181_000,
                    source="mock-provider",
                ),
            ]
        close = -20.7 if negative_price_ticker is not None and ticker == negative_price_ticker else 20.7
        return [
            PriceHistory(
                date=date(2024, 1, 2),
                open=20.0,
                high=21.0,
                low=19.8,
                close=close,
                adjusted_close=close,
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


def test_refresh_company_data_allows_missing_isin(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin=None,
            ticker="NOISIN.PA",
            name="No Isin",
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
    assert "isin is missing" in result.warnings


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
    assert service.provider.get_price_history.call_count == service.provider_call_max_attempts


def test_refresh_company_data_retries_and_succeeds_on_transient_failure(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007006",
            ticker="RETRY.PA",
            name="Retry",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    provider = _make_provider()
    price_call_count = {"value": 0}

    def _transient_price_history(ticker: str, period: str = "5y") -> list[PriceHistory]:
        price_call_count["value"] += 1
        if price_call_count["value"] == 1:
            raise DataFetchError("temporary outage")
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

    provider.get_price_history.side_effect = _transient_price_history
    service = _make_service(db_session, provider, provider_call_max_attempts=3)

    result = service.refresh_company_data(company.id)

    assert result.success is True
    assert service.provider.get_price_history.call_count == 2


def test_fetch_company_data_uses_fallback_after_optional_retry_failure(db_session):
    provider = _make_provider()
    provider.get_current_market_data.side_effect = DataFetchError("market endpoint down")
    service = _make_service(db_session, provider, provider_call_max_attempts=2)

    fetched = service.fetch_company_data("ALPHA.PA")

    assert fetched.ticker == "ALPHA.PA"
    assert fetched.market_data is None
    assert service.provider.get_current_market_data.call_count == 2


def test_refresh_company_data_offline_uses_local_data_only(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007010",
            ticker="OFFOK.PA",
            name="Offline Ok",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    price_history_repository.create(
        db_session,
        PriceHistoryModel(
            company_id=company.id,
            date=date(2024, 1, 2),
            open=20.0,
            high=21.0,
            low=19.8,
            close=20.7,
            adjusted_close=20.7,
            volume=180_000,
        ),
    )
    financial_statement_repository.create(
        db_session,
        FinancialStatement(
            company_id=company.id,
            fiscal_year=2023,
            period_type=PeriodType.ANNUAL,
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
        ),
    )
    provider = _make_provider()
    service = _make_service(db_session, provider, offline_mode=True)

    result = service.refresh_company_data(company.id)

    assert result.success is True
    assert result.prices_added == 0
    assert result.statements_added == 0
    assert "offline mode: using local data only" in result.warnings
    assert provider.get_company_profile.call_count == 0
    assert provider.get_current_market_data.call_count == 0
    assert provider.get_price_history.call_count == 0
    assert provider.get_financial_statements.call_count == 0


def test_refresh_company_data_offline_reports_missing_local_data(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007011",
            ticker="OFFKO.PA",
            name="Offline Missing",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    provider = _make_provider()
    service = _make_service(db_session, provider, offline_mode=True)

    result = service.refresh_company_data(company.id)

    assert result.success is False
    assert result.stage == "offline"
    assert result.error is not None
    assert "offline mode: missing local data" in result.error
    assert "price history" in result.error
    assert "financial statements" in result.error
    assert provider.get_company_profile.call_count == 0
    assert provider.get_current_market_data.call_count == 0
    assert provider.get_price_history.call_count == 0
    assert provider.get_financial_statements.call_count == 0


def test_refresh_company_data_blocks_invalid_payload(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007002",
            ticker="NEG.PA",
            name="Negative",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider(negative_price_ticker="NEG.PA"))

    result = service.refresh_company_data(company.id)

    assert result.success is False
    assert result.stage == "validate"
    assert result.error is not None
    assert "non-positive close" in result.error
    assert len(price_history_repository.get_by_company(db_session, company.id)) == 0
    assert len(financial_statement_repository.get_by_company(db_session, company.id)) == 0


def test_refresh_company_data_blocks_invalid_normalization(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="INVALID",
            ticker="NORM.PA",
            name="Normalize",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider())

    result = service.refresh_company_data(company.id)

    assert result.success is False
    assert result.stage == "normalize"
    assert result.error is not None
    assert "isin format is invalid" in result.error
    assert len(price_history_repository.get_by_company(db_session, company.id)) == 0
    assert len(financial_statement_repository.get_by_company(db_session, company.id)) == 0


def test_refresh_company_data_keeps_normalization_warnings(db_session, caplog):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007004",
            ticker="WARN.PA",
            name="Warning",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider(duplicate_date_ticker="WARN.PA"))

    with caplog.at_level(logging.WARNING, logger="src.services.financial_data_service"):
        result = service.refresh_company_data(company.id)

    assert result.success is True
    assert any("price_history duplicate date normalized" in warning for warning in result.warnings)
    assert any("normalization warning" in record.message for record in caplog.records)
    assert len(price_history_repository.get_by_company(db_session, company.id)) == 1


def test_refresh_company_data_accepts_currency_alias_after_normalization(db_session):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007005",
            ticker="ALIAS.PA",
            name="Alias",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider(currency_alias_ticker="ALIAS.PA"))

    result = service.refresh_company_data(company.id)
    updated = company_repository.get_by_id(db_session, company.id)

    assert result.success is True
    assert updated is not None
    assert updated.currency == "EUR"


def test_refresh_company_data_logs_skipped_company(db_session, caplog):
    service = _make_service(db_session, _make_provider())

    with caplog.at_level(logging.WARNING, logger="src.services.financial_data_service"):
        result = service.refresh_company_data(999999)

    assert result.success is False
    assert any("company skipped" in record.message for record in caplog.records)


def test_refresh_company_data_logs_validation_block(db_session, caplog):
    company = company_repository.create(
        db_session,
        Company(
            isin="FR0000007003",
            ticker="NEG2.PA",
            name="Negative 2",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider(negative_price_ticker="NEG2.PA"))

    with caplog.at_level(logging.ERROR, logger="src.services.financial_data_service"):
        result = service.refresh_company_data(company.id)

    assert result.success is False
    assert result.stage == "validate"
    assert any("validation blocked storage" in record.message for record in caplog.records)


def test_refresh_universe_data_logs_completion(db_session, caplog):
    company_repository.create(
        db_session,
        Company(
            isin="FR0000008001",
            ticker="LOG1.PA",
            name="Log One",
            country="France",
            sector="Industrial",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=320_000_000.0,
            average_daily_volume=120_000.0,
        ),
    )
    service = _make_service(db_session, _make_provider())

    with caplog.at_level(logging.INFO, logger="src.services.financial_data_service"):
        result = service.refresh_universe_data()

    assert result.total_companies == 1
    assert any("universe refresh completed" in record.message for record in caplog.records)
