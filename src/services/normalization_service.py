from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date

_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{10}$")
_CURRENCY_ALIASES: dict[str, str] = {
    "EURO": "EUR",
    "EUROS": "EUR",
    "US DOLLAR": "USD",
    "US DOLLARS": "USD",
}


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
        errors: list[str] = []
        warnings: list[str] = []
        normalized_ticker = _normalize_ticker(ticker, errors)
        normalized_isin = _normalize_isin(isin, errors, warnings)
        normalized_currency = _normalize_currency(currency, errors, warnings)
        normalized_market_cap = _normalize_market_cap(market_cap, errors)

        normalized = NormalizedCompanyData(
            ticker=normalized_ticker,
            isin=normalized_isin,
            currency=normalized_currency,
            market_cap=normalized_market_cap,
            financial_statements=[],
            price_history=[],
            dividends=[],
            splits=[],
        )
        return NormalizationResult(data=normalized, errors=errors, warnings=warnings)


def _normalize_ticker(value: str, errors: list[str]) -> str:
    normalized = value.strip().upper() if isinstance(value, str) else ""
    if not normalized:
        errors.append("ticker is empty")
    return normalized


def _normalize_isin(value: str | None, errors: list[str], warnings: list[str]) -> str | None:
    if value is None:
        warnings.append("isin is missing")
        return None
    normalized = value.strip().upper()
    if not normalized:
        warnings.append("isin is missing")
        return None
    if not _ISIN_PATTERN.match(normalized):
        errors.append("isin format is invalid")
    return normalized


def _normalize_currency(value: str | None, errors: list[str], warnings: list[str]) -> str | None:
    if value is None:
        warnings.append("currency is missing")
        return None
    raw = value.strip().upper()
    if not raw:
        warnings.append("currency is missing")
        return None
    normalized = _CURRENCY_ALIASES.get(raw, raw)
    if len(normalized) != 3 or not normalized.isalpha():
        errors.append("currency format is invalid")
        return None
    return normalized


def _normalize_market_cap(value: float | None, errors: list[str]) -> float | None:
    if value is None:
        return None
    normalized = float(value)
    if not math.isfinite(normalized):
        errors.append("market_cap must be a finite number")
        return None
    if normalized < 0:
        errors.append("market_cap cannot be negative")
        return None
    return normalized
