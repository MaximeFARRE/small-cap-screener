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
    business_summary: str | None = None
    isin: str | None = None
    full_time_employees: int | None = None
    city: str | None = None
    phone: str | None = None
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
    gross_profit: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    interest_expense: float | None = None


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


@dataclass
class AnalystData:
    ticker: str
    enterprise_value: float | None
    beta: float | None
    forward_pe: float | None
    target_price_mean: float | None
    target_price_high: float | None
    target_price_low: float | None
    recommendation_key: str | None
    number_of_analyst_opinions: int | None
    # New fundamental metrics
    gross_margins: float | None = None
    operating_margins: float | None = None
    profit_margins: float | None = None
    roe: float | None = None
    roa: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    payout_ratio: float | None = None
    # Shares and volume
    shares_outstanding: float | None = None
    float_shares: float | None = None
    average_volume: float | None = None
    # Dividends
    dividend_rate: float | None = None
    dividend_yield: float | None = None
    ex_dividend_date: datetime | None = None
    five_year_avg_dividend_yield: float | None = None
    source: str | None = None
    fetched_at: datetime | None = None


@dataclass
class HolderData:
    ticker: str
    holder_type: str
    holder_name: str
    weight: float | None
    shares: float | None = None
    market_value: float | None = None
    date_reported: date | None = None
    source: str | None = None
    fetched_at: datetime | None = None


@dataclass
class InsiderTransactionData:
    ticker: str
    insider_name: str | None
    relation: str | None
    transaction_text: str | None
    ownership: str | None
    shares: float | None
    market_value: float | None
    start_date: date | None = None
    source: str | None = None
    fetched_at: datetime | None = None


@dataclass
class ExecutiveData:
    ticker: str
    name: str
    title: str | None
    age: int | None
    total_pay: float | None
    year_born: int | None = None
    fiscal_year: int | None = None
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

    def get_major_holders(self, ticker: str) -> list[HolderData]:
        return []

    def get_institutional_holders(self, ticker: str) -> list[HolderData]:
        return []

    def get_mutualfund_holders(self, ticker: str) -> list[HolderData]:
        return []

    def get_insider_transactions(self, ticker: str) -> list[InsiderTransactionData]:
        return []

    def get_key_executives(self, ticker: str) -> list[ExecutiveData]:
        return []

    def search_by_isin(self, isin: str) -> str | None:
        """Find the ticker corresponding to an ISIN, or None if not found or not supported."""
        return None
