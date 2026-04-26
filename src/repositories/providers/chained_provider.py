from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar

from src.repositories.providers.base import (
    BaseProvider,
    CompanyInfo,
    DataFetchError,
    FinancialData,
    PriceHistory,
    ProviderError,
)

_T = TypeVar("_T")
_LOGGER = logging.getLogger(__name__)


class ChainedProvider(BaseProvider):
    """Tries providers in order, falling back to the next on ProviderError.

    Rules:
    - Providers are tried in the order given to the constructor.
    - On ProviderError (includes TickerNotFoundError, DataFetchError,
      ProviderDataInconsistentError), the next provider is tried.
    - Non-ProviderError exceptions propagate immediately without fallback,
      so unexpected errors are never silently swallowed.
    - If all providers fail, the last ProviderError is re-raised.
    - Optional provider methods (e.g. get_dividends) are only called on
      providers that expose them; if none do, DataFetchError is raised.
    """

    def __init__(self, providers: list[BaseProvider]) -> None:
        if not providers:
            raise ValueError("ChainedProvider requires at least one provider")
        self._providers = list(providers)

    @property
    def source_name(self) -> str:
        names = [p.source_name for p in self._providers]
        return "→".join(names)

    # --- Required BaseProvider methods ---

    def get_company_info(self, ticker: str) -> CompanyInfo:
        return self._try_in_order(
            "get_company_info",
            ticker,
            lambda p: p.get_company_info(ticker),
        )

    def get_price_history(self, ticker: str, period: str = "5y") -> list[PriceHistory]:
        return self._try_in_order(
            "get_price_history",
            ticker,
            lambda p: p.get_price_history(ticker, period),
        )

    def get_financial_statements(self, ticker: str, years: int = 5) -> list[FinancialData]:
        return self._try_in_order(
            "get_financial_statements",
            ticker,
            lambda p: p.get_financial_statements(ticker, years),
        )

    def get_current_price(self, ticker: str) -> float:
        return self._try_in_order(
            "get_current_price",
            ticker,
            lambda p: p.get_current_price(ticker),
        )

    # --- Optional methods forwarded to supporting providers ---

    def get_company_profile(self, ticker: str) -> object:
        return self._try_in_order(
            "get_company_profile",
            ticker,
            lambda p: p.get_company_profile(ticker),  # type: ignore[attr-defined]
        )

    def get_current_market_data(self, ticker: str) -> object:
        return self._try_in_order(
            "get_current_market_data",
            ticker,
            lambda p: p.get_current_market_data(ticker),  # type: ignore[attr-defined]
        )

    def get_dividends(self, ticker: str) -> list[object]:
        return self._try_in_order(
            "get_dividends",
            ticker,
            lambda p: p.get_dividends(ticker),  # type: ignore[attr-defined]
        )

    def get_splits(self, ticker: str) -> list[object]:
        return self._try_in_order(
            "get_splits",
            ticker,
            lambda p: p.get_splits(ticker),  # type: ignore[attr-defined]
        )

    # --- Internal orchestration ---

    def _try_in_order(
        self,
        method: str,
        ticker: str,
        call: Callable[[BaseProvider], _T],
    ) -> _T:
        """Try each provider in sequence, catching ProviderError to fall back."""
        last_error: ProviderError | None = None
        attempted: list[str] = []

        for provider in self._providers:
            if not hasattr(provider, method):
                continue
            provider_name = provider.source_name
            attempted.append(provider_name)
            try:
                result = call(provider)
                _LOGGER.info(
                    "chained provider success | method=%s ticker=%s provider=%s",
                    method,
                    ticker,
                    provider_name,
                )
                return result
            except ProviderError as exc:
                last_error = exc
                _LOGGER.warning(
                    "chained provider fallback | method=%s ticker=%s provider=%s error=%s",
                    method,
                    ticker,
                    provider_name,
                    exc,
                )

        if last_error is not None:
            _LOGGER.error(
                "chained provider all failed | method=%s ticker=%s tried=%s",
                method,
                ticker,
                "→".join(attempted),
            )
            raise last_error

        raise DataFetchError(f"No provider supports '{method}' for ticker '{ticker}' (chain: {self.source_name})")
