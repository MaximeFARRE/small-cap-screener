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
_MAX_HISTORICAL_PERIODS = 5
_MIN_CAGR_PERIODS = 3
_ANNUAL_PERIOD = PeriodType.ANNUAL.value
_TREND_POSITIVE = "positive"
_TREND_NEGATIVE = "negative"
_TREND_STABLE = "stable"


@dataclass(frozen=True)
class HistoricalMetricPoint:
    fiscal_year: int
    period_type: str
    value: float


@dataclass(frozen=True)
class HistoricalFundamentalsTrends:
    revenue_cagr: float | None
    operating_income_cagr: float | None
    net_income_cagr: float | None
    free_cash_flow_cagr: float | None
    revenue_direction: str | None
    margin_direction: str | None
    net_debt_direction: str | None


@dataclass(frozen=True)
class HistoricalFundamentals:
    revenue_history: list[HistoricalMetricPoint]
    ebitda_history: list[HistoricalMetricPoint]
    ebit_history: list[HistoricalMetricPoint]
    operating_income_history: list[HistoricalMetricPoint]
    net_income_history: list[HistoricalMetricPoint]
    free_cash_flow_history: list[HistoricalMetricPoint]
    net_debt_history: list[HistoricalMetricPoint]
    eps_history: list[HistoricalMetricPoint]
    shares_outstanding_history: list[HistoricalMetricPoint]
    trends: HistoricalFundamentalsTrends


@dataclass(frozen=True)
class CompanyFinancialDetail:
    company_id: int
    ticker: str | None
    name: str
    sector: str | None
    currency: str
    # Company profile
    industry: str | None
    website: str | None
    business_summary: str | None
    full_time_employees: int | None
    city: str | None
    phone: str | None
    # Fundamental Metrics (Latest from provider)
    latest_gross_margins: float | None
    latest_operating_margins: float | None
    latest_profit_margins: float | None
    latest_roe: float | None
    latest_roa: float | None
    latest_current_ratio: float | None
    latest_quick_ratio: float | None
    latest_payout_ratio: float | None
    # Shares and Volume
    float_shares: float | None
    # Dividend Info
    latest_dividend_rate: float | None
    latest_dividend_yield: float | None
    ex_dividend_date: date | None
    latest_five_year_avg_dividend_yield: float | None
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
    historical_fundamentals: HistoricalFundamentals


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
            statements = financial_statement_repository.get_by_company(session, company_id)
            selected_statements = _select_historical_statements(statements)
            latest_stmt = selected_statements[0] if selected_statements else None
            snapshot = kpi_snapshot_repository.get_latest_by_company(session, company_id)

            return _build_detail(company, latest_price, latest_stmt, snapshot, selected_statements)


def _select_historical_statements(statements: list[FinancialStatement]) -> list[FinancialStatement]:
    ordered = sorted(
        statements,
        key=lambda stmt: (stmt.fiscal_year, _period_priority(stmt.period_type)),
        reverse=True,
    )

    selected: list[FinancialStatement] = []
    selected_years: set[int] = set()

    for statement in ordered:
        period_type = _normalize_period_type(statement.period_type)
        if period_type != _ANNUAL_PERIOD:
            continue
        if statement.fiscal_year in selected_years:
            continue
        selected.append(statement)
        selected_years.add(statement.fiscal_year)
        if len(selected) >= _MAX_HISTORICAL_PERIODS:
            return selected

    for statement in ordered:
        if statement.fiscal_year in selected_years:
            continue
        selected.append(statement)
        selected_years.add(statement.fiscal_year)
        if len(selected) >= _MAX_HISTORICAL_PERIODS:
            break

    selected.sort(key=lambda stmt: stmt.fiscal_year, reverse=True)
    return selected


def _period_priority(period_type: str | PeriodType) -> int:
    return 1 if _normalize_period_type(period_type) == _ANNUAL_PERIOD else 0


def _normalize_period_type(period_type: str | PeriodType) -> str:
    return period_type.value if isinstance(period_type, PeriodType) else str(period_type)


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


def _operating_income(statement: FinancialStatement) -> float | None:
    if statement.ebitda is not None:
        return statement.ebitda
    return statement.ebit


def _eps(statement: FinancialStatement) -> float | None:
    return _ratio(statement.net_income, statement.shares_outstanding)


def _build_metric_history(
    statements: list[FinancialStatement],
    extractor: Callable[[FinancialStatement], float | None],
) -> list[HistoricalMetricPoint]:
    history: list[HistoricalMetricPoint] = []
    for statement in statements:
        value = extractor(statement)
        if value is None:
            continue
        history.append(
            HistoricalMetricPoint(
                fiscal_year=statement.fiscal_year,
                period_type=_normalize_period_type(statement.period_type),
                value=value,
            )
        )
    return history


def _cagr(history: list[HistoricalMetricPoint]) -> float | None:
    if len(history) < _MIN_CAGR_PERIODS:
        return None
    recent = history[0]
    oldest = history[-1]
    years = recent.fiscal_year - oldest.fiscal_year
    if years <= 0:
        return None
    if recent.value <= 0 or oldest.value <= 0:
        return None
    return (recent.value / oldest.value) ** (1.0 / years) - 1.0


def _direction_from_values(history: list[HistoricalMetricPoint]) -> str | None:
    if len(history) < 2:
        return None
    delta = history[0].value - history[-1].value
    if abs(delta) < _ZERO:
        return _TREND_STABLE
    if delta > 0:
        return _TREND_POSITIVE
    return _TREND_NEGATIVE


def _margin_history(statements: list[FinancialStatement]) -> list[HistoricalMetricPoint]:
    return _build_metric_history(statements, lambda s: _ratio(_operating_income(s), s.revenue))


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None:
        return None
    if abs(denominator) < _ZERO:
        return None
    return numerator / denominator


def _margin_direction(margins: list[HistoricalMetricPoint]) -> str | None:
    if len(margins) < 2:
        return None
    delta = margins[0].value - margins[-1].value
    if abs(delta) < _ZERO:
        return _TREND_STABLE
    if delta > 0:
        return _TREND_POSITIVE
    return _TREND_NEGATIVE


def _net_debt_direction(net_debt_history: list[HistoricalMetricPoint]) -> str | None:
    if len(net_debt_history) < 2:
        return None
    delta = net_debt_history[0].value - net_debt_history[-1].value
    if abs(delta) < _ZERO:
        return _TREND_STABLE
    if delta < 0:
        return _TREND_POSITIVE
    return _TREND_NEGATIVE


def _build_historical_fundamentals(statements: list[FinancialStatement]) -> HistoricalFundamentals:
    revenue_history = _build_metric_history(statements, lambda s: s.revenue)
    ebitda_history = _build_metric_history(statements, lambda s: s.ebitda)
    ebit_history = _build_metric_history(statements, lambda s: s.ebit)
    operating_income_history = _build_metric_history(statements, _operating_income)
    net_income_history = _build_metric_history(statements, lambda s: s.net_income)
    free_cash_flow_history = _build_metric_history(statements, lambda s: s.free_cash_flow)
    net_debt_history = _build_metric_history(statements, lambda s: s.net_debt)
    eps_history = _build_metric_history(statements, _eps)
    shares_outstanding_history = _build_metric_history(statements, lambda s: s.shares_outstanding)
    margin_history = _margin_history(statements)

    trends = HistoricalFundamentalsTrends(
        revenue_cagr=_cagr(revenue_history),
        operating_income_cagr=_cagr(operating_income_history),
        net_income_cagr=_cagr(net_income_history),
        free_cash_flow_cagr=_cagr(free_cash_flow_history),
        revenue_direction=_direction_from_values(revenue_history),
        margin_direction=_margin_direction(margin_history),
        net_debt_direction=_net_debt_direction(net_debt_history),
    )

    return HistoricalFundamentals(
        revenue_history=revenue_history,
        ebitda_history=ebitda_history,
        ebit_history=ebit_history,
        operating_income_history=operating_income_history,
        net_income_history=net_income_history,
        free_cash_flow_history=free_cash_flow_history,
        net_debt_history=net_debt_history,
        eps_history=eps_history,
        shares_outstanding_history=shares_outstanding_history,
        trends=trends,
    )


def _build_detail(
    company: Company,
    latest_price: PriceHistory | None,
    latest_stmt: FinancialStatement | None,
    snapshot: KpiSnapshot | None,
    selected_statements: list[FinancialStatement],
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
        industry=company.industry,
        website=company.website,
        business_summary=company.business_summary,
        full_time_employees=company.full_time_employees,
        city=company.city,
        phone=company.phone,
        latest_gross_margins=company.gross_margins,
        latest_operating_margins=company.operating_margins,
        latest_profit_margins=company.profit_margins,
        latest_roe=company.roe,
        latest_roa=company.roa,
        latest_current_ratio=company.current_ratio,
        latest_quick_ratio=company.quick_ratio,
        latest_payout_ratio=company.payout_ratio,
        float_shares=company.float_shares,
        latest_dividend_rate=company.dividend_rate,
        latest_dividend_yield=company.dividend_yield,
        ex_dividend_date=company.ex_dividend_date.date() if company.ex_dividend_date else None,
        latest_five_year_avg_dividend_yield=company.five_year_avg_dividend_yield,
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
        historical_fundamentals=_build_historical_fundamentals(selected_statements),
    )
