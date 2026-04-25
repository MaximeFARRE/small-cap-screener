from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.models.company import Company
from src.repositories import company_repository, market_data_repository
from src.repositories.database import get_session
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

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


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
class CompanyDataRefreshResult:
    company_id: int
    ticker: str
    success: bool
    prices_added: int = 0
    statements_added: int = 0
    error: str | None = None
    stage: str | None = None


@dataclass
class UniverseDataRefreshResult:
    total_companies: int
    refreshed_count: int
    failed_count: int
    results: list[CompanyDataRefreshResult]


@dataclass
class FinancialDataService:
    provider: BaseProvider
    session_scope_factory: SessionScopeFactory = get_session
    default_period: str = "5y"
    default_years: int = 5
    default_country: str = "France"
    default_max_market_cap: float = 2_000_000_000.0
    default_min_average_daily_volume: float | None = None

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

    def refresh_company_data(self, company_id: int) -> CompanyDataRefreshResult:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                return CompanyDataRefreshResult(
                    company_id=company_id,
                    ticker="",
                    success=False,
                    error="company not found",
                    stage="validate",
                )
            if _is_blank(company.ticker):
                return CompanyDataRefreshResult(
                    company_id=company.id,
                    ticker="",
                    success=False,
                    error="company ticker is empty",
                    stage="validate",
                )
            if _is_blank(company.isin):
                return CompanyDataRefreshResult(
                    company_id=company.id,
                    ticker=company.ticker,
                    success=False,
                    error="company isin is empty",
                    stage="validate",
                )

            try:
                fetched = self.fetch_company_data(company.ticker)
                sync = market_data_repository.sync_company(
                    session,
                    self.provider,
                    ticker=company.ticker,
                    isin=company.isin,
                    period=self.default_period,
                    years=self.default_years,
                )
                _apply_company_metadata(company, fetched)
                company_repository.update(session, company)
                return CompanyDataRefreshResult(
                    company_id=sync.company_id,
                    ticker=company.ticker,
                    success=True,
                    prices_added=sync.prices_added,
                    statements_added=sync.statements_added,
                )
            except FinancialDataServiceError as exc:
                return CompanyDataRefreshResult(
                    company_id=company.id,
                    ticker=company.ticker,
                    success=False,
                    error=exc.message,
                    stage=exc.stage,
                )

    def refresh_universe_data(self) -> UniverseDataRefreshResult:
        with self.session_scope_factory() as session:
            companies = company_repository.get_investable_universe(
                session,
                max_market_cap=self.default_max_market_cap,
                min_average_daily_volume=self.default_min_average_daily_volume,
                country=self.default_country,
            )
            company_ids = [company.id for company in companies]

        results = [self.refresh_company_data(company_id) for company_id in company_ids]
        refreshed_count = sum(1 for result in results if result.success)
        failed_count = len(results) - refreshed_count
        return UniverseDataRefreshResult(
            total_companies=len(company_ids),
            refreshed_count=refreshed_count,
            failed_count=failed_count,
            results=results,
        )


def _normalize_ticker(ticker: str) -> str:
    normalized = ticker.strip().upper()
    if not normalized:
        raise FinancialDataServiceError("validate", ticker, "ticker is empty")
    return normalized


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _apply_company_metadata(company: Company, fetched: FetchedCompanyData) -> None:
    if fetched.profile is not None:
        company.country = fetched.profile.country
        company.sector = fetched.profile.sector
    if fetched.market_data is not None:
        company.market_cap = fetched.market_data.market_cap
        company.average_daily_volume = fetched.market_data.volume
        if fetched.market_data.currency is not None:
            company.currency = fetched.market_data.currency
