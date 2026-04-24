from __future__ import annotations

import time
from typing import Callable, TypeVar

import pandas as pd
import yfinance as yf

from src.repositories.providers.base import (
    BaseProvider,
    CompanyInfo,
    DataFetchError,
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
