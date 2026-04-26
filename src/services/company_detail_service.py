from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.kpi_snapshot import KpiSnapshot
from src.models.price_history import PriceHistory
from src.repositories import (
    company_repository,
    financial_statement_repository,
    kpi_snapshot_repository,
    price_history_repository,
)
from src.repositories.database import get_session

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_LOGGER = logging.getLogger(__name__)

_ZERO = 1e-9


@dataclass(frozen=True)
class CompanyFinancialDetail:
    company_id: int
    ticker: str | None
    name: str
    sector: str | None
    currency: str
    # Market data
    current_price: float | None
    market_cap: float | None
    enterprise_value: float | None
    # Latest financial period
    fiscal_year: int | None
    period_type: str | None
    # Raw financials
    revenue: float | None
    ebitda: float | None
    ebit: float | None
    net_income: float | None
    free_cash_flow: float | None
    net_debt: float | None
    shares_outstanding: float | None
    # Valuation ratios
    pe_ratio: float | None
    pb_ratio: float | None
    ev_ebitda: float | None
    ev_sales: float | None
    fcf_yield: float | None
    # Quality ratios
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None
    roe: float | None
    roic: float | None
    # Growth
    revenue_growth: float | None
    ebitda_growth: float | None
    # Risk
    net_debt_to_ebitda: float | None
    # Data quality
    data_quality_score: float | None
    snapshot_date: date | None


@dataclass
class CompanyDetailService:
    session_scope_factory: SessionScopeFactory = field(default=get_session)

    def get_financial_detail(self, company_id: int) -> CompanyFinancialDetail | None:
        with self.session_scope_factory() as session:
            company = company_repository.get_by_id(session, company_id)
            if company is None:
                _LOGGER.warning("company_detail not found | company_id=%s", company_id)
                return None

            latest_price = price_history_repository.get_latest(session, company_id)
            latest_stmt = _get_latest_annual_statement(session, company_id)
            snapshot = kpi_snapshot_repository.get_latest_by_company(session, company_id)

            return _build_detail(company, latest_price, latest_stmt, snapshot)


def _get_latest_annual_statement(session: Session, company_id: int) -> FinancialStatement | None:
    statements = financial_statement_repository.get_by_company(session, company_id)
    annual = [s for s in statements if s.period_type in (PeriodType.ANNUAL, PeriodType.ANNUAL.value)]
    annual.sort(key=lambda s: s.fiscal_year, reverse=True)
    return annual[0] if annual else None


def _metric(snapshot: KpiSnapshot | None, key: str) -> float | None:
    if snapshot is None:
        return None
    value = snapshot.metrics.get(key)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ev_sales(enterprise_value: float | None, revenue: float | None) -> float | None:
    if enterprise_value is None or revenue is None:
        return None
    if abs(revenue) < _ZERO:
        return None
    return enterprise_value / revenue


def _net_margin(net_income: float | None, revenue: float | None) -> float | None:
    if net_income is None or revenue is None:
        return None
    if abs(revenue) < _ZERO:
        return None
    return net_income / revenue


def _build_detail(
    company: Company,
    latest_price: PriceHistory | None,
    latest_stmt: FinancialStatement | None,
    snapshot: KpiSnapshot | None,
) -> CompanyFinancialDetail:
    current_price = latest_price.close if latest_price is not None else None

    market_cap = _metric(snapshot, "market_cap") or company.market_cap
    enterprise_value = _metric(snapshot, "enterprise_value")

    revenue = latest_stmt.revenue if latest_stmt is not None else None
    ebitda = latest_stmt.ebitda if latest_stmt is not None else None
    ebit = latest_stmt.ebit if latest_stmt is not None else None
    net_income = latest_stmt.net_income if latest_stmt is not None else None
    free_cash_flow = latest_stmt.free_cash_flow if latest_stmt is not None else None
    net_debt = latest_stmt.net_debt if latest_stmt is not None else None
    shares_outstanding = latest_stmt.shares_outstanding if latest_stmt is not None else None

    return CompanyFinancialDetail(
        company_id=company.id,
        ticker=company.ticker,
        name=company.name,
        sector=company.sector,
        currency=company.currency,
        current_price=current_price,
        market_cap=market_cap,
        enterprise_value=enterprise_value,
        fiscal_year=latest_stmt.fiscal_year if latest_stmt is not None else None,
        period_type=latest_stmt.period_type if latest_stmt is not None else None,
        revenue=revenue,
        ebitda=ebitda,
        ebit=ebit,
        net_income=net_income,
        free_cash_flow=free_cash_flow,
        net_debt=net_debt,
        shares_outstanding=shares_outstanding,
        pe_ratio=_metric(snapshot, "pe_ratio"),
        pb_ratio=_metric(snapshot, "pb_ratio"),
        ev_ebitda=_metric(snapshot, "ev_ebitda"),
        ev_sales=_ev_sales(enterprise_value, revenue),
        fcf_yield=_metric(snapshot, "fcf_yield"),
        gross_margin=_metric(snapshot, "gross_margin"),
        operating_margin=_metric(snapshot, "operating_margin"),
        net_margin=_net_margin(net_income, revenue),
        roe=_metric(snapshot, "roe"),
        roic=_metric(snapshot, "roic"),
        revenue_growth=_metric(snapshot, "revenue_growth"),
        ebitda_growth=_metric(snapshot, "ebitda_growth"),
        net_debt_to_ebitda=_metric(snapshot, "net_debt_to_ebitda"),
        data_quality_score=_metric(snapshot, "data_quality_score"),
        snapshot_date=snapshot.snapshot_date if snapshot is not None else None,
    )
