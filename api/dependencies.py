from functools import lru_cache

from fastapi import HTTPException
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.repositories import company_repository
from src.repositories.database import get_session
from src.repositories.providers.yfinance_provider import YFinanceProvider
from src.services.company_detail_service import CompanyDetailService
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.peer_comparison_service import PeerComparisonService
from src.services.scoring_service import ScoringService
from src.services.screening_service import ScreeningService
from src.services.watchlist_service import WatchlistService


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./data/screener.db"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# ---------------------------------------------------------------------------
# Service singletons
# Services are stateless (they create sessions on demand), so singletons work.
# ---------------------------------------------------------------------------


@lru_cache
def get_scoring_service() -> ScoringService:
    return ScoringService()


@lru_cache
def get_kpi_service() -> KpiSnapshotService:
    return KpiSnapshotService(scoring_service=get_scoring_service())


@lru_cache
def get_screening_service() -> ScreeningService:
    return ScreeningService(
        scoring_service=get_scoring_service(),
        kpi_snapshot_service=get_kpi_service(),
    )


@lru_cache
def get_company_detail_service() -> CompanyDetailService:
    return CompanyDetailService()


@lru_cache
def get_watchlist_service() -> WatchlistService:
    return WatchlistService(
        scoring_service=get_scoring_service(),
        kpi_snapshot_service=get_kpi_service(),
    )


@lru_cache
def get_peer_service() -> PeerComparisonService:
    return PeerComparisonService(screening_service=get_screening_service())


@lru_cache
def get_financial_data_service() -> FinancialDataService:
    return FinancialDataService(provider=YFinanceProvider())


# ---------------------------------------------------------------------------
# Company lookup helper — translates ticker → company_id for routers.
# Raises 404 HTTPException when the ticker is unknown.
# ---------------------------------------------------------------------------


def get_company_id(ticker: str) -> int:
    with get_session() as session:
        company = company_repository.get_by_ticker(session, ticker)
    if company is None:
        raise HTTPException(status_code=404, detail=f"Company not found: {ticker}")
    return company.id
