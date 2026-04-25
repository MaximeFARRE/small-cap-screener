from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

import pandas as pd
import yfinance as yf

from src.models.financial_statement import PeriodType
from src.repositories.providers.base import (
    BaseProvider,
    CompanyInfo,
    CompanyProfile,
    DataFetchError,
    DividendData,
    FinancialData,
    MarketData,
    PriceRecord,
    SplitData,
    TickerNotFoundError,
)

_T = TypeVar("_T")

_MAX_ATTEMPTS: int = 3
_RETRY_DELAY: float = 2.0


def _with_retry(fn: Callable[[], _T]) -> _T:
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY)
    raise DataFetchError(f"Failed after {_MAX_ATTEMPTS} attempts") from last_exc


def _get_company_info(ticker: str) -> CompanyInfo:
    profile = _get_company_profile(ticker)
    return CompanyInfo(
        name=profile.name,
        sector=profile.sector,
        market=profile.market,
        currency=profile.currency,
    )


def _to_float(value: object) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _to_int(value: object) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _get_ticker_info(ticker: str) -> dict:
    return _with_retry(lambda: yf.Ticker(ticker).info)


def _ensure_ticker_exists(ticker: str) -> None:
    _get_company_profile(ticker)


def _get_company_profile(ticker: str) -> CompanyProfile:
    info = _get_ticker_info(ticker)
    name = info.get("longName") or info.get("shortName")
    if not name:
        raise TickerNotFoundError(f"No data found for ticker '{ticker}'")
    return CompanyProfile(
        ticker=ticker,
        name=name,
        sector=info.get("sector"),
        industry=info.get("industry"),
        market=info.get("exchange"),
        country=info.get("country"),
        currency=info.get("currency", "EUR"),
        website=info.get("website"),
    )


def _safe_float(row: pd.Series, key: str) -> float | None:
    val = row.get(key)
    if val is None or pd.isna(val):
        return None
    return float(val)


def _parse_price_row(ts: pd.Timestamp, row: pd.Series) -> PriceRecord:
    volume_raw = row.get("Volume")
    return PriceRecord(
        date=ts.date(),
        open=_safe_float(row, "Open"),
        high=_safe_float(row, "High"),
        low=_safe_float(row, "Low"),
        close=float(row["Close"]),
        adjusted_close=_safe_float(row, "Adj Close"),
        volume=(int(volume_raw) if volume_raw is not None and not pd.isna(volume_raw) else None),
    )


def _df_float(df: pd.DataFrame, row: str, col: object) -> float | None:
    try:
        val = df.loc[row, col]
        return None if pd.isna(val) else float(val)
    except (KeyError, TypeError):
        return None


def _parse_statement(
    col: pd.Timestamp,
    income: pd.DataFrame,
    balance: pd.DataFrame | None,
    cashflow: pd.DataFrame | None,
    shares: float | None,
) -> FinancialData:
    ebit = _df_float(income, "EBIT", col)
    ebitda = _df_float(income, "EBITDA", col)
    if ebitda is None and ebit is not None and cashflow is not None:
        da = _df_float(cashflow, "Depreciation And Amortization", col)
        if da is not None:
            ebitda = ebit + da
    total_debt = _df_float(balance, "Total Debt", col) if balance is not None else None
    cash = _df_float(balance, "Cash And Cash Equivalents", col) if balance is not None else None
    net_debt = (total_debt - cash) if total_debt is not None and cash is not None else None
    equity = _df_float(balance, "Stockholders Equity", col) if balance is not None else None
    return FinancialData(
        fiscal_year=col.year,
        period_type=PeriodType.ANNUAL,
        revenue=_df_float(income, "Total Revenue", col),
        ebit=ebit,
        ebitda=ebitda,
        net_income=_df_float(income, "Net Income", col),
        total_assets=(_df_float(balance, "Total Assets", col) if balance is not None else None),
        total_equity=equity,
        total_debt=total_debt,
        net_debt=net_debt,
        free_cash_flow=(_df_float(cashflow, "Free Cash Flow", col) if cashflow is not None else None),
        shares_outstanding=shares,
    )


def _get_financial_statements(ticker: str, years: int) -> list[FinancialData]:
    t = yf.Ticker(ticker)
    income: pd.DataFrame = _with_retry(lambda: t.financials)
    if income is None or income.empty:
        raise TickerNotFoundError(f"No financial data for ticker '{ticker}'")
    balance: pd.DataFrame | None = _with_retry(lambda: t.balance_sheet)
    cashflow: pd.DataFrame | None = _with_retry(lambda: t.cashflow)
    shares_raw = _get_ticker_info(ticker).get("sharesOutstanding")
    shares = float(shares_raw) if shares_raw else None
    cols = list(income.columns)[:years]
    return [_parse_statement(col, income, balance, cashflow, shares) for col in cols]


def _get_price_history(ticker: str, period: str) -> list[PriceRecord]:
    hist: pd.DataFrame = _with_retry(lambda: yf.Ticker(ticker).history(period=period, auto_adjust=False))
    if hist.empty:
        raise TickerNotFoundError(f"No price history for ticker '{ticker}'")
    return [_parse_price_row(ts, row) for ts, row in hist.iterrows()]


def _get_current_market_data(ticker: str) -> MarketData:
    info = _get_ticker_info(ticker)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    if current_price is None:
        raise TickerNotFoundError(f"No current market data for ticker '{ticker}'")

    return MarketData(
        ticker=ticker,
        current_price=float(current_price),
        previous_close=_to_float(info.get("previousClose") or info.get("regularMarketPreviousClose")),
        open=_to_float(info.get("open") or info.get("regularMarketOpen")),
        day_high=_to_float(info.get("dayHigh") or info.get("regularMarketDayHigh")),
        day_low=_to_float(info.get("dayLow") or info.get("regularMarketDayLow")),
        volume=_to_int(info.get("volume") or info.get("regularMarketVolume")),
        market_cap=_to_float(info.get("marketCap")),
        currency=info.get("currency"),
    )


def _parse_ratio(value: float) -> tuple[float, float]:
    ratio = float(value)
    if ratio <= 0:
        raise DataFetchError("Invalid split ratio returned by yfinance")
    if ratio >= 1:
        return 1.0, ratio
    return 1.0 / ratio, 1.0


def _get_dividends(ticker: str) -> list[DividendData]:
    dividends: pd.Series = _with_retry(lambda: yf.Ticker(ticker).dividends)
    if dividends is None or dividends.empty:
        _ensure_ticker_exists(ticker)
        return []

    records: list[DividendData] = []
    for ts, amount in dividends.items():
        if pd.isna(amount):
            continue
        records.append(
            DividendData(
                ex_date=pd.Timestamp(ts).date(),
                amount=float(amount),
                payment_date=None,
            )
        )
    return records


def _get_splits(ticker: str) -> list[SplitData]:
    splits: pd.Series = _with_retry(lambda: yf.Ticker(ticker).splits)
    if splits is None or splits.empty:
        _ensure_ticker_exists(ticker)
        return []

    records: list[SplitData] = []
    for ts, raw_ratio in splits.items():
        if pd.isna(raw_ratio):
            continue
        ratio_from, ratio_to = _parse_ratio(float(raw_ratio))
        records.append(
            SplitData(
                split_date=pd.Timestamp(ts).date(),
                ratio_from=ratio_from,
                ratio_to=ratio_to,
            )
        )
    return records


class YFinanceProvider(BaseProvider):
    def get_company_profile(self, ticker: str) -> CompanyProfile:
        return _get_company_profile(ticker)

    def get_company_info(self, ticker: str) -> CompanyInfo:
        return _get_company_info(ticker)

    def get_current_market_data(self, ticker: str) -> MarketData:
        return _get_current_market_data(ticker)

    def get_price_history(self, ticker: str, period: str = "5y") -> list[PriceRecord]:
        return _get_price_history(ticker, period)

    def get_dividends(self, ticker: str) -> list[DividendData]:
        return _get_dividends(ticker)

    def get_splits(self, ticker: str) -> list[SplitData]:
        return _get_splits(ticker)

    def get_financial_statements(self, ticker: str, years: int = 5) -> list[FinancialData]:
        return _get_financial_statements(ticker, years)

    def get_current_price(self, ticker: str) -> float:
        return self.get_current_market_data(ticker).current_price
