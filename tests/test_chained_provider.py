from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.repositories.providers.base import (
    DataFetchError,
    ProviderDataInconsistentError,
    TickerNotFoundError,
)
from src.repositories.providers.chained_provider import ChainedProvider
from src.repositories.providers.noop_provider import NoOpProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider(
    *,
    source: str = "mock",
    price: float | None = 42.0,
    error: Exception | None = None,
) -> MagicMock:
    """Build a minimal MagicMock provider."""
    provider = MagicMock()
    provider.source_name = source
    if error is not None:
        provider.get_current_price.side_effect = error
        provider.get_company_info.side_effect = error
        provider.get_price_history.side_effect = error
        provider.get_financial_statements.side_effect = error
    else:
        provider.get_current_price.return_value = price
    return provider


# ---------------------------------------------------------------------------
# NoOpProvider
# ---------------------------------------------------------------------------


def test_noop_provider_source_name():
    assert NoOpProvider().source_name == "noop"


def test_noop_provider_get_current_price_raises():
    with pytest.raises(DataFetchError):
        NoOpProvider().get_current_price("ACME")


def test_noop_provider_get_company_info_raises():
    with pytest.raises(DataFetchError):
        NoOpProvider().get_company_info("ACME")


def test_noop_provider_get_price_history_raises():
    with pytest.raises(DataFetchError):
        NoOpProvider().get_price_history("ACME")


def test_noop_provider_get_financial_statements_raises():
    with pytest.raises(DataFetchError):
        NoOpProvider().get_financial_statements("ACME")


# ---------------------------------------------------------------------------
# ChainedProvider — construction
# ---------------------------------------------------------------------------


def test_chained_provider_requires_at_least_one_provider():
    with pytest.raises(ValueError, match="at least one"):
        ChainedProvider([])


def test_chained_provider_source_name_single():
    chain = ChainedProvider([_make_provider(source="alpha")])
    assert chain.source_name == "alpha"


def test_chained_provider_source_name_chain():
    chain = ChainedProvider([_make_provider(source="alpha"), _make_provider(source="beta")])
    assert chain.source_name == "alpha→beta"


# ---------------------------------------------------------------------------
# ChainedProvider — primary succeeds
# ---------------------------------------------------------------------------


def test_chained_provider_primary_success_returns_value():
    primary = _make_provider(source="primary", price=99.0)
    fallback = _make_provider(source="fallback", price=1.0)
    chain = ChainedProvider([primary, fallback])

    result = chain.get_current_price("ACME")

    assert result == 99.0
    fallback.get_current_price.assert_not_called()


def test_chained_provider_primary_success_fallback_not_called():
    primary = _make_provider(source="primary", price=50.0)
    fallback = _make_provider(source="fallback", price=1.0)
    chain = ChainedProvider([primary, fallback])

    chain.get_current_price("ACME")

    fallback.get_current_price.assert_not_called()


# ---------------------------------------------------------------------------
# ChainedProvider — fallback used
# ---------------------------------------------------------------------------


def test_chained_provider_falls_back_on_data_fetch_error():
    primary = _make_provider(source="primary", error=DataFetchError("primary down"))
    fallback = _make_provider(source="fallback", price=77.0)
    chain = ChainedProvider([primary, fallback])

    result = chain.get_current_price("ACME")

    assert result == 77.0


def test_chained_provider_falls_back_on_ticker_not_found():
    primary = _make_provider(source="primary", error=TickerNotFoundError("not found"))
    fallback = _make_provider(source="fallback", price=55.0)
    chain = ChainedProvider([primary, fallback])

    result = chain.get_current_price("ACME")

    assert result == 55.0


def test_chained_provider_falls_back_on_inconsistent_data_error():
    primary = _make_provider(source="primary", error=ProviderDataInconsistentError("bad data"))
    fallback = _make_provider(source="fallback", price=33.0)
    chain = ChainedProvider([primary, fallback])

    result = chain.get_current_price("ACME")

    assert result == 33.0


# ---------------------------------------------------------------------------
# ChainedProvider — all providers fail
# ---------------------------------------------------------------------------


def test_chained_provider_raises_when_all_fail():
    err1 = DataFetchError("primary failed")
    err2 = DataFetchError("fallback failed")
    chain = ChainedProvider(
        [
            _make_provider(source="primary", error=err1),
            _make_provider(source="fallback", error=err2),
        ]
    )

    with pytest.raises(DataFetchError) as exc_info:
        chain.get_current_price("ACME")

    assert exc_info.value is err2


def test_chained_provider_raises_last_error_not_first():
    first_err = TickerNotFoundError("primary: no ticker")
    last_err = DataFetchError("fallback: connection error")
    chain = ChainedProvider(
        [
            _make_provider(source="primary", error=first_err),
            _make_provider(source="fallback", error=last_err),
        ]
    )

    with pytest.raises(DataFetchError) as exc_info:
        chain.get_current_price("ACME")

    assert exc_info.value is last_err


# ---------------------------------------------------------------------------
# ChainedProvider — non-ProviderError propagates immediately
# ---------------------------------------------------------------------------


def test_chained_provider_propagates_non_provider_error_immediately():
    unexpected = RuntimeError("unexpected network failure")
    primary = _make_provider(source="primary")
    primary.get_current_price.side_effect = unexpected
    fallback = _make_provider(source="fallback", price=1.0)
    chain = ChainedProvider([primary, fallback])

    with pytest.raises(RuntimeError, match="unexpected network failure"):
        chain.get_current_price("ACME")

    # Fallback must NOT have been consulted
    fallback.get_current_price.assert_not_called()


# ---------------------------------------------------------------------------
# ChainedProvider — optional method skips providers that lack it
# ---------------------------------------------------------------------------


def test_chained_provider_optional_method_skips_missing_provider():
    """get_dividends not on provider_a; only provider_b has it."""
    provider_a = _make_provider(source="a")
    del provider_a.get_dividends  # simulate provider without get_dividends

    provider_b = MagicMock()
    provider_b.source_name = "b"
    provider_b.get_dividends.return_value = []

    chain = ChainedProvider([provider_a, provider_b])

    result = chain.get_dividends("ACME")

    assert result == []
    provider_b.get_dividends.assert_called_once_with("ACME")


def test_chained_provider_optional_method_raises_when_no_provider_supports_it():
    provider_a = _make_provider(source="a")
    del provider_a.get_dividends

    chain = ChainedProvider([provider_a])

    with pytest.raises(DataFetchError, match="No provider supports"):
        chain.get_dividends("ACME")


# ---------------------------------------------------------------------------
# ChainedProvider — three-provider chain
# ---------------------------------------------------------------------------


def test_chained_provider_three_providers_uses_second_on_first_fail():
    err = DataFetchError("first down")
    chain = ChainedProvider(
        [
            _make_provider(source="first", error=err),
            _make_provider(source="second", price=22.0),
            _make_provider(source="third", price=33.0),
        ]
    )

    result = chain.get_current_price("ACME")

    assert result == 22.0


# ---------------------------------------------------------------------------
# ChainedProvider — with NoOpProvider as fallback
# ---------------------------------------------------------------------------


def test_chained_provider_noop_fallback_fails_chain():
    chain = ChainedProvider([NoOpProvider()])

    with pytest.raises(DataFetchError):
        chain.get_current_price("ACME")


def test_chained_provider_primary_with_noop_fallback_succeeds_via_primary():
    primary = _make_provider(source="primary", price=88.0)
    chain = ChainedProvider([primary, NoOpProvider()])

    result = chain.get_current_price("ACME")

    assert result == 88.0
