from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class NormalizedFinancialStatement:
    fiscal_year: int
    period_type: str
    fiscal_date: date
    revenue: float | None
    ebitda: float | None
    ebit: float | None
    net_income: float | None
    free_cash_flow: float | None


@dataclass
class NormalizedPricePoint:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    adjusted_close: float | None
    volume: int | None


@dataclass
class NormalizedDividend:
    ex_date: date
    payment_date: date | None
    amount: float


@dataclass
class NormalizedSplit:
    split_date: date
    ratio_from: float
    ratio_to: float


@dataclass
class NormalizedCompanyData:
    ticker: str
    isin: str | None
    currency: str | None
    market_cap: float | None
    financial_statements: list[NormalizedFinancialStatement]
    price_history: list[NormalizedPricePoint]
    dividends: list[NormalizedDividend]
    splits: list[NormalizedSplit]


@dataclass
class NormalizationResult:
    data: NormalizedCompanyData
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_normalized(self) -> bool:
        return len(self.errors) == 0


@dataclass
class NormalizationService:
    """Normalize external payloads into a single internal V1 shape."""

    def normalize_company_payload(
        self,
        ticker: str,
        isin: str | None,
        currency: str | None,
        market_cap: float | None,
    ) -> NormalizationResult:
        normalized = NormalizedCompanyData(
            ticker=ticker,
            isin=isin,
            currency=currency,
            market_cap=market_cap,
            financial_statements=[],
            price_history=[],
            dividends=[],
            splits=[],
        )
        return NormalizationResult(data=normalized)
