from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class ProviderError(Exception):
    """Base class for all data-provider errors."""


class TickerNotFoundError(ProviderError):
    """Raised when a ticker symbol cannot be resolved by the provider."""


class DataFetchError(ProviderError):
    """Raised when data retrieval fails after all retry attempts."""


@dataclass
class CompanyInfo:
    name: str
    sector: str | None
    market: str | None
    currency: str


@dataclass
class PriceRecord:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    adjusted_close: float | None
    volume: int | None


@dataclass
class FinancialData:
    fiscal_year: int
    period_type: str
    revenue: float | None
    ebit: float | None
    ebitda: float | None
    net_income: float | None
    total_assets: float | None
    total_equity: float | None
    total_debt: float | None
    net_debt: float | None
    free_cash_flow: float | None
    shares_outstanding: float | None
