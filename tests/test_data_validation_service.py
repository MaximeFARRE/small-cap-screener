from __future__ import annotations

from datetime import date

from src.repositories.providers.base import (
    CompanyProfile,
    DividendData,
    FinancialData,
    MarketData,
    PriceHistory,
    SplitData,
)
from src.services.data_validation_service import DataValidationService


def _valid_profile() -> CompanyProfile:
    return CompanyProfile(
        ticker="ABC.PA",
        name="ABC",
        sector="Industrial",
        industry="Capital Goods",
        market="PAR",
        country="France",
        currency="EUR",
        website=None,
        source="tests",
    )


def _valid_market_data() -> MarketData:
    return MarketData(
        ticker="ABC.PA",
        current_price=12.0,
        previous_close=11.9,
        open=12.0,
        day_high=12.4,
        day_low=11.7,
        volume=120_000,
        market_cap=240_000_000.0,
        currency="EUR",
        source="tests",
    )


def _valid_price_history(close: float = 12.0) -> list[PriceHistory]:
    return [
        PriceHistory(
            date=date(2024, 1, 2),
            open=11.8,
            high=12.5,
            low=11.7,
            close=close,
            adjusted_close=close,
            volume=100_000,
            source="tests",
        )
    ]


def _valid_statements() -> list[FinancialData]:
    return [
        FinancialData(
            fiscal_year=2023,
            period_type="annual",
            revenue=10_000_000.0,
            ebit=1_500_000.0,
            ebitda=2_000_000.0,
            net_income=1_000_000.0,
            total_assets=8_000_000.0,
            total_equity=3_000_000.0,
            total_debt=1_000_000.0,
            net_debt=750_000.0,
            free_cash_flow=500_000.0,
            shares_outstanding=1_200_000.0,
        )
    ]


def _valid_dividends() -> list[DividendData]:
    return [
        DividendData(
            ex_date=date(2024, 5, 1),
            amount=0.2,
            payment_date=date(2024, 5, 20),
            source="tests",
        )
    ]


def _valid_splits() -> list[SplitData]:
    return [
        SplitData(
            split_date=date(2024, 6, 10),
            ratio_from=1.0,
            ratio_to=2.0,
            source="tests",
        )
    ]


def test_validation_accepts_valid_data():
    service = DataValidationService()

    result = service.validate_company_data(
        ticker=" abc.pa ",
        profile=_valid_profile(),
        market_data=_valid_market_data(),
        price_history=_valid_price_history(),
        financial_statements=_valid_statements(),
        dividends=_valid_dividends(),
        splits=_valid_splits(),
    )

    assert result.is_valid is True
    assert result.data.ticker == "ABC.PA"
    assert result.errors == []


def test_validation_rejects_negative_price():
    service = DataValidationService()

    result = service.validate_company_data(
        ticker="ABC.PA",
        profile=_valid_profile(),
        market_data=_valid_market_data(),
        price_history=_valid_price_history(close=-1.0),
        financial_statements=_valid_statements(),
        dividends=_valid_dividends(),
        splits=_valid_splits(),
    )

    assert result.is_valid is False
    assert any("non-positive close" in error for error in result.errors)


def test_validation_rejects_empty_ticker():
    service = DataValidationService()

    result = service.validate_company_data(
        ticker="   ",
        profile=_valid_profile(),
        market_data=_valid_market_data(),
        price_history=_valid_price_history(),
        financial_statements=_valid_statements(),
        dividends=_valid_dividends(),
        splits=_valid_splits(),
    )

    assert result.is_valid is False
    assert "ticker is empty" in result.errors


def test_validation_rejects_negative_market_cap():
    service = DataValidationService()
    market_data = _valid_market_data()
    market_data.market_cap = -10.0

    result = service.validate_company_data(
        ticker="ABC.PA",
        profile=_valid_profile(),
        market_data=market_data,
        price_history=_valid_price_history(),
        financial_statements=_valid_statements(),
        dividends=_valid_dividends(),
        splits=_valid_splits(),
    )

    assert result.is_valid is False
    assert "market_data has non-positive market_cap" in result.errors


def test_validation_accepts_partial_missing_data_with_warnings():
    service = DataValidationService()
    market_data = _valid_market_data()
    market_data.currency = None
    market_data.market_cap = None

    result = service.validate_company_data(
        ticker="ABC.PA",
        profile=None,
        market_data=market_data,
        price_history=_valid_price_history(),
        financial_statements=[],
        dividends=[],
        splits=[],
    )

    assert result.is_valid is True
    assert "financial_statements is empty" in result.warnings
    assert "dividends is empty" in result.warnings
    assert "splits is empty" in result.warnings
    assert "currency is missing in both profile and market_data" in result.warnings
