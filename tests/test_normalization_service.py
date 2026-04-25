from __future__ import annotations

from datetime import UTC, date, datetime

from src.repositories.providers.base import DividendData, FinancialData, PriceHistory, SplitData
from src.services.normalization_service import NormalizationService


def test_normalization_currency_alias_and_identifiers():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker=" tte.pa ",
        isin=" fr0000120271 ",
        currency="euro",
        market_cap=120_000_000_000.0,
    )

    assert result.is_normalized is True
    assert result.data.ticker == "TTE.PA"
    assert result.data.isin == "FR0000120271"
    assert result.data.currency == "EUR"
    assert result.data.market_cap == 120_000_000_000.0


def test_normalization_detects_ticker_inconsistency():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker="TTE.PA",
        isin="FR0000120271",
        currency="EUR",
        market_cap=1.0,
        profile_ticker="ABC.PA",
    )

    assert result.is_normalized is False
    assert "profile ticker is inconsistent with requested ticker" in result.errors


def test_normalization_detects_currency_inconsistency():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker="TTE.PA",
        isin="FR0000120271",
        currency="EUR",
        market_cap=1.0,
        market_currency="USD",
    )

    assert result.is_normalized is False
    assert "currencies are inconsistent across sources" in result.errors


def test_normalization_rejects_invalid_isin():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker="TTE.PA",
        isin="INVALID",
        currency="EUR",
        market_cap=1.0,
    )

    assert result.is_normalized is False
    assert "isin format is invalid" in result.errors


def test_normalization_rejects_negative_market_cap():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker="TTE.PA",
        isin="FR0000120271",
        currency="EUR",
        market_cap=-1.0,
    )

    assert result.is_normalized is False
    assert "market_cap cannot be negative" in result.errors


def test_normalization_normalizes_dates_for_market_records():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker="TTE.PA",
        isin="FR0000120271",
        currency="EUR",
        market_cap=1.0,
        price_history=[
            PriceHistory(
                date=datetime(2024, 1, 1, 23, 0, tzinfo=UTC),
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                adjusted_close=10.5,
                volume=100,
            ),
            PriceHistory(
                date="2024-01-02T01:00:00+02:00",
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.5,
                adjusted_close=10.5,
                volume=100,
            ),
        ],
        dividends=[DividendData(ex_date="2024-05-01", amount=1.0, payment_date=None)],
        splits=[SplitData(split_date="2020-01-01", ratio_from=1.0, ratio_to=2.0)],
    )

    assert result.is_normalized is True
    assert len(result.data.price_history) == 1
    assert result.data.price_history[0].date == date(2024, 1, 1)
    assert result.data.dividends[0].ex_date == date(2024, 5, 1)
    assert result.data.splits[0].split_date == date(2020, 1, 1)
    assert any("price_history duplicate date normalized" in warning for warning in result.warnings)


def test_normalization_handles_missing_values_with_warnings():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker="TTE.PA",
        isin=None,
        currency=None,
        market_cap=None,
        financial_statements=None,
        price_history=None,
        dividends=None,
        splits=None,
    )

    assert result.is_normalized is True
    assert result.data.isin is None
    assert result.data.currency is None
    assert "isin is missing" in result.warnings
    assert "currency is missing" in result.warnings
    assert "financial_statements is missing" in result.warnings


def test_normalization_creates_fiscal_dates():
    service = NormalizationService()

    result = service.normalize_company_payload(
        ticker="TTE.PA",
        isin="FR0000120271",
        currency="EUR",
        market_cap=1.0,
        financial_statements=[
            FinancialData(
                fiscal_year=2023,
                period_type="annual",
                revenue=1.0,
                ebit=1.0,
                ebitda=1.0,
                net_income=1.0,
                total_assets=None,
                total_equity=None,
                total_debt=None,
                net_debt=None,
                free_cash_flow=1.0,
                shares_outstanding=None,
            ),
            FinancialData(
                fiscal_year=2023,
                period_type="half_year",
                revenue=1.0,
                ebit=1.0,
                ebitda=1.0,
                net_income=1.0,
                total_assets=None,
                total_equity=None,
                total_debt=None,
                net_debt=None,
                free_cash_flow=1.0,
                shares_outstanding=None,
            ),
        ],
    )

    assert result.is_normalized is True
    assert result.data.financial_statements[0].fiscal_date == date(2023, 6, 30)
    assert result.data.financial_statements[1].fiscal_date == date(2023, 12, 31)
