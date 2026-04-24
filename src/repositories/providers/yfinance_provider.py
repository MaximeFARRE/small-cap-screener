from __future__ import annotations

import time
from typing import Callable, TypeVar

import pandas as pd
import yfinance as yf

from src.repositories.providers.base import (
    BaseProvider,
    CompanyInfo,
    DataFetchError,
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


class YFinanceProvider(BaseProvider):
    def get_company_info(self, ticker: str) -> CompanyInfo:
        return _get_company_info(ticker)
