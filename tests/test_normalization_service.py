from __future__ import annotations

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
