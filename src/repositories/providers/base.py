from __future__ import annotations

from abc import ABC, abstractmethod
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


class BaseProvider(ABC):
    """Contract that every financial data provider must fulfil.

    To add a new source (Bloomberg, Refinitiv, …) create a subclass
    and implement all four methods — no other file needs to change.
    """

    @abstractmethod
    def get_company_info(self, ticker: str) -> CompanyInfo: ...

    @abstractmethod
    def get_price_history(self, ticker: str, period: str = "5y") -> list[PriceRecord]: ...

    @abstractmethod
    def get_financial_statements(self, ticker: str, years: int = 5) -> list[FinancialData]: ...

    @abstractmethod
    def get_current_price(self, ticker: str) -> float: ...
