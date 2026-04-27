from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from src.repositories.providers.base import DividendData, FinancialData, PriceHistory, SplitData

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
        financial_statements: list[FinancialData] | None = None,
        price_history: list[PriceHistory] | None = None,
        dividends: list[DividendData] | None = None,
        splits: list[SplitData] | None = None,
        profile_ticker: str | None = None,
        market_ticker: str | None = None,
        profile_currency: str | None = None,
        market_currency: str | None = None,
    ) -> NormalizationResult:
        errors: list[str] = []
        warnings: list[str] = []
        normalized_ticker = _normalize_ticker(ticker, errors)
        _validate_ticker_consistency(normalized_ticker, profile_ticker, market_ticker, errors, warnings)
        normalized_isin = _normalize_isin(isin, errors, warnings)
        normalized_currency = _resolve_currency(
            primary=currency,
            profile_currency=profile_currency,
            market_currency=market_currency,
            errors=errors,
            warnings=warnings,
        )
        normalized_market_cap = _normalize_market_cap(market_cap, errors)
        normalized_financials = _normalize_financial_statements(financial_statements, errors, warnings)
        normalized_prices = _normalize_price_history(price_history, errors, warnings)
        normalized_dividends = _normalize_dividends(dividends, errors, warnings)
        normalized_splits = _normalize_splits(splits, errors, warnings)

        normalized = NormalizedCompanyData(
            ticker=normalized_ticker,
            isin=normalized_isin,
            currency=normalized_currency,
            market_cap=normalized_market_cap,
            financial_statements=normalized_financials,
            price_history=normalized_prices,
            dividends=normalized_dividends,
            splits=normalized_splits,
        )
        return NormalizationResult(data=normalized, errors=errors, warnings=warnings)


def _normalize_ticker(value: str, errors: list[str]) -> str:
    normalized = value.strip().upper() if isinstance(value, str) else ""
    if not normalized:
        errors.append("ticker is empty")
    return normalized


def _validate_ticker_consistency(
    canonical_ticker: str,
    profile_ticker: str | None,
    market_ticker: str | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    if not canonical_ticker:
        return
    for source_name, source_ticker in (("profile", profile_ticker), ("market_data", market_ticker)):
        if source_ticker is None:
            continue
        normalized_source = source_ticker.strip().upper()
        if not normalized_source:
            warnings.append(f"{source_name} ticker is empty")
            continue
        if normalized_source != canonical_ticker:
            errors.append(f"{source_name} ticker is inconsistent with requested ticker")


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


def _resolve_currency(
    primary: str | None,
    profile_currency: str | None,
    market_currency: str | None,
    errors: list[str],
    warnings: list[str],
) -> str | None:
    normalized_primary = _normalize_currency(
        primary,
        errors,
        warnings,
        source_name="currency",
        emit_missing_warning=False,
    )
    normalized_profile = _normalize_currency(
        profile_currency,
        errors,
        warnings,
        source_name="profile_currency",
        emit_missing_warning=False,
    )
    normalized_market = _normalize_currency(
        market_currency,
        errors,
        warnings,
        source_name="market_currency",
        emit_missing_warning=False,
    )

    candidates = [value for value in (normalized_primary, normalized_profile, normalized_market) if value is not None]
    if not candidates:
        warnings.append("currency is missing")
        return None
    first = candidates[0]
    inconsistent = [value for value in candidates[1:] if value != first]
    if inconsistent:
        errors.append("currencies are inconsistent across sources")
    return first


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


def _normalize_financial_statements(
    records: list[FinancialData] | None,
    errors: list[str],
    warnings: list[str],
) -> list[NormalizedFinancialStatement]:
    if records is None:
        warnings.append("financial_statements is missing")
        return []
    normalized: list[NormalizedFinancialStatement] = []
    for index, record in enumerate(records):
        if not isinstance(record, FinancialData):
            errors.append(f"financial_statements[{index}] is corrupted")
            continue
        if record.fiscal_year <= 0:
            errors.append(f"financial_statements[{index}] has invalid fiscal_year")
            continue
        period_type = record.period_type.strip().lower()
        fiscal_date = _to_fiscal_date(record.fiscal_year, period_type, warnings)
        normalized.append(
            NormalizedFinancialStatement(
                fiscal_year=int(record.fiscal_year),
                period_type=period_type,
                fiscal_date=fiscal_date,
                revenue=_normalize_nullable_float(record.revenue, f"financial_statements[{index}].revenue", errors),
                ebitda=_normalize_nullable_float(record.ebitda, f"financial_statements[{index}].ebitda", errors),
                ebit=_normalize_nullable_float(record.ebit, f"financial_statements[{index}].ebit", errors),
                net_income=_normalize_nullable_float(
                    record.net_income, f"financial_statements[{index}].net_income", errors
                ),
                total_assets=_normalize_nullable_float(
                    record.total_assets, f"financial_statements[{index}].total_assets", errors
                ),
                total_equity=_normalize_nullable_float(
                    record.total_equity, f"financial_statements[{index}].total_equity", errors
                ),
                total_debt=_normalize_nullable_float(
                    record.total_debt, f"financial_statements[{index}].total_debt", errors
                ),
                net_debt=_normalize_nullable_float(record.net_debt, f"financial_statements[{index}].net_debt", errors),
                free_cash_flow=_normalize_nullable_float(
                    record.free_cash_flow, f"financial_statements[{index}].free_cash_flow", errors
                ),
                shares_outstanding=_normalize_nullable_float(
                    record.shares_outstanding, f"financial_statements[{index}].shares_outstanding", errors
                ),
                gross_profit=_normalize_nullable_float(
                    record.gross_profit, f"financial_statements[{index}].gross_profit", errors
                ),
                current_assets=_normalize_nullable_float(
                    record.current_assets, f"financial_statements[{index}].current_assets", errors
                ),
                current_liabilities=_normalize_nullable_float(
                    record.current_liabilities, f"financial_statements[{index}].current_liabilities", errors
                ),
                interest_expense=_normalize_nullable_float(
                    record.interest_expense, f"financial_statements[{index}].interest_expense", errors
                ),
            )
        )
    return sorted(normalized, key=lambda statement: statement.fiscal_date)


def _normalize_currency(
    value: str | None,
    errors: list[str],
    warnings: list[str],
    source_name: str = "currency",
    emit_missing_warning: bool = True,
) -> str | None:
    if value is None:
        if emit_missing_warning:
            warnings.append(f"{source_name} is missing")
        return None
    raw = value.strip().upper()
    if not raw:
        if emit_missing_warning:
            warnings.append(f"{source_name} is missing")
        return None
    normalized = _CURRENCY_ALIASES.get(raw, raw)
    if len(normalized) != 3 or not normalized.isalpha():
        errors.append(f"{source_name} format is invalid")
        return None
    return normalized


def _normalize_price_history(
    records: list[PriceHistory] | None,
    errors: list[str],
    warnings: list[str],
) -> list[NormalizedPricePoint]:
    if records is None:
        warnings.append("price_history is missing")
        return []
    dedup: dict[date, NormalizedPricePoint] = {}
    for index, record in enumerate(records):
        if not isinstance(record, PriceHistory):
            errors.append(f"price_history[{index}] is corrupted")
            continue
        normalized_date = _normalize_date(record.date, f"price_history[{index}].date", errors)
        if normalized_date is None:
            continue
        normalized = NormalizedPricePoint(
            date=normalized_date,
            open=_normalize_nullable_float(record.open, f"price_history[{index}].open", errors),
            high=_normalize_nullable_float(record.high, f"price_history[{index}].high", errors),
            low=_normalize_nullable_float(record.low, f"price_history[{index}].low", errors),
            close=_normalize_required_float(record.close, f"price_history[{index}].close", errors),
            adjusted_close=_normalize_nullable_float(
                record.adjusted_close, f"price_history[{index}].adjusted_close", errors
            ),
            volume=_normalize_nullable_int(record.volume, f"price_history[{index}].volume", errors),
        )
        if normalized_date in dedup:
            warnings.append(f"price_history duplicate date normalized: {normalized_date.isoformat()}")
        dedup[normalized_date] = normalized
    return [dedup[key] for key in sorted(dedup.keys())]


def _normalize_dividends(
    records: list[DividendData] | None,
    errors: list[str],
    warnings: list[str],
) -> list[NormalizedDividend]:
    if records is None:
        warnings.append("dividends is missing")
        return []
    dedup: dict[date, NormalizedDividend] = {}
    for index, record in enumerate(records):
        if not isinstance(record, DividendData):
            errors.append(f"dividends[{index}] is corrupted")
            continue
        ex_date = _normalize_date(record.ex_date, f"dividends[{index}].ex_date", errors)
        if ex_date is None:
            continue
        payment_date = _normalize_date(record.payment_date, f"dividends[{index}].payment_date", errors, allow_none=True)
        normalized = NormalizedDividend(
            ex_date=ex_date,
            payment_date=payment_date,
            amount=_normalize_required_float(record.amount, f"dividends[{index}].amount", errors),
        )
        if ex_date in dedup:
            warnings.append(f"dividends duplicate ex_date normalized: {ex_date.isoformat()}")
        dedup[ex_date] = normalized
    return [dedup[key] for key in sorted(dedup.keys())]


def _normalize_splits(
    records: list[SplitData] | None,
    errors: list[str],
    warnings: list[str],
) -> list[NormalizedSplit]:
    if records is None:
        warnings.append("splits is missing")
        return []
    dedup: dict[date, NormalizedSplit] = {}
    for index, record in enumerate(records):
        if not isinstance(record, SplitData):
            errors.append(f"splits[{index}] is corrupted")
            continue
        split_date = _normalize_date(record.split_date, f"splits[{index}].split_date", errors)
        if split_date is None:
            continue
        normalized = NormalizedSplit(
            split_date=split_date,
            ratio_from=_normalize_required_float(record.ratio_from, f"splits[{index}].ratio_from", errors),
            ratio_to=_normalize_required_float(record.ratio_to, f"splits[{index}].ratio_to", errors),
        )
        if split_date in dedup:
            warnings.append(f"splits duplicate split_date normalized: {split_date.isoformat()}")
        dedup[split_date] = normalized
    return [dedup[key] for key in sorted(dedup.keys())]


def _to_fiscal_date(fiscal_year: int, period_type: str, warnings: list[str]) -> date:
    if period_type == "annual":
        return date(fiscal_year, 12, 31)
    if period_type == "half_year":
        return date(fiscal_year, 6, 30)
    warnings.append(f"unknown period_type normalized as annual date: {period_type}")
    return date(fiscal_year, 12, 31)


def _normalize_nullable_float(value: float | None, field_name: str, errors: list[str]) -> float | None:
    if value is None:
        return None
    normalized = float(value)
    if not math.isfinite(normalized):
        errors.append(f"{field_name} must be finite")
        return None
    return normalized


def _normalize_required_float(value: float, field_name: str, errors: list[str]) -> float:
    normalized = _normalize_nullable_float(value, field_name, errors)
    if normalized is None:
        errors.append(f"{field_name} is required")
        return 0.0
    return normalized


def _normalize_nullable_int(value: int | None, field_name: str, errors: list[str]) -> int | None:
    if value is None:
        return None
    normalized = int(value)
    if normalized < 0:
        errors.append(f"{field_name} cannot be negative")
        return None
    return normalized


def _normalize_date(
    value: object,
    field_name: str,
    errors: list[str],
    allow_none: bool = False,
) -> date | None:
    if value is None:
        if allow_none:
            return None
        errors.append(f"{field_name} is required")
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).date()
        return value.date()
    if isinstance(value, str):
        parsed = _parse_datetime_string(value)
        if parsed is None:
            errors.append(f"{field_name} has invalid date format")
            return None
        return parsed
    errors.append(f"{field_name} has unsupported date type")
    return None


def _parse_datetime_string(value: str) -> date | None:
    raw = value.strip()
    if not raw:
        return None
    iso_candidate = raw.replace("Z", "+00:00")
    try:
        parsed_dt = datetime.fromisoformat(iso_candidate)
        if parsed_dt.tzinfo is not None:
            return parsed_dt.astimezone(UTC).date()
        return parsed_dt.date()
    except ValueError:
        pass
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None
