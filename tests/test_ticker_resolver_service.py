from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.repositories.providers.base import (
    CompanyProfile,
    DataFetchError,
    ProviderDataInconsistentError,
    TickerNotFoundError,
)
from src.services.ticker_resolver_service import (
    TickerErrorKind,
    TickerResolverService,
    _has_suffix,
    _normalize,
)

# ---------------------------------------------------------------------------
# _normalize / _has_suffix helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("mc.pa", "MC.PA"),
        ("  MC.PA  ", "MC.PA"),
        ("BNP", "BNP"),
    ],
)
def test_normalize(raw, expected):
    assert _normalize(raw) == expected


@pytest.mark.parametrize(
    "ticker, has",
    [
        ("MC.PA", True),
        ("MC", False),
        ("ALAMY.AL", True),
        ("BNP", False),
    ],
)
def test_has_suffix(ticker, has):
    assert _has_suffix(ticker) == has


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(ticker: str) -> CompanyProfile:
    return CompanyProfile(
        ticker=ticker,
        name=f"{ticker} Corp",
        sector="Industrials",
        industry=None,
        market="ENX",
        country="France",
        currency="EUR",
        website=None,
    )


def _resolver(provider) -> TickerResolverService:
    return TickerResolverService(provider=provider)


# ---------------------------------------------------------------------------
# Direct resolution — ticker already complete
# ---------------------------------------------------------------------------


def test_resolve_direct_success():
    provider = MagicMock()
    provider.get_company_profile.return_value = _make_profile("MC.PA")
    result = _resolver(provider).resolve("MC.PA")

    assert result.success
    assert result.resolved_ticker == "MC.PA"
    assert result.suffix_added is None
    assert result.original_input == "MC.PA"
    assert result.error is None
    assert result.profile is not None
    provider.get_company_profile.assert_called_once_with("MC.PA")


def test_resolve_normalizes_input():
    provider = MagicMock()
    provider.get_company_profile.return_value = _make_profile("MC.PA")
    result = _resolver(provider).resolve("  mc.pa  ")

    assert result.success
    assert result.resolved_ticker == "MC.PA"
    assert result.original_input == "MC.PA"


# ---------------------------------------------------------------------------
# Suffix fallback — ticker without suffix
# ---------------------------------------------------------------------------


def test_resolve_adds_pa_suffix():
    provider = MagicMock()
    provider.get_company_profile.side_effect = [
        TickerNotFoundError("MC not found"),  # bare ticker
        _make_profile("MC.PA"),  # .PA candidate
    ]
    result = _resolver(provider).resolve("MC")

    assert result.success
    assert result.resolved_ticker == "MC.PA"
    assert result.suffix_added == ".PA"
    assert result.original_input == "MC"


def test_resolve_falls_back_to_al_suffix():
    provider = MagicMock()
    provider.get_company_profile.side_effect = [
        TickerNotFoundError("bare not found"),
        TickerNotFoundError(".PA not found"),
        _make_profile("ALAMY.AL"),
    ]
    result = _resolver(provider).resolve("ALAMY")

    assert result.success
    assert result.resolved_ticker == "ALAMY.AL"
    assert result.suffix_added == ".AL"


def test_resolve_no_suffix_added_when_suffix_already_present():
    provider = MagicMock()
    provider.get_company_profile.side_effect = TickerNotFoundError("not found")
    result = _resolver(provider).resolve("XXXX.PA")

    assert not result.success
    assert result.error_kind == TickerErrorKind.NOT_FOUND
    # Should not have tried .PA.PA or similar
    assert provider.get_company_profile.call_count == 1


# ---------------------------------------------------------------------------
# Not found — all attempts exhausted
# ---------------------------------------------------------------------------


def test_resolve_not_found_after_all_suffixes():
    provider = MagicMock()
    provider.get_company_profile.side_effect = TickerNotFoundError("not found")
    result = _resolver(provider).resolve("XXXX")

    assert not result.success
    assert result.resolved_ticker is None
    assert result.error_kind == TickerErrorKind.NOT_FOUND
    assert result.error is not None
    # bare + .PA + .AL = 3 attempts
    assert provider.get_company_profile.call_count == 3


# ---------------------------------------------------------------------------
# Provider errors — stop immediately, do not try suffixes
# ---------------------------------------------------------------------------


def test_resolve_stops_on_data_fetch_error():
    provider = MagicMock()
    provider.get_company_profile.side_effect = DataFetchError("network down")
    result = _resolver(provider).resolve("MC")

    assert not result.success
    assert result.error_kind == TickerErrorKind.PROVIDER_ERROR
    # Should not have tried any suffixes
    assert provider.get_company_profile.call_count == 1


def test_resolve_stops_on_data_inconsistent_error():
    provider = MagicMock()
    provider.get_company_profile.side_effect = ProviderDataInconsistentError("bad data")
    result = _resolver(provider).resolve("MC.PA")

    assert not result.success
    assert result.error_kind == TickerErrorKind.DATA_INCONSISTENT
    assert provider.get_company_profile.call_count == 1


def test_resolve_stops_on_unexpected_exception():
    provider = MagicMock()
    provider.get_company_profile.side_effect = RuntimeError("unexpected")
    result = _resolver(provider).resolve("MC")

    assert not result.success
    assert result.error_kind == TickerErrorKind.PROVIDER_ERROR
    assert provider.get_company_profile.call_count == 1
