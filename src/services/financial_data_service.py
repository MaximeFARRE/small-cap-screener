from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.models.company import Company
from src.repositories import (
    company_repository,
    financial_statement_repository,
    market_data_repository,
    price_history_repository,
)
from src.repositories.database import get_session
from src.repositories.providers.base import (
    BaseProvider,
    CompanyProfile,
    DividendData,
    FinancialData,
    MarketData,
    PriceHistory,
    ProviderDataInconsistentError,
    ProviderError,
    SplitData,
    TickerNotFoundError,
)
from src.services.data_validation_service import DataValidationService
from src.services.normalization_service import NormalizationService, NormalizedCompanyData

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_LOGGER = logging.getLogger(__name__)


class FinancialDataServiceError(Exception):
    """Raised when the financial data service cannot complete one ingestion stage."""

    def __init__(self, stage: str, ticker: str, message: str, error_kind: str | None = None):
        self.stage = stage
        self.ticker = ticker
        self.message = message
        self.error_kind = error_kind
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
    error_kind: str | None = None
    stage: str | None = None
    warnings: list[str] = field(default_factory=list)
    provider_used: str | None = None


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
    normalization_service: NormalizationService = field(default_factory=NormalizationService)
    validation_service: DataValidationService = field(default_factory=DataValidationService)
    default_period: str = "5y"
    default_years: int = 5
    default_country: str = "France"
    default_max_market_cap: float = 2_000_000_000.0
    default_min_average_daily_volume: float | None = None
    provider_call_max_attempts: int = 3
    provider_retry_delay_seconds: float = 0.0
    offline_mode: bool = False

    def fetch_company_data(self, ticker: str) -> FetchedCompanyData:
        normalized_ticker = _normalize_ticker(ticker)
        if self.offline_mode:
            raise FinancialDataServiceError(
                "offline",
                normalized_ticker,
                "offline mode is enabled; provider fetch is disabled",
            )
        profile = (
            self._fetch_optional_provider_data(
                ticker=normalized_ticker,
                operation="company_profile",
                fallback=None,
                fetch_fn=lambda: self.provider.get_company_profile(normalized_ticker),
            )
            if hasattr(self.provider, "get_company_profile")
            else None
        )
        market_data = (
            self._fetch_optional_provider_data(
                ticker=normalized_ticker,
                operation="market_data",
                fallback=None,
                fetch_fn=lambda: self.provider.get_current_market_data(normalized_ticker),
            )
            if hasattr(self.provider, "get_current_market_data")
            else None
        )
        price_history = self._fetch_required_provider_data(
            ticker=normalized_ticker,
            operation="price_history",
            fetch_fn=lambda: self.provider.get_price_history(normalized_ticker, period=self.default_period),
        )
        financial_statements = self._fetch_optional_provider_data(
            ticker=normalized_ticker,
            operation="financial_statements",
            fallback=[],
            fetch_fn=lambda: self.provider.get_financial_statements(normalized_ticker, years=self.default_years),
        )
        dividends = (
            self._fetch_optional_provider_data(
                ticker=normalized_ticker,
                operation="dividends",
                fallback=[],
                fetch_fn=lambda: self.provider.get_dividends(normalized_ticker),
            )
            if hasattr(self.provider, "get_dividends")
            else []
        )
        splits = (
            self._fetch_optional_provider_data(
                ticker=normalized_ticker,
                operation="splits",
                fallback=[],
                fetch_fn=lambda: self.provider.get_splits(normalized_ticker),
            )
            if hasattr(self.provider, "get_splits")
            else []
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
                _LOGGER.warning(
                    (
                        "company skipped | stage=validate provider=%s offline_mode=%s "
                        "company_id=%s ticker=%s reason=not_found"
                    ),
                    self._provider_name(),
                    self.offline_mode,
                    company_id,
                    "",
                )
                return CompanyDataRefreshResult(
                    company_id=company_id,
                    ticker="",
                    success=False,
                    error="company not found",
                    stage="validate",
                    provider_used=self._provider_name(),
                )
            if _is_blank(company.ticker):
                _LOGGER.warning(
                    (
                        "company skipped | stage=validate provider=%s offline_mode=%s "
                        "company_id=%s ticker=%s reason=empty_ticker"
                    ),
                    self._provider_name(),
                    self.offline_mode,
                    company.id,
                    "",
                )
                return CompanyDataRefreshResult(
                    company_id=company.id,
                    ticker="",
                    success=False,
                    error="company ticker is empty",
                    stage="validate",
                    provider_used=self._provider_name(),
                )

            if self.offline_mode:
                return self._refresh_company_data_offline(session, company)

            try:
                fetched = self.fetch_company_data(company.ticker)
                normalization = self.normalization_service.normalize_company_payload(
                    ticker=fetched.ticker,
                    isin=company.isin,
                    currency=fetched.market_data.currency if fetched.market_data is not None else None,
                    market_cap=fetched.market_data.market_cap if fetched.market_data is not None else None,
                    financial_statements=fetched.financial_statements,
                    price_history=fetched.price_history,
                    dividends=fetched.dividends,
                    splits=fetched.splits,
                    profile_ticker=fetched.profile.ticker if fetched.profile is not None else None,
                    market_ticker=fetched.market_data.ticker if fetched.market_data is not None else None,
                    profile_currency=fetched.profile.currency if fetched.profile is not None else None,
                    market_currency=fetched.market_data.currency if fetched.market_data is not None else None,
                )
                if normalization.warnings:
                    _LOGGER.warning(
                        (
                            "normalization warning | stage=normalize provider=%s offline_mode=%s "
                            "company_id=%s ticker=%s warnings=%s"
                        ),
                        self._provider_name(),
                        self.offline_mode,
                        company.id,
                        company.ticker,
                        "; ".join(normalization.warnings),
                    )
                if not normalization.is_normalized:
                    _LOGGER.error(
                        (
                            "normalization blocked storage | stage=normalize provider=%s offline_mode=%s "
                            "company_id=%s ticker=%s errors=%s"
                        ),
                        self._provider_name(),
                        self.offline_mode,
                        company.id,
                        company.ticker,
                        "; ".join(normalization.errors),
                    )
                    return CompanyDataRefreshResult(
                        company_id=company.id,
                        ticker=company.ticker,
                        success=False,
                        error="; ".join(normalization.errors),
                        stage="normalize",
                        warnings=normalization.warnings,
                        provider_used=self._provider_name(),
                    )

                normalized_payload = _build_payload_from_normalized(normalization.data, fetched)
                validation = self.validation_service.validate_company_data(
                    ticker=normalized_payload.ticker,
                    profile=normalized_payload.profile,
                    market_data=normalized_payload.market_data,
                    price_history=normalized_payload.price_history,
                    financial_statements=normalized_payload.financial_statements,
                    dividends=normalized_payload.dividends,
                    splits=normalized_payload.splits,
                )
                combined_warnings = _merge_warnings(normalization.warnings, validation.warnings)
                if validation.warnings:
                    _LOGGER.warning(
                        (
                            "validation warning | stage=validate provider=%s offline_mode=%s "
                            "company_id=%s ticker=%s warnings=%s"
                        ),
                        self._provider_name(),
                        self.offline_mode,
                        company.id,
                        company.ticker,
                        "; ".join(validation.warnings),
                    )
                if not validation.is_valid:
                    _LOGGER.error(
                        (
                            "validation blocked storage | stage=validate provider=%s offline_mode=%s "
                            "company_id=%s ticker=%s errors=%s"
                        ),
                        self._provider_name(),
                        self.offline_mode,
                        company.id,
                        company.ticker,
                        "; ".join(validation.errors),
                    )
                    return CompanyDataRefreshResult(
                        company_id=company.id,
                        ticker=company.ticker,
                        success=False,
                        error="; ".join(validation.errors),
                        stage="validate",
                        warnings=combined_warnings,
                        provider_used=self._provider_name(),
                    )

                validated_data = validation.data
                sync = market_data_repository.sync_company_from_payload(
                    session,
                    company=company,
                    price_history=validated_data.price_history,
                    financial_statements=validated_data.financial_statements,
                    dividends=validated_data.dividends,
                    splits=validated_data.splits,
                )
                _apply_company_metadata(
                    company,
                    _validation_data_to_fetched_data(validated_data),
                )
                company_repository.update(session, company)
                _LOGGER.info(
                    (
                        "company storage succeeded | stage=store provider=%s offline_mode=%s "
                        "company_id=%s ticker=%s prices_added=%s statements_added=%s "
                        "dividends_added=%s splits_added=%s"
                    ),
                    self._provider_name(),
                    self.offline_mode,
                    sync.company_id,
                    company.ticker,
                    sync.prices_added,
                    sync.statements_added,
                    sync.dividends_added,
                    sync.splits_added,
                )
                return CompanyDataRefreshResult(
                    company_id=sync.company_id,
                    ticker=company.ticker,
                    success=True,
                    prices_added=sync.prices_added,
                    statements_added=sync.statements_added,
                    warnings=combined_warnings,
                    provider_used=self._provider_name(),
                )
            except FinancialDataServiceError as exc:
                _LOGGER.error(
                    ("company refresh failed | stage=%s provider=%s offline_mode=%s company_id=%s ticker=%s error=%s"),
                    exc.stage,
                    self._provider_name(),
                    self.offline_mode,
                    company.id,
                    company.ticker,
                    exc.message,
                )
                return CompanyDataRefreshResult(
                    company_id=company.id,
                    ticker=company.ticker,
                    success=False,
                    error=exc.message,
                    error_kind=exc.error_kind,
                    stage=exc.stage,
                    provider_used=self._provider_name(),
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
        _LOGGER.info(
            "universe refresh started | stage=refresh provider=%s offline_mode=%s total_companies=%s",
            self._provider_name(),
            self.offline_mode,
            len(company_ids),
        )

        results = [self.refresh_company_data(company_id) for company_id in company_ids]
        refreshed_count = sum(1 for result in results if result.success)
        failed_count = len(results) - refreshed_count
        _LOGGER.info(
            (
                "universe refresh completed | stage=refresh provider=%s offline_mode=%s "
                "total_companies=%s refreshed=%s failed=%s"
            ),
            self._provider_name(),
            self.offline_mode,
            len(company_ids),
            refreshed_count,
            failed_count,
        )
        return UniverseDataRefreshResult(
            total_companies=len(company_ids),
            refreshed_count=refreshed_count,
            failed_count=failed_count,
            results=results,
        )

    def _refresh_company_data_offline(self, session: Session, company: Company) -> CompanyDataRefreshResult:
        local_prices = price_history_repository.get_by_company(session, company.id)
        local_statements = financial_statement_repository.get_by_company(session, company.id)
        missing_data: list[str] = []
        if not local_prices:
            missing_data.append("price history")
        if not local_statements:
            missing_data.append("financial statements")
        if missing_data:
            missing_text = ", ".join(missing_data)
            _LOGGER.warning(
                (
                    "offline refresh blocked | stage=offline provider=%s offline_mode=%s "
                    "company_id=%s ticker=%s missing=%s"
                ),
                self._provider_name(),
                self.offline_mode,
                company.id,
                company.ticker,
                missing_text,
            )
            return CompanyDataRefreshResult(
                company_id=company.id,
                ticker=company.ticker,
                success=False,
                error=f"offline mode: missing local data ({missing_text})",
                stage="offline",
                provider_used=self._provider_name(),
            )
        _LOGGER.info(
            (
                "offline refresh succeeded | stage=offline provider=%s offline_mode=%s "
                "company_id=%s ticker=%s local_prices=%s local_statements=%s"
            ),
            self._provider_name(),
            self.offline_mode,
            company.id,
            company.ticker,
            len(local_prices),
            len(local_statements),
        )
        return CompanyDataRefreshResult(
            company_id=company.id,
            ticker=company.ticker,
            success=True,
            prices_added=0,
            statements_added=0,
            warnings=["offline mode: using local data only"],
            provider_used=self._provider_name(),
        )

    def _fetch_required_provider_data(
        self,
        *,
        ticker: str,
        operation: str,
        fetch_fn: Callable[[], object],
    ) -> object:
        success, result, error_kind = self._call_provider_with_retry(
            ticker=ticker,
            operation=operation,
            fetch_fn=fetch_fn,
        )
        if success:
            return result
        message = (
            f"{operation} failed after {self._effective_max_attempts()} attempts: {result}"
            if result is not None
            else f"{operation} failed after {self._effective_max_attempts()} attempts"
        )
        raise FinancialDataServiceError("fetch", ticker, message, error_kind=error_kind)

    def _fetch_optional_provider_data(
        self,
        *,
        ticker: str,
        operation: str,
        fallback: object,
        fetch_fn: Callable[[], object],
    ) -> object:
        success, result, _error_kind = self._call_provider_with_retry(
            ticker=ticker,
            operation=operation,
            fetch_fn=fetch_fn,
        )
        if success:
            return result
        _LOGGER.warning(
            (
                "provider fallback used | stage=fetch provider=%s offline_mode=%s "
                "ticker=%s operation=%s attempts=%s error=%s"
            ),
            self._provider_name(),
            self.offline_mode,
            ticker,
            operation,
            self._effective_max_attempts(),
            result,
        )
        return fallback

    def _call_provider_with_retry(
        self,
        *,
        ticker: str,
        operation: str,
        fetch_fn: Callable[[], object],
    ) -> tuple[bool, object | Exception, str | None]:
        last_error: Exception | None = None
        max_attempts = self._effective_max_attempts()
        for attempt in range(1, max_attempts + 1):
            try:
                return True, fetch_fn(), None
            except ProviderError as exc:
                last_error = exc
            except Exception as exc:  # pragma: no cover - defensive wrapper
                last_error = exc
            if attempt < max_attempts:
                _LOGGER.warning(
                    (
                        "provider retry scheduled | stage=fetch provider=%s offline_mode=%s "
                        "ticker=%s operation=%s attempt=%s/%s error=%s"
                    ),
                    self._provider_name(),
                    self.offline_mode,
                    ticker,
                    operation,
                    attempt,
                    max_attempts,
                    last_error,
                )
                if self.provider_retry_delay_seconds > 0:
                    time.sleep(self.provider_retry_delay_seconds)
        _LOGGER.error(
            (
                "provider fetch failed after retries | stage=fetch provider=%s offline_mode=%s "
                "ticker=%s operation=%s attempts=%s error=%s"
            ),
            self._provider_name(),
            self.offline_mode,
            ticker,
            operation,
            max_attempts,
            last_error,
        )
        final_error = last_error if last_error is not None else RuntimeError("provider call failed")
        return False, final_error, _classify_provider_error(final_error)

    def _effective_max_attempts(self) -> int:
        return max(1, self.provider_call_max_attempts)

    def _provider_name(self) -> str:
        return self.provider.source_name


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


def _build_payload_from_normalized(
    normalized: NormalizedCompanyData, fetched: FetchedCompanyData
) -> FetchedCompanyData:
    profile = _normalized_profile(normalized, fetched.profile)
    market_data = _normalized_market_data(normalized, fetched.market_data)
    return FetchedCompanyData(
        ticker=normalized.ticker,
        profile=profile,
        market_data=market_data,
        price_history=[
            PriceHistory(
                date=record.date,
                open=record.open,
                high=record.high,
                low=record.low,
                close=record.close,
                adjusted_close=record.adjusted_close,
                volume=record.volume,
                source="normalized",
                fetched_at=None,
            )
            for record in normalized.price_history
        ],
        financial_statements=[
            FinancialData(
                fiscal_year=record.fiscal_year,
                period_type=record.period_type,
                revenue=record.revenue,
                ebit=record.ebit,
                ebitda=record.ebitda,
                net_income=record.net_income,
                total_assets=record.total_assets,
                total_equity=record.total_equity,
                total_debt=record.total_debt,
                net_debt=record.net_debt,
                free_cash_flow=record.free_cash_flow,
                shares_outstanding=record.shares_outstanding,
            )
            for record in normalized.financial_statements
        ],
        dividends=[
            DividendData(
                ex_date=record.ex_date,
                amount=record.amount,
                payment_date=record.payment_date,
                source="normalized",
                fetched_at=None,
            )
            for record in normalized.dividends
        ],
        splits=[
            SplitData(
                split_date=record.split_date,
                ratio_from=record.ratio_from,
                ratio_to=record.ratio_to,
                source="normalized",
                fetched_at=None,
            )
            for record in normalized.splits
        ],
    )


def _normalized_profile(normalized: NormalizedCompanyData, profile: CompanyProfile | None) -> CompanyProfile | None:
    if profile is None:
        return None
    return CompanyProfile(
        ticker=normalized.ticker,
        name=profile.name,
        sector=profile.sector,
        industry=profile.industry,
        market=profile.market,
        country=profile.country,
        currency=normalized.currency if normalized.currency is not None else profile.currency,
        website=profile.website,
        source=profile.source,
        fetched_at=profile.fetched_at,
    )


def _normalized_market_data(normalized: NormalizedCompanyData, market_data: MarketData | None) -> MarketData | None:
    if market_data is None:
        return None
    return MarketData(
        ticker=normalized.ticker,
        current_price=market_data.current_price,
        previous_close=market_data.previous_close,
        open=market_data.open,
        day_high=market_data.day_high,
        day_low=market_data.day_low,
        volume=market_data.volume,
        market_cap=normalized.market_cap,
        currency=normalized.currency,
        source=market_data.source,
        fetched_at=market_data.fetched_at,
    )


def _validation_data_to_fetched_data(validated_data) -> FetchedCompanyData:
    return FetchedCompanyData(
        ticker=validated_data.ticker,
        profile=validated_data.profile,
        market_data=validated_data.market_data,
        price_history=validated_data.price_history,
        financial_statements=validated_data.financial_statements,
        dividends=validated_data.dividends,
        splits=validated_data.splits,
    )


def _classify_provider_error(exc: Exception) -> str:
    """Map a provider exception to a short error-kind string for UI consumption."""
    if isinstance(exc, TickerNotFoundError):
        return "not_found"
    if isinstance(exc, ProviderDataInconsistentError):
        return "data_inconsistent"
    return "provider_error"


def _merge_warnings(*warning_lists: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for warnings in warning_lists:
        for warning in warnings:
            if warning in seen:
                continue
            seen.add(warning)
            merged.append(warning)
    return merged
