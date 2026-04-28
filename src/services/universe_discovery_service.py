from __future__ import annotations

import logging
import time
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
ProgressCallback = Callable[[dict], None]
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
    error_kind: str | None = None
    stage: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class UniverseRefreshResult:
    total: int
    succeeded: int
    failed: int
    skipped: int
    results: list[CompanyUniverseRefreshResult] = field(default_factory=list)
    skipped_tickers: list[str] = field(default_factory=list)


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
                error_kind=data_result.error_kind,
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

    def batch_refresh_universe(self, pacing_seconds: float = 2.0) -> UniverseRefreshResult:
        """Refresh all active companies, one by one, tolerating individual failures."""
        with self.session_scope_factory() as session:
            companies = company_repository.get_all_active(session)
            company_ids = [(c.id, c.ticker or "") for c in companies]

        total = len(company_ids)
        _LOGGER.info("universe batch refresh started | total_companies=%s", total)
        company_id_list = [company_id for company_id, _ in company_ids]
        return self.refresh_companies_by_ids(company_id_list=company_id_list, pacing_seconds=pacing_seconds)

    def refresh_companies_by_ids(
        self,
        *,
        company_id_list: list[int],
        pacing_seconds: float = 2.0,
        batch_size: int = 25,
        skip_recently_refreshed: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> UniverseRefreshResult:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")

        ordered_unique_ids = list(dict.fromkeys(company_id_list))
        with self.session_scope_factory() as session:
            company_by_id: dict[int, tuple[int, str, datetime | None]] = {}
            for company_id in ordered_unique_ids:
                company = company_repository.get_by_id(session, company_id)
                if company is None:
                    continue
                company_by_id[company.id] = (
                    company.id,
                    company.ticker or "",
                    company.last_universe_refresh_at,
                )

        companies = [company_by_id[company_id] for company_id in ordered_unique_ids if company_id in company_by_id]
        total = len(companies)
        total_batches = (total + batch_size - 1) // batch_size if total > 0 else 0

        results: list[CompanyUniverseRefreshResult] = []
        skipped_tickers: list[str] = []
        skipped = 0
        processed = 0

        for batch_number, batch_start in enumerate(range(0, total, batch_size), start=1):
            batch_companies = companies[batch_start : batch_start + batch_size]
            _emit_progress(
                progress_callback,
                {
                    "phase": "batch_start",
                    "batch_number": batch_number,
                    "total_batches": total_batches,
                    "batch_size": len(batch_companies),
                    "processed": processed,
                    "total": total,
                },
            )
            for local_index, (company_id, ticker, last_refreshed_at) in enumerate(batch_companies):
                if processed > 0 and pacing_seconds > 0:
                    time.sleep(pacing_seconds)
                processed += 1
                if skip_recently_refreshed and _is_same_day_utc(last_refreshed_at, datetime.now(UTC)):
                    skipped += 1
                    skipped_tickers.append(ticker)
                    _emit_progress(
                        progress_callback,
                        {
                            "phase": "company_result",
                            "status": "skipped",
                            "company_id": company_id,
                            "ticker": ticker,
                            "processed": processed,
                            "total": total,
                            "batch_number": batch_number,
                            "total_batches": total_batches,
                            "batch_position": local_index + 1,
                            "batch_size": len(batch_companies),
                            "message": "already refreshed today",
                        },
                    )
                    continue

                _emit_progress(
                    progress_callback,
                    {
                        "phase": "company_start",
                        "company_id": company_id,
                        "ticker": ticker,
                        "processed": processed - 1,
                        "total": total,
                        "batch_number": batch_number,
                        "total_batches": total_batches,
                        "batch_position": local_index + 1,
                        "batch_size": len(batch_companies),
                    },
                )

                try:
                    result = self.refresh_company(company_id)
                    results.append(result)
                    _emit_progress(
                        progress_callback,
                        {
                            "phase": "company_result",
                            "status": "success" if result.success else "failed",
                            "company_id": company_id,
                            "ticker": result.ticker or ticker,
                            "processed": processed,
                            "total": total,
                            "batch_number": batch_number,
                            "total_batches": total_batches,
                            "batch_position": local_index + 1,
                            "batch_size": len(batch_companies),
                            "error": result.error,
                            "error_kind": result.error_kind,
                            "stage": result.stage,
                            "warnings": list(result.warnings),
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.error(
                        "universe refresh unexpected error | company_id=%s ticker=%s error=%s",
                        company_id,
                        ticker,
                        exc,
                    )
                    failed_result = CompanyUniverseRefreshResult(
                        company_id=company_id,
                        ticker=ticker,
                        success=False,
                        error=str(exc),
                        stage="unexpected",
                    )
                    results.append(failed_result)
                    _emit_progress(
                        progress_callback,
                        {
                            "phase": "company_result",
                            "status": "failed",
                            "company_id": company_id,
                            "ticker": ticker,
                            "processed": processed,
                            "total": total,
                            "batch_number": batch_number,
                            "total_batches": total_batches,
                            "batch_position": local_index + 1,
                            "batch_size": len(batch_companies),
                            "error": str(exc),
                            "stage": "unexpected",
                        },
                    )

        succeeded = sum(1 for result in results if result.success)
        failed = len(results) - succeeded
        _emit_progress(
            progress_callback,
            {
                "phase": "completed",
                "total": total,
                "succeeded": succeeded,
                "failed": failed,
                "skipped": skipped,
            },
        )
        _LOGGER.info(
            "universe refresh completed | total=%s succeeded=%s failed=%s skipped=%s",
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
            skipped_tickers=skipped_tickers,
        )

    def refresh_watchlist(self, pacing_seconds: float = 2.0) -> UniverseRefreshResult:
        """Refresh only companies currently in the watchlist, preserving analyst data."""
        with self.session_scope_factory() as session:
            entries = watchlist_repository.list_all(session)
            company_ids = [entry.company_id for entry in entries]
        return self.refresh_companies_by_ids(company_id_list=company_ids, pacing_seconds=pacing_seconds)

    def _stamp_refresh_timestamp(self, company_id: int) -> None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is not None:
                company.last_universe_refresh_at = datetime.now(UTC)
                company_repository.update(session, company)


def _emit_progress(progress_callback: ProgressCallback | None, payload: dict) -> None:
    if progress_callback is None:
        return
    progress_callback(payload)


def _is_same_day_utc(left: datetime | None, right: datetime) -> bool:
    if left is None:
        return False
    if left.tzinfo is None:
        left_date = left.date()
    else:
        left_date = left.astimezone(UTC).date()
    right_date = right.astimezone(UTC).date()
    return left_date == right_date
