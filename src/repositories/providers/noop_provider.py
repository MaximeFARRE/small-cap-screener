from __future__ import annotations

from src.repositories.providers.base import (
    BaseProvider,
    CompanyInfo,
    DataFetchError,
    FinancialData,
    PriceHistory,
)

_SOURCE_NAME = "noop"


class NoOpProvider(BaseProvider):
    """Explicit no-op provider — always raises DataFetchError.

    Used as a fallback sentinel in ChainedProvider to test provider
    redundancy chains, or as a placeholder when a provider is intentionally
    disabled (e.g. during offline testing without network mocks).
    """

    @property
    def source_name(self) -> str:
        return _SOURCE_NAME

    def get_company_info(self, ticker: str) -> CompanyInfo:
        raise DataFetchError(f"NoOpProvider: no data available for '{ticker}'")

    def get_price_history(self, ticker: str, period: str = "5y") -> list[PriceHistory]:
        raise DataFetchError(f"NoOpProvider: no price history for '{ticker}'")

    def get_financial_statements(self, ticker: str, years: int = 5) -> list[FinancialData]:
        raise DataFetchError(f"NoOpProvider: no financial statements for '{ticker}'")

    def get_current_price(self, ticker: str) -> float:
        raise DataFetchError(f"NoOpProvider: no current price for '{ticker}'")
