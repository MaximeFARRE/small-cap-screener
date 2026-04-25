from __future__ import annotations

from dataclasses import dataclass

from src.repositories.providers.base import (
    BaseProvider,
    CompanyProfile,
    DividendData,
    FinancialData,
    MarketData,
    PriceHistory,
    ProviderError,
    SplitData,
)


class FinancialDataServiceError(Exception):
    """Raised when the financial data service cannot complete one ingestion stage."""

    def __init__(self, stage: str, ticker: str, message: str):
        self.stage = stage
        self.ticker = ticker
        self.message = message
        super().__init__(f"[{stage}] {ticker}: {message}")


@dataclass
class FetchedCompanyData:
    ticker: str
    profile: CompanyProfile | None
    market_data: MarketData | None
    price_history: list[PriceHistory]
    financial_statements: list[FinancialData]
    dividends: list[DividendData]
    splits: list[SplitData]


@dataclass
class FinancialDataService:
    provider: BaseProvider
    default_period: str = "5y"
    default_years: int = 5

    def fetch_company_data(self, ticker: str) -> FetchedCompanyData:
        normalized_ticker = _normalize_ticker(ticker)
        try:
            profile = (
                self.provider.get_company_profile(normalized_ticker)
                if hasattr(self.provider, "get_company_profile")
                else None
            )
            market_data = (
                self.provider.get_current_market_data(normalized_ticker)
                if hasattr(self.provider, "get_current_market_data")
                else None
            )
            price_history = self.provider.get_price_history(normalized_ticker, period=self.default_period)
            financial_statements = self.provider.get_financial_statements(normalized_ticker, years=self.default_years)
            dividends = (
                self.provider.get_dividends(normalized_ticker) if hasattr(self.provider, "get_dividends") else []
            )
            splits = self.provider.get_splits(normalized_ticker) if hasattr(self.provider, "get_splits") else []
        except ProviderError as exc:
            raise FinancialDataServiceError("fetch", normalized_ticker, str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise FinancialDataServiceError("fetch", normalized_ticker, str(exc)) from exc

        if not price_history and not financial_statements:
            raise FinancialDataServiceError(
                "validate",
                normalized_ticker,
                "provider returned no price history and no financial statements",
            )
        return FetchedCompanyData(
            ticker=normalized_ticker,
            profile=profile,
            market_data=market_data,
            price_history=price_history,
            financial_statements=financial_statements,
            dividends=dividends,
            splits=splits,
        )


def _normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not normalized:
        raise FinancialDataServiceError("validate", ticker, "ticker is empty")
    return normalized
