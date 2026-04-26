from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from src.repositories import company_repository, watchlist_repository
from src.repositories.database import get_session
from src.services.financial_data_service import CompanyDataRefreshResult, FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompanyUniverseRefreshResult:
    company_id: int
    ticker: str
    success: bool
    prices_added: int = 0
    statements_added: int = 0
    kpi_snapshot_id: int | None = None
    error: str | None = None
    stage: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UniverseRefreshResult:
    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[CompanyUniverseRefreshResult] = field(default_factory=list)


@dataclass
class UniverseDiscoveryService:
    financial_data_service: FinancialDataService
    kpi_snapshot_service: KpiSnapshotService
    session_scope_factory: SessionScopeFactory = field(default=get_session)

    def refresh_company(self, company_id: int) -> CompanyUniverseRefreshResult:
        """Refresh financial data and KPI snapshot for one company, then stamp last_universe_refresh_at."""
        data_result: CompanyDataRefreshResult = self.financial_data_service.refresh_company_data(company_id)
        if not data_result.success:
            _LOGGER.warning(
                "universe refresh data failed | company_id=%s ticker=%s stage=%s error=%s",
                company_id,
                data_result.ticker,
                data_result.stage,
                data_result.error,
            )
            return CompanyUniverseRefreshResult(
                company_id=company_id,
                ticker=data_result.ticker,
                success=False,
                error=data_result.error,
                stage=data_result.stage,
                warnings=list(data_result.warnings),
            )

        kpi_result = self.kpi_snapshot_service.compute_and_upsert_for_company(
            company_id=company_id,
            snapshot_date=date.today(),
        )
        warnings = list(data_result.warnings)
        if not kpi_result.success:
            warnings.append(f"KPI snapshot failed: {kpi_result.error}")
            _LOGGER.warning(
                "universe refresh kpi failed | company_id=%s ticker=%s error=%s",
                company_id,
                data_result.ticker,
                kpi_result.error,
            )

        self._stamp_refresh_timestamp(company_id)

        return CompanyUniverseRefreshResult(
            company_id=company_id,
            ticker=data_result.ticker,
            success=True,
            prices_added=data_result.prices_added,
            statements_added=data_result.statements_added,
            kpi_snapshot_id=kpi_result.snapshot_id if kpi_result.success else None,
            warnings=warnings,
        )

    def batch_refresh_universe(self) -> UniverseRefreshResult:
        """Refresh all active companies, one by one, tolerating individual failures."""
        with self.session_scope_factory() as session:
            companies = company_repository.get_all_active(session)
            company_ids = [(c.id, c.ticker or "") for c in companies]

        total = len(company_ids)
        _LOGGER.info("universe batch refresh started | total_companies=%s", total)

        results: list[CompanyUniverseRefreshResult] = []
        skipped = 0
        for company_id, ticker in company_ids:
            try:
                result = self.refresh_company(company_id)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "universe batch refresh unexpected error | company_id=%s ticker=%s error=%s",
                    company_id,
                    ticker,
                    exc,
                )
                results.append(
                    CompanyUniverseRefreshResult(
                        company_id=company_id,
                        ticker=ticker,
                        success=False,
                        error=str(exc),
                        stage="unexpected",
                    )
                )

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded

        _LOGGER.info(
            "universe batch refresh completed | total=%s succeeded=%s failed=%s skipped=%s",
            total,
            succeeded,
            failed,
            skipped,
        )
        return UniverseRefreshResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            results=results,
        )

    def refresh_watchlist(self) -> UniverseRefreshResult:
        """Refresh only companies currently in the watchlist, preserving analyst data."""
        with self.session_scope_factory() as session:
            entries = watchlist_repository.list_all(session)
            company_ids = [(e.company_id, "") for e in entries]

        total = len(company_ids)
        _LOGGER.info("watchlist refresh started | total_companies=%s", total)

        results: list[CompanyUniverseRefreshResult] = []
        skipped = 0
        for company_id, _ in company_ids:
            try:
                result = self.refresh_company(company_id)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "watchlist refresh unexpected error | company_id=%s error=%s",
                    company_id,
                    exc,
                )
                results.append(
                    CompanyUniverseRefreshResult(
                        company_id=company_id,
                        ticker="",
                        success=False,
                        error=str(exc),
                        stage="unexpected",
                    )
                )

        succeeded = sum(1 for r in results if r.success)
        failed = len(results) - succeeded
        _LOGGER.info(
            "watchlist refresh completed | total=%s succeeded=%s failed=%s skipped=%s",
            total,
            succeeded,
            failed,
            skipped,
        )
        return UniverseRefreshResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            results=results,
        )

    def _stamp_refresh_timestamp(self, company_id: int) -> None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is not None:
                company.last_universe_refresh_at = datetime.now(UTC)
                company_repository.update(session, company)
