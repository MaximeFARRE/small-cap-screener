from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.repositories.providers.base import DataFetchError, TickerNotFoundError
from src.repositories.providers.yfinance_provider import YFinanceProvider

TICKER = "TTE.PA"


def _mock_ticker(
    info=None, history=None, financials=None, balance_sheet=None, cashflow=None, dividends=None, splits=None
):
    t = MagicMock()
    t.info = info or {}
    t.history.return_value = history if history is not None else pd.DataFrame()
    t.financials = financials if financials is not None else pd.DataFrame()
    t.balance_sheet = balance_sheet if balance_sheet is not None else pd.DataFrame()
    t.cashflow = cashflow if cashflow is not None else pd.DataFrame()
    t.dividends = dividends if dividends is not None else pd.Series(dtype="float64")
    t.splits = splits if splits is not None else pd.Series(dtype="float64")
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
def test_get_company_profile_returns_parsed_data(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        info={
            "longName": "TotalEnergies SE",
            "sector": "Energy",
            "industry": "Oil & Gas Integrated",
            "exchange": "PAR",
            "country": "France",
            "currency": "EUR",
            "website": "https://totalenergies.com",
        }
    )
    profile = YFinanceProvider().get_company_profile(TICKER)
    assert profile.ticker == TICKER
    assert profile.name == "TotalEnergies SE"
    assert profile.industry == "Oil & Gas Integrated"
    assert profile.country == "France"


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


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
@patch("src.repositories.providers.yfinance_provider.time.sleep")
def test_get_company_info_logs_retry_and_final_failure(mock_sleep, mock_ticker_cls, caplog):
    mock_ticker_cls.side_effect = RuntimeError("network")

    with caplog.at_level(logging.WARNING, logger="src.repositories.providers.yfinance_provider"):
        with pytest.raises(DataFetchError):
            YFinanceProvider().get_company_info(TICKER)

    retry_logs = [record for record in caplog.records if "provider retry scheduled" in record.message]
    final_error_logs = [record for record in caplog.records if "provider fetch failed after retries" in record.message]
    assert len(retry_logs) == 2
    assert len(final_error_logs) == 1
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


# --- get_dividends / get_splits ---


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_dividends_returns_records(mock_ticker_cls):
    dividends = pd.Series(
        data=[0.74, 0.79],
        index=pd.DatetimeIndex([pd.Timestamp("2024-04-01"), pd.Timestamp("2024-05-01")]),
    )
    mock_ticker_cls.return_value = _mock_ticker(
        info={"longName": "TotalEnergies SE", "currency": "EUR"},
        dividends=dividends,
    )
    records = YFinanceProvider().get_dividends(TICKER)
    assert len(records) == 2
    assert records[0].ex_date == date(2024, 4, 1)
    assert records[1].amount == pytest.approx(0.79)


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_dividends_returns_empty_when_no_events(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        info={"longName": "TotalEnergies SE", "currency": "EUR"},
        dividends=pd.Series(dtype="float64"),
    )
    records = YFinanceProvider().get_dividends(TICKER)
    assert records == []


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_dividends_raises_on_unknown_ticker(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(info={}, dividends=pd.Series(dtype="float64"))
    with pytest.raises(TickerNotFoundError):
        YFinanceProvider().get_dividends(TICKER)


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_splits_returns_records(mock_ticker_cls):
    splits = pd.Series(
        data=[2.0, 0.2],
        index=pd.DatetimeIndex([pd.Timestamp("2020-01-10"), pd.Timestamp("2024-07-01")]),
    )
    mock_ticker_cls.return_value = _mock_ticker(
        info={"longName": "TotalEnergies SE", "currency": "EUR"},
        splits=splits,
    )
    records = YFinanceProvider().get_splits(TICKER)
    assert len(records) == 2
    assert records[0].ratio_from == pytest.approx(1.0)
    assert records[0].ratio_to == pytest.approx(2.0)
    assert records[1].ratio_from == pytest.approx(5.0)
    assert records[1].ratio_to == pytest.approx(1.0)


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_splits_returns_empty_when_no_events(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        info={"longName": "TotalEnergies SE", "currency": "EUR"},
        splits=pd.Series(dtype="float64"),
    )
    records = YFinanceProvider().get_splits(TICKER)
    assert records == []


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_splits_raises_on_unknown_ticker(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(info={}, splits=pd.Series(dtype="float64"))
    with pytest.raises(TickerNotFoundError):
        YFinanceProvider().get_splits(TICKER)


# --- get_current_market_data / get_current_price ---


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_current_market_data(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(
        info={
            "currentPrice": 55.30,
            "previousClose": 54.80,
            "open": 55.00,
            "dayHigh": 56.0,
            "dayLow": 54.5,
            "volume": 500_000,
            "marketCap": 120_000_000_000,
            "currency": "EUR",
        }
    )
    data = YFinanceProvider().get_current_market_data(TICKER)
    assert data.current_price == pytest.approx(55.30)
    assert data.previous_close == pytest.approx(54.80)
    assert data.volume == 500_000
    assert data.currency == "EUR"


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_get_current_market_data_raises_when_missing(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(info={})
    with pytest.raises(TickerNotFoundError):
        YFinanceProvider().get_current_market_data(TICKER)


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


@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_price_history_cache_hit_reuses_recent_data(mock_ticker_cls):
    mock_ticker_cls.return_value = _mock_ticker(history=_make_history_df())
    provider = YFinanceProvider(cache_max_age=timedelta(days=1))

    first = provider.get_price_history(TICKER, period="1mo")
    second = provider.get_price_history(TICKER, period="1mo")

    assert len(first) == 2
    assert len(second) == 2
    assert mock_ticker_cls.call_count == 1


@patch("src.repositories.providers.yfinance_provider._fetched_at_now")
@patch("src.repositories.providers.yfinance_provider.yf.Ticker")
def test_price_history_cache_miss_for_stale_data(mock_ticker_cls, mock_now):
    mock_ticker_cls.return_value = _mock_ticker(history=_make_history_df())
    base_time = datetime(2026, 1, 10, 10, 0, 0, tzinfo=UTC)
    mock_now.side_effect = [
        base_time,
        base_time,
        base_time + timedelta(days=2),
        base_time + timedelta(days=2),
    ]
    provider = YFinanceProvider(cache_max_age=timedelta(days=1))

    provider.get_price_history(TICKER, period="1mo")
    provider.get_price_history(TICKER, period="1mo")

    assert mock_ticker_cls.call_count == 2
