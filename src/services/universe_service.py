from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from src.models.company import Company
from src.repositories import company_repository, euronext_discovery_repository, seed_universe_repository
from src.repositories.database import get_session

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


@dataclass
class CompanyUniverseSummary:
    total_companies: int
    filtered_companies: int
    exclusions: dict[str, int]


@dataclass
class UniverseService:
    session_scope_factory: SessionScopeFactory = get_session
    default_country: str = "France"
    default_max_market_cap: float = 2_000_000_000.0
    default_min_average_daily_volume: float | None = None

    def load_seed_universe(self, csv_path: str | Path) -> list[Company]:
        entries = seed_universe_repository.read_seed_universe(csv_path)
        with self.session_scope_factory() as session:
            return company_repository.bulk_upsert_from_seed(session, entries)

    def load_euronext_france_universe(self) -> list[Company]:
        entries = euronext_discovery_repository.discover_french_listed_companies()
        with self.session_scope_factory() as session:
            return company_repository.bulk_upsert_from_seed(session, entries)

    def refresh_investable_universe(
        self,
        max_market_cap: float,
        min_average_daily_volume: float | None,
    ) -> list[Company]:
        with self.session_scope_factory() as session:
            return company_repository.get_investable_universe(
                session,
                max_market_cap=max_market_cap,
                min_average_daily_volume=min_average_daily_volume,
                country=self.default_country,
            )

    def get_company_universe_summary(self) -> CompanyUniverseSummary:
        with self.session_scope_factory() as session:
            investable = company_repository.get_investable_universe(
                session,
                max_market_cap=self.default_max_market_cap,
                min_average_daily_volume=self.default_min_average_daily_volume,
                country=self.default_country,
            )
            companies = company_repository.get_all(session)

        illiquid_count = 0
        if self.default_min_average_daily_volume is not None:
            illiquid_count = sum(
                1
                for company in companies
                if company.country == self.default_country
                and company.is_active
                and company.market_cap is not None
                and company.market_cap <= self.default_max_market_cap
                and company.average_daily_volume is not None
                and company.average_daily_volume < self.default_min_average_daily_volume
            )

        exclusions = {
            "non_target_country": sum(1 for company in companies if company.country != self.default_country),
            "inactive": sum(
                1 for company in companies if company.country == self.default_country and not company.is_active
            ),
            "inconsistent_identity": sum(
                1
                for company in companies
                if company.country == self.default_country and (_is_blank(company.ticker) or _is_blank(company.isin))
            ),
            "over_market_cap": sum(
                1
                for company in companies
                if company.country == self.default_country
                and company.is_active
                and company.market_cap is not None
                and company.market_cap > self.default_max_market_cap
            ),
            "illiquid": illiquid_count,
        }
        return CompanyUniverseSummary(
            total_companies=len(companies),
            filtered_companies=len(investable),
            exclusions=exclusions,
        )


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()
