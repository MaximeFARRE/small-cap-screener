from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


class ProviderError(Exception):
    """Base class for all data-provider errors."""


class TickerNotFoundError(ProviderError):
    """Raised when a ticker symbol cannot be resolved by the provider."""


class DataFetchError(ProviderError):
    """Raised when data retrieval fails after all retry attempts."""


class ProviderDataInconsistentError(ProviderError):
    """Raised when the provider returns a response but the data is incoherent."""


@dataclass
class CompanyInfo:
    name: str
    sector: str | None
    market: str | None
    currency: str


@dataclass
class CompanyProfile:
    ticker: str
    name: str
    sector: str | None
    industry: str | None
    market: str | None
    country: str | None
    currency: str
    website: str | None
    isin: str | None = None
    source: str | None = None
    fetched_at: datetime | None = None


@dataclass
class PriceHistory:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    adjusted_close: float | None
    volume: int | None
    source: str | None = None
    fetched_at: datetime | None = None


# Backward-compatible alias kept to avoid breaking existing imports.
PriceRecord = PriceHistory


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


@dataclass
class MarketData:
    ticker: str
    current_price: float
    previous_close: float | None
    open: float | None
    day_high: float | None
    day_low: float | None
    volume: int | None
    market_cap: float | None
    currency: str | None
    source: str | None = None
    fetched_at: datetime | None = None


@dataclass
class DividendData:
    ex_date: date
    amount: float
    payment_date: date | None
    source: str | None = None
    fetched_at: datetime | None = None


@dataclass
class SplitData:
    split_date: date
    ratio_from: float
    ratio_to: float
    source: str | None = None
    fetched_at: datetime | None = None


class BaseProvider(ABC):
    """Contract that every financial data provider must fulfil.

    To add a new source (Bloomberg, Refinitiv, …) create a subclass
    and implement all four methods — no other file needs to change.
    """

    @property
    def source_name(self) -> str:
        """Human-readable identifier used in logs and result tracking."""
        return type(self).__name__

    @abstractmethod
    def get_company_info(self, ticker: str) -> CompanyInfo: ...

    @abstractmethod
    def get_price_history(self, ticker: str, period: str = "5y") -> list[PriceHistory]: ...

    @abstractmethod
    def get_financial_statements(self, ticker: str, years: int = 5) -> list[FinancialData]: ...

    @abstractmethod
    def get_current_price(self, ticker: str) -> float: ...

    def search_by_isin(self, isin: str) -> str | None:
        """Find the ticker corresponding to an ISIN, or None if not found or not supported."""
        return None
