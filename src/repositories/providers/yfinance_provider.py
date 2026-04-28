from __future__ import annotations

import copy
import datetime as dt
import json
import logging
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import pandas as pd
import yfinance as yf

from src.models.financial_statement import PeriodType
from src.repositories.providers.base import (
    AnalystData,
    BaseProvider,
    CompanyInfo,
    CompanyProfile,
    DataFetchError,
    DividendData,
    FinancialData,
    MarketData,
    PriceHistory,
    SplitData,
    TickerNotFoundError,
)

_T = TypeVar("_T")

_MAX_ATTEMPTS: int = 3
_RETRY_DELAY: float = 2.0
_SOURCE_NAME: str = "yfinance"
_DEFAULT_CACHE_MAX_AGE: dt.timedelta = dt.timedelta(days=1)
_LOGGER = logging.getLogger(__name__)


@dataclass
class _ProviderCacheEntry:
    value: object
    refreshed_at: dt.datetime


def _fetched_at_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _with_retry(fn: Callable[[], _T], operation: str) -> _T:
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            attempt_number = attempt + 1
            if attempt < _MAX_ATTEMPTS - 1:
                _LOGGER.warning(
                    "provider retry scheduled: operation=%s attempt=%s/%s error=%s",
                    operation,
                    attempt_number,
                    _MAX_ATTEMPTS,
                    exc,
                )
                time.sleep(_RETRY_DELAY)
            else:
                _LOGGER.error(
                    "provider fetch failed after retries: operation=%s attempts=%s error=%s",
                    operation,
                    _MAX_ATTEMPTS,
                    exc,
                )
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


def _parse_info_date(val: object) -> dt.datetime | None:
    if val is None or pd.isna(val):
        return None
    try:
        return dt.datetime.fromtimestamp(int(val), dt.UTC)
    except (ValueError, TypeError, OverflowError):
        return None


def _get_ticker_info(ticker: str) -> dict:
    return _with_retry(lambda: yf.Ticker(ticker).info, operation=f"ticker_info:{ticker}")


def _ensure_ticker_exists(ticker: str) -> None:
    _get_company_profile(ticker)


def _get_company_profile(ticker: str) -> CompanyProfile:
    info = _get_ticker_info(ticker)
    name = info.get("longName") or info.get("shortName")
    if not name:
        raise TickerNotFoundError(f"No data found for ticker '{ticker}'")
    fetched_at = _fetched_at_now()
    raw_employees = info.get("fullTimeEmployees")
    return CompanyProfile(
        ticker=ticker,
        name=name,
        sector=info.get("sector"),
        industry=info.get("industry"),
        market=info.get("exchange"),
        country=info.get("country"),
        currency=info.get("currency", "EUR"),
        website=info.get("website"),
        business_summary=info.get("longBusinessSummary") or None,
        isin=info.get("isin") or None,
        full_time_employees=_to_int(raw_employees) if raw_employees is not None else None,
        city=info.get("city") or None,
        phone=info.get("phone") or None,
        source=_SOURCE_NAME,
        fetched_at=fetched_at,
    )


def _safe_float(row: pd.Series, key: str) -> float | None:
    val = row.get(key)
    if val is None or pd.isna(val):
        return None
    return float(val)


def _parse_price_row(ts: pd.Timestamp, row: pd.Series, fetched_at: dt.datetime) -> PriceHistory:
    volume_raw = row.get("Volume")
    return PriceHistory(
        date=ts.date(),
        open=_safe_float(row, "Open"),
        high=_safe_float(row, "High"),
        low=_safe_float(row, "Low"),
        close=float(row["Close"]),
        adjusted_close=_safe_float(row, "Adj Close"),
        volume=(int(volume_raw) if volume_raw is not None and not pd.isna(volume_raw) else None),
        source=_SOURCE_NAME,
        fetched_at=fetched_at,
    )


def _df_float(df: pd.DataFrame, row: str, col: object) -> float | None:
    try:
        val = df.loc[row, col]
        return None if pd.isna(val) else float(val)
    except (KeyError, TypeError):
        return None


def _df_float_multi(df: pd.DataFrame, rows: list[str], col: object) -> float | None:
    if df is None:
        return None
    for row in rows:
        val = _df_float(df, row, col)
        if val is not None:
            return val
    return None


def _parse_statement(
    col: pd.Timestamp,
    income: pd.DataFrame,
    balance: pd.DataFrame | None,
    cashflow: pd.DataFrame | None,
    shares: float | None,
) -> FinancialData:
    ebit = _df_float_multi(income, ["EBIT", "Operating Income"], col)
    ebitda = _df_float(income, "EBITDA", col)
    if ebitda is None and ebit is not None and cashflow is not None:
        da = _df_float_multi(cashflow, ["Depreciation And Amortization", "Depreciation & Amortization"], col)
        if da is not None:
            ebitda = ebit + da

    total_debt = _df_float(balance, "Total Debt", col) if balance is not None else None
    cash = (
        _df_float_multi(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"], col)
        if balance is not None
        else None
    )
    net_debt = (total_debt - cash) if total_debt is not None and cash is not None else None
    equity = _df_float(balance, "Stockholders Equity", col) if balance is not None else None
    current_assets = _df_float(balance, "Current Assets", col) if balance is not None else None
    current_liabilities = _df_float(balance, "Current Liabilities", col) if balance is not None else None

    gross_profit = _df_float(income, "Gross Profit", col)
    revenue = _df_float(income, "Total Revenue", col)
    if gross_profit is None and revenue is not None:
        cost_of_rev = _df_float(income, "Cost Of Revenue", col)
        if cost_of_rev is not None:
            gross_profit = revenue - cost_of_rev

    # Interest expense - some providers use negative values
    interest = _df_float_multi(income, ["Interest Expense", "Interest Expense Non Operating"], col)
    if interest is not None:
        interest = abs(interest)

    return FinancialData(
        fiscal_year=col.year,
        period_type=PeriodType.ANNUAL,
        revenue=revenue,
        ebit=ebit,
        ebitda=ebitda,
        net_income=_df_float(income, "Net Income", col),
        total_assets=(_df_float(balance, "Total Assets", col) if balance is not None else None),
        total_equity=equity,
        total_debt=total_debt,
        net_debt=net_debt,
        free_cash_flow=(_df_float(cashflow, "Free Cash Flow", col) if cashflow is not None else None),
        shares_outstanding=shares,
        gross_profit=gross_profit,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        interest_expense=interest,
    )


def _get_financial_statements(ticker: str, years: int) -> list[FinancialData]:
    t = yf.Ticker(ticker)
    income: pd.DataFrame = _with_retry(lambda: t.financials, operation=f"financials:{ticker}")
    if income is None or income.empty:
        raise TickerNotFoundError(f"No financial data for ticker '{ticker}'")
    balance: pd.DataFrame | None = _with_retry(lambda: t.balance_sheet, operation=f"balance_sheet:{ticker}")
    cashflow: pd.DataFrame | None = _with_retry(lambda: t.cashflow, operation=f"cashflow:{ticker}")
    shares_raw = _get_ticker_info(ticker).get("sharesOutstanding")
    shares = float(shares_raw) if shares_raw else None
    cols = list(income.columns)[:years]
    return [_parse_statement(col, income, balance, cashflow, shares) for col in cols]


def _get_price_history(ticker: str, period: str) -> list[PriceHistory]:
    hist: pd.DataFrame = _with_retry(
        lambda: yf.Ticker(ticker).history(period=period, auto_adjust=False),
        operation=f"price_history:{ticker}:{period}",
    )
    if hist.empty:
        raise TickerNotFoundError(f"No price history for ticker '{ticker}'")
    fetched_at = _fetched_at_now()
    return [_parse_price_row(ts, row, fetched_at) for ts, row in hist.iterrows()]


def _get_current_market_data(ticker: str) -> MarketData:
    info = _get_ticker_info(ticker)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    if current_price is None:
        raise TickerNotFoundError(f"No current market data for ticker '{ticker}'")
    fetched_at = _fetched_at_now()

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
        source=_SOURCE_NAME,
        fetched_at=fetched_at,
    )


def _parse_ratio(value: float) -> tuple[float, float]:
    ratio = float(value)
    if ratio <= 0:
        raise DataFetchError("Invalid split ratio returned by yfinance")
    if ratio >= 1:
        return 1.0, ratio
    return 1.0 / ratio, 1.0


def _get_dividends(ticker: str) -> list[DividendData]:
    dividends: pd.Series = _with_retry(lambda: yf.Ticker(ticker).dividends, operation=f"dividends:{ticker}")
    if dividends is None or dividends.empty:
        _ensure_ticker_exists(ticker)
        return []

    fetched_at = _fetched_at_now()
    records: list[DividendData] = []
    for ts, amount in dividends.items():
        if pd.isna(amount):
            continue
        records.append(
            DividendData(
                ex_date=pd.Timestamp(ts).date(),
                amount=float(amount),
                payment_date=None,
                source=_SOURCE_NAME,
                fetched_at=fetched_at,
            )
        )
    return records


def _get_splits(ticker: str) -> list[SplitData]:
    splits: pd.Series = _with_retry(lambda: yf.Ticker(ticker).splits, operation=f"splits:{ticker}")
    if splits is None or splits.empty:
        _ensure_ticker_exists(ticker)
        return []

    fetched_at = _fetched_at_now()
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
                source=_SOURCE_NAME,
                fetched_at=fetched_at,
            )
        )
    return records


def _get_analyst_data(ticker: str) -> AnalystData:
    info = _get_ticker_info(ticker)
    fetched_at = _fetched_at_now()
    raw_opinions = info.get("numberOfAnalystOpinions")
    return AnalystData(
        ticker=ticker,
        enterprise_value=_to_float(info.get("enterpriseValue")),
        beta=_to_float(info.get("beta")),
        forward_pe=_to_float(info.get("forwardPE")),
        target_price_mean=_to_float(info.get("targetMeanPrice")),
        target_price_high=_to_float(info.get("targetHighPrice")),
        target_price_low=_to_float(info.get("targetLowPrice")),
        recommendation_key=info.get("recommendationKey") or None,
        number_of_analyst_opinions=(_to_int(raw_opinions) if raw_opinions is not None else None),
        # Fundamentals
        gross_margins=_to_float(info.get("grossMargins")),
        operating_margins=_to_float(info.get("operatingMargins")),
        profit_margins=_to_float(info.get("profitMargins")),
        roe=_to_float(info.get("returnOnEquity")),
        roa=_to_float(info.get("returnOnAssets")),
        current_ratio=_to_float(info.get("currentRatio")),
        quick_ratio=_to_float(info.get("quickRatio")),
        payout_ratio=_to_float(info.get("payoutRatio")),
        # Shares & Volume
        shares_outstanding=_to_float(info.get("sharesOutstanding")),
        float_shares=_to_float(info.get("floatShares")),
        average_volume=_to_float(info.get("averageVolume")),
        # Dividends
        dividend_rate=_to_float(info.get("dividendRate")),
        dividend_yield=_to_float(info.get("dividendYield")),
        ex_dividend_date=_parse_info_date(info.get("exDividendDate")),
        five_year_avg_dividend_yield=_to_float(info.get("fiveYearAvgDividendYield")),
        source=_SOURCE_NAME,
        fetched_at=fetched_at,
    )


def _search_by_isin(isin: str) -> str | None:
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={isin}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            quotes = data.get("quotes", [])
            if quotes and "symbol" in quotes[0]:
                return quotes[0]["symbol"]
    except Exception as exc:
        _LOGGER.warning("ISIN search failed for %s: %s", isin, exc)
    return None


class YFinanceProvider(BaseProvider):
    def __init__(self, cache_max_age: dt.timedelta | None = None) -> None:
        self._cache_max_age = _DEFAULT_CACHE_MAX_AGE if cache_max_age is None else cache_max_age
        self._cache: dict[tuple[str, str, str], _ProviderCacheEntry] = {}

    def _get_cached_or_fetch(
        self,
        *,
        ticker: str,
        data_type: str,
        variant: str,
        fetch_fn: Callable[[], _T],
    ) -> _T:
        normalized_ticker = ticker.strip().upper()
        cache_key = (normalized_ticker, data_type, variant)
        now = _fetched_at_now()

        cached = self._cache.get(cache_key)
        if cached is not None and now - cached.refreshed_at <= self._cache_max_age:
            return copy.deepcopy(cached.value)

        value = fetch_fn()
        self._cache[cache_key] = _ProviderCacheEntry(value=copy.deepcopy(value), refreshed_at=now)
        return value

    def get_company_profile(self, ticker: str) -> CompanyProfile:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="company_profile",
            variant="default",
            fetch_fn=lambda: _get_company_profile(ticker),
        )

    def get_company_info(self, ticker: str) -> CompanyInfo:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="company_info",
            variant="default",
            fetch_fn=lambda: _get_company_info(ticker),
        )

    def get_current_market_data(self, ticker: str) -> MarketData:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="market_data",
            variant="default",
            fetch_fn=lambda: _get_current_market_data(ticker),
        )

    def get_price_history(self, ticker: str, period: str = "5y") -> list[PriceHistory]:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="price_history",
            variant=period,
            fetch_fn=lambda: _get_price_history(ticker, period),
        )

    def get_dividends(self, ticker: str) -> list[DividendData]:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="dividends",
            variant="default",
            fetch_fn=lambda: _get_dividends(ticker),
        )

    def get_splits(self, ticker: str) -> list[SplitData]:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="splits",
            variant="default",
            fetch_fn=lambda: _get_splits(ticker),
        )

    def get_financial_statements(self, ticker: str, years: int = 5) -> list[FinancialData]:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="financial_statements",
            variant=str(years),
            fetch_fn=lambda: _get_financial_statements(ticker, years),
        )

    def get_analyst_data(self, ticker: str) -> AnalystData:
        return self._get_cached_or_fetch(
            ticker=ticker,
            data_type="analyst_data",
            variant="default",
            fetch_fn=lambda: _get_analyst_data(ticker),
        )

    def get_current_price(self, ticker: str) -> float:
        return self.get_current_market_data(ticker).current_price

    def search_by_isin(self, isin: str) -> str | None:
        return self._get_cached_or_fetch(
            ticker=isin,
            data_type="isin_search",
            variant="default",
            fetch_fn=lambda: _search_by_isin(isin),
        )
