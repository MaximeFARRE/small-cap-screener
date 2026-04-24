from __future__ import annotations

import time
from typing import Callable, TypeVar

import pandas as pd
import yfinance as yf

from src.models.financial_statement import PeriodType
from src.repositories.providers.base import (
    BaseProvider,
    CompanyInfo,
    DataFetchError,
    FinancialData,
    PriceRecord,
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
    info: dict = _with_retry(lambda: yf.Ticker(ticker).info)
    name = info.get("longName") or info.get("shortName")
    if not name:
        raise TickerNotFoundError(f"No data found for ticker '{ticker}'")
    return CompanyInfo(
        name=name,
        sector=info.get("sector"),
        market=info.get("exchange"),
        currency=info.get("currency", "EUR"),
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
        volume=int(volume_raw) if volume_raw is not None and not pd.isna(volume_raw) else None,
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
        total_assets=_df_float(balance, "Total Assets", col) if balance is not None else None,
        total_equity=equity,
        total_debt=total_debt,
        net_debt=net_debt,
        free_cash_flow=_df_float(cashflow, "Free Cash Flow", col) if cashflow is not None else None,
        shares_outstanding=shares,
    )


def _get_financial_statements(ticker: str, years: int) -> list[FinancialData]:
    t = yf.Ticker(ticker)
    income: pd.DataFrame = _with_retry(lambda: t.financials)
    if income is None or income.empty:
        raise TickerNotFoundError(f"No financial data for ticker '{ticker}'")
    balance: pd.DataFrame | None = _with_retry(lambda: t.balance_sheet)
    cashflow: pd.DataFrame | None = _with_retry(lambda: t.cashflow)
    shares_raw = _with_retry(lambda: t.info).get("sharesOutstanding")
    shares = float(shares_raw) if shares_raw else None
    cols = list(income.columns)[:years]
    return [_parse_statement(col, income, balance, cashflow, shares) for col in cols]


def _get_price_history(ticker: str, period: str) -> list[PriceRecord]:
    hist: pd.DataFrame = _with_retry(
        lambda: yf.Ticker(ticker).history(period=period, auto_adjust=False)
    )
    if hist.empty:
        raise TickerNotFoundError(f"No price history for ticker '{ticker}'")
    return [_parse_price_row(ts, row) for ts, row in hist.iterrows()]


class YFinanceProvider(BaseProvider):
    def get_company_info(self, ticker: str) -> CompanyInfo:
        return _get_company_info(ticker)

    def get_price_history(self, ticker: str, period: str = "5y") -> list[PriceRecord]:
        return _get_price_history(ticker, period)

    def get_financial_statements(self, ticker: str, years: int = 5) -> list[FinancialData]:
        return _get_financial_statements(ticker, years)
