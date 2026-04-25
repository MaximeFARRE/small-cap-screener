from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from src.repositories.providers.base import (
    CompanyProfile,
    DividendData,
    FinancialData,
    MarketData,
    PriceHistory,
    SplitData,
)

_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


@dataclass
class ValidatedCompanyData:
    ticker: str
    profile: CompanyProfile | None
    market_data: MarketData | None
    price_history: list[PriceHistory]
    financial_statements: list[FinancialData]
    dividends: list[DividendData]
    splits: list[SplitData]


@dataclass
class DataValidationResult:
    data: ValidatedCompanyData
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass
class DataValidationService:
    def validate_company_data(
        self,
        ticker: str,
        profile: CompanyProfile | None,
        market_data: MarketData | None,
        price_history: list[PriceHistory],
        financial_statements: list[FinancialData],
        dividends: list[DividendData],
        splits: list[SplitData],
    ) -> DataValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        normalized_ticker = ticker.strip().upper() if isinstance(ticker, str) else ""
        if not normalized_ticker:
            errors.append("ticker is empty")

        validated_price_history = _validate_price_history(price_history, errors)
        validated_financial_statements = _validate_financial_statements(financial_statements, errors)
        validated_dividends = _validate_dividends(dividends, errors)
        validated_splits = _validate_splits(splits, errors)
        _validate_market_data(normalized_ticker, market_data, errors)
        _validate_currency_consistency(profile, market_data, errors, warnings)

        if not validated_price_history:
            warnings.append("price_history is empty")
        if not validated_financial_statements:
            warnings.append("financial_statements is empty")
        if not validated_dividends:
            warnings.append("dividends is empty")
        if not validated_splits:
            warnings.append("splits is empty")

        if not validated_price_history and not validated_financial_statements:
            errors.append("both price_history and financial_statements are empty")

        validated = ValidatedCompanyData(
            ticker=normalized_ticker,
            profile=profile,
            market_data=market_data,
            price_history=validated_price_history,
            financial_statements=validated_financial_statements,
            dividends=validated_dividends,
            splits=validated_splits,
        )
        return DataValidationResult(data=validated, errors=errors, warnings=warnings)


def _is_valid_date(value: object) -> bool:
    return isinstance(value, date)


def _validate_price_history(price_history: object, errors: list[str]) -> list[PriceHistory]:
    validated: list[PriceHistory] = []
    if not isinstance(price_history, list):
        errors.append("price_history is corrupted (not a list)")
        return validated
    for index, record in enumerate(price_history):
        if not isinstance(record, PriceHistory):
            errors.append(f"price_history[{index}] is corrupted")
            continue
        if not _is_valid_date(record.date):
            errors.append(f"price_history[{index}] has invalid date")
        if record.close <= 0:
            errors.append(f"price_history[{index}] has non-positive close")
        if record.open is not None and record.open <= 0:
            errors.append(f"price_history[{index}] has non-positive open")
        if record.high is not None and record.high <= 0:
            errors.append(f"price_history[{index}] has non-positive high")
        if record.low is not None and record.low <= 0:
            errors.append(f"price_history[{index}] has non-positive low")
        if record.volume is not None and record.volume < 0:
            errors.append(f"price_history[{index}] has negative volume")
        validated.append(record)
    return validated


def _validate_financial_statements(financial_statements: object, errors: list[str]) -> list[FinancialData]:
    validated: list[FinancialData] = []
    if not isinstance(financial_statements, list):
        errors.append("financial_statements is corrupted (not a list)")
        return validated
    for index, statement in enumerate(financial_statements):
        if not isinstance(statement, FinancialData):
            errors.append(f"financial_statements[{index}] is corrupted")
            continue
        if statement.fiscal_year <= 0:
            errors.append(f"financial_statements[{index}] has invalid fiscal_year")
        if not statement.period_type:
            errors.append(f"financial_statements[{index}] has empty period_type")
        validated.append(statement)
    return validated


def _validate_dividends(dividends: object, errors: list[str]) -> list[DividendData]:
    validated: list[DividendData] = []
    if not isinstance(dividends, list):
        errors.append("dividends is corrupted (not a list)")
        return validated
    for index, dividend in enumerate(dividends):
        if not isinstance(dividend, DividendData):
            errors.append(f"dividends[{index}] is corrupted")
            continue
        if not _is_valid_date(dividend.ex_date):
            errors.append(f"dividends[{index}] has invalid ex_date")
        if dividend.payment_date is not None and not _is_valid_date(dividend.payment_date):
            errors.append(f"dividends[{index}] has invalid payment_date")
        if dividend.amount <= 0:
            errors.append(f"dividends[{index}] has non-positive amount")
        validated.append(dividend)
    return validated


def _validate_splits(splits: object, errors: list[str]) -> list[SplitData]:
    validated: list[SplitData] = []
    if not isinstance(splits, list):
        errors.append("splits is corrupted (not a list)")
        return validated
    for index, split in enumerate(splits):
        if not isinstance(split, SplitData):
            errors.append(f"splits[{index}] is corrupted")
            continue
        if not _is_valid_date(split.split_date):
            errors.append(f"splits[{index}] has invalid split_date")
        if split.ratio_from <= 0 or split.ratio_to <= 0:
            errors.append(f"splits[{index}] has invalid ratio")
        validated.append(split)
    return validated


def _validate_market_data(input_ticker: str, market_data: MarketData | None, errors: list[str]) -> None:
    if market_data is None:
        return
    normalized_market_ticker = market_data.ticker.strip().upper() if market_data.ticker is not None else ""
    if not normalized_market_ticker:
        errors.append("market_data has empty ticker")
    elif input_ticker and normalized_market_ticker != input_ticker:
        errors.append("market_data ticker does not match requested ticker")

    if market_data.current_price <= 0:
        errors.append("market_data has non-positive current_price")
    if market_data.previous_close is not None and market_data.previous_close <= 0:
        errors.append("market_data has non-positive previous_close")
    if market_data.open is not None and market_data.open <= 0:
        errors.append("market_data has non-positive open")
    if market_data.day_high is not None and market_data.day_high <= 0:
        errors.append("market_data has non-positive day_high")
    if market_data.day_low is not None and market_data.day_low <= 0:
        errors.append("market_data has non-positive day_low")
    if market_data.volume is not None and market_data.volume < 0:
        errors.append("market_data has negative volume")
    if market_data.market_cap is not None and market_data.market_cap <= 0:
        errors.append("market_data has non-positive market_cap")
    if market_data.currency is not None and not _CURRENCY_PATTERN.match(market_data.currency):
        errors.append("market_data has invalid currency")


def _validate_currency_consistency(
    profile: CompanyProfile | None,
    market_data: MarketData | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    profile_currency = profile.currency if profile is not None else None
    market_currency = market_data.currency if market_data is not None else None

    if profile_currency is not None and not _CURRENCY_PATTERN.match(profile_currency):
        errors.append("profile has invalid currency")
    if profile_currency and market_currency and profile_currency != market_currency:
        errors.append("profile currency and market_data currency are inconsistent")
    if profile_currency is None and market_currency is None:
        warnings.append("currency is missing in both profile and market_data")
