from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.repositories.providers.base import TickerNotFoundError
from src.repositories.providers.yfinance_provider import YFinanceProvider

TICKER = "TTE.PA"


def _mock_ticker(info=None, history=None, financials=None, balance_sheet=None, cashflow=None):
    t = MagicMock()
    t.info = info or {}
    t.history.return_value = history if history is not None else pd.DataFrame()
    t.financials = financials if financials is not None else pd.DataFrame()
    t.balance_sheet = balance_sheet if balance_sheet is not None else pd.DataFrame()
    t.cashflow = cashflow if cashflow is not None else pd.DataFrame()
    return t


# --- get_company_info ---


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_company_info_returns_parsed_data(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        info={
            "longName": "TotalEnergies SE",
            "sector": "Energy",
            "exchange": "PAR",
            "currency": "EUR",
        }
    )
    info = YFinanceProvider().get_company_info(TICKER)
    assert info.name == "TotalEnergies SE"
    assert info.sector == "Energy"
    assert info.currency == "EUR"


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_company_info_raises_when_no_name(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(info={})
    with pytest.raises(TickerNotFoundError):
        YFinanceProvider().get_company_info(TICKER)


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
@patch("src.repositories.providers.yfinance_provider.time.sleep")
def test_get_company_info_retries_on_error(mock_sleep, mock_ticker_cls):
    mock_ticker_cls.side_effect = [
        RuntimeError("network"),
        RuntimeError("network"),
        _mock_ticker(info={"longName": "TotalEnergies SE", "currency": "EUR"}),
    ]
    info = YFinanceProvider().get_company_info(TICKER)
    assert info.name == "TotalEnergies SE"
    assert mock_sleep.call_count == 2


# --- get_price_history ---


def _make_history_df() -> pd.DataFrame:
    idx = pd.DatetimeIndex([pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")])
    return pd.DataFrame(
        {
            "Open": [50.0, 51.0],
            "High": [52.0, 53.0],
            "Low": [49.0, 50.0],
            "Close": [51.5, 52.0],
            "Adj Close": [51.5, 52.0],
            "Volume": [100_000, 120_000],
        },
        index=idx,
    )


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_price_history_returns_records(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(history=_make_history_df())
    records = YFinanceProvider().get_price_history(TICKER, period="1mo")
    assert len(records) == 2
    assert records[0].date == date(2024, 1, 2)
    assert records[0].close == 51.5
    assert records[0].volume == 100_000


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_price_history_raises_on_empty(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(history=pd.DataFrame())
    with pytest.raises(TickerNotFoundError):
        YFinanceProvider().get_price_history(TICKER)


# --- get_financial_statements ---


def _make_financials_df() -> pd.DataFrame:
    col = pd.Timestamp("2023-12-31")
    return pd.DataFrame(
        {
            col: {
                "Total Revenue": 200_000_000.0,
                "EBIT": 20_000_000.0,
                "EBITDA": 30_000_000.0,
                "Net Income": 15_000_000.0,
            }
        }
    )


def _make_balance_df() -> pd.DataFrame:
    col = pd.Timestamp("2023-12-31")
    return pd.DataFrame(
        {
            col: {
                "Total Assets": 500_000_000.0,
                "Stockholders Equity": 150_000_000.0,
                "Total Debt": 80_000_000.0,
                "Cash And Cash Equivalents": 30_000_000.0,
            }
        }
    )


def _make_cashflow_df() -> pd.DataFrame:
    col = pd.Timestamp("2023-12-31")
    return pd.DataFrame({col: {"Free Cash Flow": 18_000_000.0}})


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_financial_statements_returns_parsed_data(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        info={"sharesOutstanding": 2_000_000},
        financials=_make_financials_df(),
        balance_sheet=_make_balance_df(),
        cashflow=_make_cashflow_df(),
    )
    stmts = YFinanceProvider().get_financial_statements(TICKER, years=1)
    assert len(stmts) == 1
    s = stmts[0]
    assert s.fiscal_year == 2023
    assert s.revenue == 200_000_000.0
    assert s.net_debt == pytest.approx(50_000_000.0)
    assert s.shares_outstanding == 2_000_000.0


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_financial_statements_raises_on_empty(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(financials=pd.DataFrame())
    with pytest.raises(TickerNotFoundError):
        YFinanceProvider().get_financial_statements(TICKER)


# --- get_current_price ---


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_current_price(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(info={"currentPrice": 55.30})
    assert YFinanceProvider().get_current_price(TICKER) == pytest.approx(55.30)


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_current_price_fallback_to_regular_market(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(info={"regularMarketPrice": 54.80})
    assert YFinanceProvider().get_current_price(TICKER) == pytest.approx(54.80)


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_current_price_raises_when_missing(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(info={})
    with pytest.raises(TickerNotFoundError):
        YFinanceProvider().get_current_price(TICKER)
