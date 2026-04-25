from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.kpi_snapshot import KpiSnapshot
from src.repositories import (
    company_repository,
    financial_statement_repository,
    kpi_snapshot_repository,
    price_history_repository,
)
from src.repositories.database import get_session
from src.services.ratio_service import CompanyRatios, RatioService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


@dataclass
class KpiSnapshotServiceResult:
    company_id: int
    snapshot_date: date
    success: bool
    snapshot_id: int | None = None
    error: str | None = None
    stage: str | None = None
    metrics: dict[str, float | int | None] = field(default_factory=dict)


@dataclass
class UniverseKpiSnapshotError:
    company_id: int
    ticker: str | None
    error: str
    stage: str | None = None


@dataclass
class UniverseKpiSnapshotRefreshResult:
    total: int
    success_count: int
    failed_count: int
    errors: list[UniverseKpiSnapshotError] = field(default_factory=list)


@dataclass
class CompanyKpiContext:
    company: Company
    latest_statement: FinancialStatement
    previous_statement: FinancialStatement | None
    price: float


@dataclass
class CompanyKpiContextLoadResult:
    context: CompanyKpiContext | None
    error: str | None = None


@dataclass
class KpiSnapshotService:
    session_scope_factory: SessionScopeFactory = get_session
    ratio_service: RatioService = field(default_factory=RatioService)
    source_name: str = "ratio_service_v1"
    default_country: str = "France"
    default_max_market_cap: float = 2_000_000_000.0
    default_min_average_daily_volume: float | None = None

    def compute_and_upsert_for_company(
        self,
        company_id: int,
        snapshot_date: date,
    ) -> KpiSnapshotServiceResult:
        with self.session_scope_factory() as session:
            load = _load_company_kpi_context(session, company_id)
            if load.context is None:
                return KpiSnapshotServiceResult(
                    company_id=company_id,
                    snapshot_date=snapshot_date,
                    success=False,
                    error=load.error,
                    stage="load",
                )
            context = load.context

            ratios = self.ratio_service.compute_all(
                company_id=company_id,
                fiscal_year=context.latest_statement.fiscal_year,
                price=context.price,
                stmt=context.latest_statement,
                previous_stmt=context.previous_statement,
            )
            metrics = _ratios_to_metrics_payload(ratios)

            snapshot = build_snapshot_payload(
                company_id=company_id,
                snapshot_date=snapshot_date,
                metrics=metrics,
                source=self.source_name,
            )
            stored = kpi_snapshot_repository.upsert(session, snapshot)
            return KpiSnapshotServiceResult(
                company_id=company_id,
                snapshot_date=snapshot_date,
                success=True,
                snapshot_id=stored.id,
                metrics=metrics,
            )

    def refresh_universe_kpi_snapshots(
        self,
        snapshot_date: date,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> UniverseKpiSnapshotRefreshResult:
        raise NotImplementedError


def build_snapshot_payload(
    company_id: int,
    snapshot_date: date,
    metrics: dict[str, float | int | None],
    source: str,
) -> KpiSnapshot:
    return KpiSnapshot(
        company_id=company_id,
        snapshot_date=snapshot_date,
        metrics=metrics,
        source=source,
    )


def _load_company_kpi_context(session: Session, company_id: int) -> CompanyKpiContextLoadResult:
    company = company_repository.get_by_id(session, company_id)
    if company is None:
        return CompanyKpiContextLoadResult(context=None, error="company not found")

    statements = financial_statement_repository.get_by_company(session, company_id)
    annual_statements = _annual_statements(statements)
    if not annual_statements:
        return CompanyKpiContextLoadResult(context=None, error="no annual financial statements")

    latest_statement = annual_statements[0]
    previous_statement = annual_statements[1] if len(annual_statements) > 1 else None
    price = _derive_company_price(session, company, latest_statement)
    if price is None:
        return CompanyKpiContextLoadResult(context=None, error="no usable price data")

    return CompanyKpiContextLoadResult(
        context=CompanyKpiContext(
            company=company,
            latest_statement=latest_statement,
            previous_statement=previous_statement,
            price=price,
        )
    )


def _annual_statements(statements: list[FinancialStatement]) -> list[FinancialStatement]:
    annual = [
        statement
        for statement in statements
        if statement.period_type == PeriodType.ANNUAL or statement.period_type == PeriodType.ANNUAL.value
    ]
    annual.sort(key=lambda statement: statement.fiscal_year, reverse=True)
    return annual


def _derive_company_price(
    session: Session,
    company: Company,
    latest_statement: FinancialStatement,
) -> float | None:
    latest_price = price_history_repository.get_latest(session, company.id)
    if latest_price is not None:
        return latest_price.close
    if company.market_cap is not None and latest_statement.shares_outstanding is not None:
        if latest_statement.shares_outstanding > 0:
            return company.market_cap / latest_statement.shares_outstanding
    return None


def _ratios_to_metrics_payload(ratios: CompanyRatios) -> dict[str, float | int | None]:
    return {
        "fiscal_year": ratios.fiscal_year,
        "price": ratios.price,
        "market_cap": ratios.mkt_cap,
        "enterprise_value": ratios.ev,
        "pe_ratio": ratios.pe_ratio,
        "pb_ratio": ratios.pb_ratio,
        "ev_ebitda": ratios.ev_ebitda,
        "ev_ebit": ratios.ev_ebit,
        "fcf_yield": ratios.fcf_yield,
        "roe": ratios.roe,
        "roic": ratios.roic,
        "roce": ratios.roce,
        "gross_margin": ratios.gross_margin,
        "operating_margin": ratios.operating_margin,
        "revenue_growth": ratios.revenue_growth,
        "ebitda_growth": ratios.ebitda_growth,
        "net_debt_to_ebitda": ratios.net_debt_to_ebitda,
        "current_ratio": ratios.current_ratio,
        "interest_coverage": ratios.interest_coverage,
    }
