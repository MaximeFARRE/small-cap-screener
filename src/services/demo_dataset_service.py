from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.dividend import Dividend
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.kpi_snapshot import KpiSnapshot
from src.models.price_history import PriceHistory
from src.models.screening_snapshot import ScreeningSnapshot
from src.models.split import Split
from src.models.watchlist_entry import (
    WATCHLIST_STATUS_CONVICTION,
    WATCHLIST_STATUS_REJECTED,
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_WATCHING,
    WatchlistEntry,
)
from src.repositories import (
    company_repository,
    financial_statement_repository,
    price_history_repository,
    watchlist_repository,
)
from src.repositories.database import get_session, init_db
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.screening_service import ScreeningService, UniverseScreeningFilters
from src.services.universe_service import UniverseService
from src.services.watchlist_service import WatchlistService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]

DEMO_DEFAULT_SEED_PATH = Path("data/demo/seed_universe_fr_small_caps.csv")
DEMO_SNAPSHOT_DATE = date(2026, 3, 31)
DEMO_SCREENING_SNAPSHOT_NAME = "demo baseline ranking"
_DEMO_BASELINE_FILTERS = UniverseScreeningFilters(sort_by="rank")


@dataclass(frozen=True)
class DemoStatementPayload:
    fiscal_year: int
    revenue: float
    ebit: float
    ebitda: float
    net_income: float
    total_assets: float
    total_equity: float
    total_debt: float
    net_debt: float
    free_cash_flow: float
    shares_outstanding: float


@dataclass(frozen=True)
class DemoCompanyProfile:
    market_cap: float
    average_daily_volume: float
    latest_price_close: float | None
    latest_statement: DemoStatementPayload | None
    previous_statement: DemoStatementPayload | None


@dataclass(frozen=True)
class DemoWatchlistProfile:
    status: str
    notes: str
    is_excluded: bool


@dataclass(frozen=True)
class DemoDatasetSummary:
    total_companies: int
    scored_companies: int
    unscored_companies: int
    watchlist_entries: int
    excluded_entries: int
    ranking_snapshot_id: int
    top_ranked_tickers: tuple[str, ...]


_PROFILES_BY_TICKER: dict[str, DemoCompanyProfile] = {
    "ALPS.PA": DemoCompanyProfile(
        market_cap=210_000_000.0,
        average_daily_volume=320_000.0,
        latest_price_close=24.0,
        latest_statement=DemoStatementPayload(
            2024,
            240_000_000.0,
            28_000_000.0,
            36_000_000.0,
            20_000_000.0,
            350_000_000.0,
            160_000_000.0,
            40_000_000.0,
            20_000_000.0,
            18_000_000.0,
            8_000_000.0,
        ),
        previous_statement=DemoStatementPayload(
            2023,
            216_000_000.0,
            25_000_000.0,
            32_000_000.0,
            18_000_000.0,
            330_000_000.0,
            150_000_000.0,
            45_000_000.0,
            25_000_000.0,
            16_000_000.0,
            8_000_000.0,
        ),
    ),
    "BRET.PA": DemoCompanyProfile(
        market_cap=180_000_000.0,
        average_daily_volume=260_000.0,
        latest_price_close=18.0,
        latest_statement=DemoStatementPayload(
            2024,
            190_000_000.0,
            18_000_000.0,
            24_000_000.0,
            12_000_000.0,
            300_000_000.0,
            140_000_000.0,
            55_000_000.0,
            36_000_000.0,
            9_000_000.0,
            10_000_000.0,
        ),
        previous_statement=DemoStatementPayload(
            2023,
            183_000_000.0,
            17_000_000.0,
            22_800_000.0,
            11_000_000.0,
            290_000_000.0,
            135_000_000.0,
            58_000_000.0,
            38_000_000.0,
            8_500_000.0,
            10_000_000.0,
        ),
    ),
    "CAMA.PA": DemoCompanyProfile(
        market_cap=125_000_000.0,
        average_daily_volume=140_000.0,
        latest_price_close=10.0,
        latest_statement=DemoStatementPayload(
            2024,
            170_000_000.0,
            12_000_000.0,
            18_000_000.0,
            8_000_000.0,
            260_000_000.0,
            90_000_000.0,
            70_000_000.0,
            45_000_000.0,
            4_000_000.0,
            12_000_000.0,
        ),
        previous_statement=DemoStatementPayload(
            2023,
            180_000_000.0,
            14_000_000.0,
            20_000_000.0,
            9_000_000.0,
            255_000_000.0,
            92_000_000.0,
            68_000_000.0,
            42_000_000.0,
            4_500_000.0,
            12_000_000.0,
        ),
    ),
    "DORD.PA": DemoCompanyProfile(
        market_cap=260_000_000.0,
        average_daily_volume=210_000.0,
        latest_price_close=42.0,
        latest_statement=DemoStatementPayload(
            2024,
            150_000_000.0,
            15_000_000.0,
            20_000_000.0,
            9_000_000.0,
            240_000_000.0,
            110_000_000.0,
            22_000_000.0,
            6_000_000.0,
            6_000_000.0,
            6_000_000.0,
        ),
        previous_statement=DemoStatementPayload(
            2023,
            120_000_000.0,
            12_000_000.0,
            15_000_000.0,
            7_000_000.0,
            220_000_000.0,
            100_000_000.0,
            25_000_000.0,
            10_000_000.0,
            5_000_000.0,
            6_000_000.0,
        ),
    ),
    "EQNX.PA": DemoCompanyProfile(
        market_cap=235_000_000.0,
        average_daily_volume=180_000.0,
        latest_price_close=30.0,
        latest_statement=DemoStatementPayload(
            2024,
            200_000_000.0,
            21_000_000.0,
            25_000_000.0,
            19_000_000.0,
            320_000_000.0,
            100_000_000.0,
            120_000_000.0,
            95_000_000.0,
            10_000_000.0,
            7_000_000.0,
        ),
        previous_statement=DemoStatementPayload(
            2023,
            198_000_000.0,
            20_000_000.0,
            24_000_000.0,
            18_000_000.0,
            315_000_000.0,
            95_000_000.0,
            118_000_000.0,
            92_000_000.0,
            9_400_000.0,
            7_000_000.0,
        ),
    ),
    "FLAN.PA": DemoCompanyProfile(
        market_cap=130_000_000.0,
        average_daily_volume=120_000.0,
        latest_price_close=14.0,
        latest_statement=DemoStatementPayload(
            2024,
            140_000_000.0,
            6_000_000.0,
            10_000_000.0,
            4_000_000.0,
            220_000_000.0,
            80_000_000.0,
            50_000_000.0,
            30_000_000.0,
            1_000_000.0,
            9_000_000.0,
        ),
        previous_statement=DemoStatementPayload(
            2023,
            138_000_000.0,
            6_000_000.0,
            9_800_000.0,
            3_800_000.0,
            215_000_000.0,
            78_000_000.0,
            49_000_000.0,
            29_000_000.0,
            800_000.0,
            9_000_000.0,
        ),
    ),
    "GARN.PA": DemoCompanyProfile(
        market_cap=115_000_000.0,
        average_daily_volume=90_000.0,
        latest_price_close=None,
        latest_statement=None,
        previous_statement=None,
    ),
}

_WATCHLIST_BY_TICKER: dict[str, DemoWatchlistProfile] = {
    "ALPS.PA": DemoWatchlistProfile(
        WATCHLIST_STATUS_CONVICTION, "high recurring revenue and strong cash conversion", False
    ),
    "DORD.PA": DemoWatchlistProfile(WATCHLIST_STATUS_REVIEW, "strong growth profile but premium valuation", True),
    "CAMA.PA": DemoWatchlistProfile(WATCHLIST_STATUS_REJECTED, "decelerating growth with leverage pressure", False),
    "GARN.PA": DemoWatchlistProfile(WATCHLIST_STATUS_WATCHING, "missing financial history in demo dataset", False),
}


@dataclass
class DemoDatasetService:
    session_scope_factory: SessionScopeFactory = get_session
    universe_service: UniverseService | None = None
    kpi_snapshot_service: KpiSnapshotService | None = None
    watchlist_service: WatchlistService | None = None
    screening_service: ScreeningService | None = None

    def __post_init__(self) -> None:
        if self.universe_service is None:
            self.universe_service = UniverseService(session_scope_factory=self.session_scope_factory)
        if self.kpi_snapshot_service is None:
            self.kpi_snapshot_service = KpiSnapshotService(session_scope_factory=self.session_scope_factory)
        if self.watchlist_service is None:
            self.watchlist_service = WatchlistService(session_scope_factory=self.session_scope_factory)
        if self.screening_service is None:
            self.screening_service = ScreeningService(session_scope_factory=self.session_scope_factory)

    def build_demo_dataset(
        self,
        *,
        seed_csv_path: str | Path = DEMO_DEFAULT_SEED_PATH,
        reset_existing: bool = True,
        initialize_storage: bool = True,
    ) -> DemoDatasetSummary:
        if initialize_storage:
            init_db()

        csv_path = Path(seed_csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"demo seed file not found: {csv_path}")

        if reset_existing:
            self._reset_existing_data()

        if self.universe_service is None or self.kpi_snapshot_service is None:
            raise RuntimeError("demo dataset service is not initialized")

        self.universe_service.load_seed_universe(csv_path)
        company_ids_by_ticker = self._enrich_companies()
        self.kpi_snapshot_service.refresh_universe_kpi_snapshots(snapshot_date=DEMO_SNAPSHOT_DATE)
        self._seed_watchlist(company_ids_by_ticker)

        if self.screening_service is None:
            raise RuntimeError("demo dataset service is not initialized")
        saved_snapshot = self.screening_service.save_screening_snapshot(
            _DEMO_BASELINE_FILTERS,
            name=DEMO_SCREENING_SNAPSHOT_NAME,
        )
        return self._build_summary(saved_snapshot.snapshot_id)

    def _reset_existing_data(self) -> None:
        with self.session_scope_factory() as session:
            session.execute(delete(ScreeningSnapshot))
            session.execute(delete(WatchlistEntry))
            session.execute(delete(KpiSnapshot))
            session.execute(delete(PriceHistory))
            session.execute(delete(FinancialStatement))
            session.execute(delete(Dividend))
            session.execute(delete(Split))
            session.execute(delete(Company))

    def _enrich_companies(self) -> dict[str, int]:
        by_ticker: dict[str, int] = {}
        with self.session_scope_factory() as session:
            for company in company_repository.get_all(session):
                if company.ticker is None:
                    continue
                profile = _PROFILES_BY_TICKER.get(company.ticker)
                if profile is None:
                    continue
                company.market_cap = profile.market_cap
                company.average_daily_volume = profile.average_daily_volume
                company_repository.update(session, company)
                self._upsert_statement(session, company.id, profile.latest_statement)
                self._upsert_statement(session, company.id, profile.previous_statement)
                self._upsert_price(session, company.id, profile.latest_price_close)
                by_ticker[company.ticker] = company.id
        return by_ticker

    def _upsert_statement(
        self,
        session: Session,
        company_id: int,
        payload: DemoStatementPayload | None,
    ) -> None:
        if payload is None:
            return
        existing = financial_statement_repository.get_by_company_and_year(
            session,
            company_id=company_id,
            fiscal_year=payload.fiscal_year,
            period_type=PeriodType.ANNUAL,
        )
        if existing is None:
            financial_statement_repository.create(
                session,
                FinancialStatement(
                    company_id=company_id,
                    fiscal_year=payload.fiscal_year,
                    period_type=PeriodType.ANNUAL,
                    revenue=payload.revenue,
                    ebit=payload.ebit,
                    ebitda=payload.ebitda,
                    net_income=payload.net_income,
                    total_assets=payload.total_assets,
                    total_equity=payload.total_equity,
                    total_debt=payload.total_debt,
                    net_debt=payload.net_debt,
                    free_cash_flow=payload.free_cash_flow,
                    shares_outstanding=payload.shares_outstanding,
                ),
            )
            return
        existing.revenue = payload.revenue
        existing.ebit = payload.ebit
        existing.ebitda = payload.ebitda
        existing.net_income = payload.net_income
        existing.total_assets = payload.total_assets
        existing.total_equity = payload.total_equity
        existing.total_debt = payload.total_debt
        existing.net_debt = payload.net_debt
        existing.free_cash_flow = payload.free_cash_flow
        existing.shares_outstanding = payload.shares_outstanding
        session.flush()

    def _upsert_price(self, session: Session, company_id: int, close_price: float | None) -> None:
        if close_price is None:
            return
        existing = price_history_repository.get_by_company_and_date(session, company_id, DEMO_SNAPSHOT_DATE)
        if existing is None:
            price_history_repository.create(
                session,
                PriceHistory(
                    company_id=company_id,
                    date=DEMO_SNAPSHOT_DATE,
                    open=close_price * 0.98,
                    high=close_price * 1.02,
                    low=close_price * 0.97,
                    close=close_price,
                    adjusted_close=close_price,
                    volume=100_000,
                ),
            )
            return
        existing.open = close_price * 0.98
        existing.high = close_price * 1.02
        existing.low = close_price * 0.97
        existing.close = close_price
        existing.adjusted_close = close_price
        existing.volume = 100_000
        session.flush()

    def _seed_watchlist(self, company_ids_by_ticker: dict[str, int]) -> None:
        if self.watchlist_service is None:
            raise RuntimeError("demo dataset service is not initialized")
        for ticker, profile in _WATCHLIST_BY_TICKER.items():
            company_id = company_ids_by_ticker.get(ticker)
            if company_id is None:
                continue
            self.watchlist_service.update_company_notes(company_id, profile.notes)
            self.watchlist_service.update_company_status(company_id, profile.status)
            self.watchlist_service.update_company_exclusion(company_id, profile.is_excluded)

    def _build_summary(self, ranking_snapshot_id: int) -> DemoDatasetSummary:
        if self.screening_service is None:
            raise RuntimeError("demo dataset service is not initialized")
        with self.session_scope_factory() as session:
            total_companies = len(company_repository.get_all(session))
            watchlist_entries_list = watchlist_repository.list_all(session)
            watchlist_entries = len(watchlist_entries_list)
            excluded_entries = sum(1 for entry in watchlist_entries_list if entry.is_excluded)

        ranked = self.screening_service.filter_universe_with_scores(
            UniverseScreeningFilters(
                include_excluded=True,
                sort_by="rank",
                scored_only=False,
            )
        )
        scored_companies = len([entry for entry in ranked if entry.total_score is not None])
        top_ranked_tickers = tuple(
            entry.ticker or ""
            for entry in self.screening_service.filter_universe_with_scores(
                UniverseScreeningFilters(
                    include_excluded=True,
                    scored_only=True,
                    sort_by="rank",
                    top_n=3,
                )
            )
        )
        return DemoDatasetSummary(
            total_companies=total_companies,
            scored_companies=scored_companies,
            unscored_companies=total_companies - scored_companies,
            watchlist_entries=watchlist_entries,
            excluded_entries=excluded_entries,
            ranking_snapshot_id=ranking_snapshot_id,
            top_ranked_tickers=top_ranked_tickers,
        )
