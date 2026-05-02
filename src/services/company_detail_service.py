from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from src.models.company import Company
from src.models.company_executive import CompanyExecutive
from src.models.company_holder import CompanyHolder
from src.models.company_insider_transaction import CompanyInsiderTransaction
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.kpi_snapshot import KpiSnapshot
from src.models.price_history import PriceHistory
from src.repositories import (
    company_executive_repository,
    company_holder_repository,
    company_insider_transaction_repository,
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
_STRONG_DROP_THRESHOLD = -0.2


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
    revenue_history: list[HistoricalMetricPoint] = field(default_factory=list)
    ebitda_history: list[HistoricalMetricPoint] = field(default_factory=list)
    ebit_history: list[HistoricalMetricPoint] = field(default_factory=list)
    operating_income_history: list[HistoricalMetricPoint] = field(default_factory=list)
    net_income_history: list[HistoricalMetricPoint] = field(default_factory=list)
    free_cash_flow_history: list[HistoricalMetricPoint] = field(default_factory=list)
    net_debt_history: list[HistoricalMetricPoint] = field(default_factory=list)
    eps_history: list[HistoricalMetricPoint] = field(default_factory=list)
    shares_outstanding_history: list[HistoricalMetricPoint] = field(default_factory=list)
    revenue_growth_history: list[HistoricalMetricPoint] = field(default_factory=list)
    ebitda_growth_history: list[HistoricalMetricPoint] = field(default_factory=list)
    net_income_growth_history: list[HistoricalMetricPoint] = field(default_factory=list)
    free_cash_flow_growth_history: list[HistoricalMetricPoint] = field(default_factory=list)
    ebitda_margin_history: list[HistoricalMetricPoint] = field(default_factory=list)
    financial_anomalies: list[FinancialAnomaly] = field(default_factory=list)
    trends: HistoricalFundamentalsTrends = field(
        default_factory=lambda: HistoricalFundamentalsTrends(
            revenue_cagr=None,
            operating_income_cagr=None,
            net_income_cagr=None,
            free_cash_flow_cagr=None,
            revenue_direction=None,
            margin_direction=None,
            net_debt_direction=None,
        )
    )


@dataclass(frozen=True)
class FinancialAnomaly:
    metric_key: str
    fiscal_year: int
    kind: str


@dataclass(frozen=True)
class OwnershipHolderItem:
    holder_name: str
    holder_type: str
    weight: float | None = None
    shares: float | None = None
    market_value: float | None = None
    date_reported: date | None = None


@dataclass(frozen=True)
class OwnershipExecutiveItem:
    name: str
    title: str | None = None
    age: int | None = None
    total_pay: float | None = None


@dataclass(frozen=True)
class OwnershipInsiderItem:
    insider_name: str | None
    relation: str | None
    transaction_text: str | None
    ownership: str | None
    shares: float | None
    market_value: float | None
    start_date: date | None = None


@dataclass(frozen=True)
class CompanyFinancialDetail:
    company_id: int
    name: str = ""
    ticker: str | None = None
    sector: str | None = None
    country: str | None = None
    currency: str = "EUR"
    # Company profile
    industry: str | None = None
    website: str | None = None
    business_summary: str | None = None
    full_time_employees: int | None = None
    city: str | None = None
    phone: str | None = None
    # Fundamental Metrics (Latest from provider)
    latest_gross_margins: float | None = None
    latest_operating_margins: float | None = None
    latest_profit_margins: float | None = None
    latest_roe: float | None = None
    latest_roa: float | None = None
    latest_current_ratio: float | None = None
    latest_quick_ratio: float | None = None
    latest_payout_ratio: float | None = None
    # Shares and Volume
    float_shares: float | None = None
    # Dividend Info
    latest_dividend_rate: float | None = None
    latest_dividend_yield: float | None = None
    ex_dividend_date: date | None = None
    latest_five_year_avg_dividend_yield: float | None = None
    # Market data
    current_price: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    enterprise_value_yahoo: float | None = None
    last_refresh_at: datetime | None = None
    # Analyst summary
    analyst_target_price: float | None = None
    analyst_target_upside: float | None = None
    analyst_target_downside: float | None = None
    analyst_recommendation: str | None = None
    analyst_count: int | None = None
    forward_pe: float | None = None
    beta: float | None = None
    average_daily_volume: float | None = None
    confidence_level: str | None = None
    provider_source: str | None = None
    snapshot_source: str | None = None
    missing_fields: tuple[str, ...] = ()
    # Latest financial period
    fiscal_year: int | None = None
    period_type: str | None = None
    # Raw financials
    revenue: float | None = None
    ebitda: float | None = None
    ebit: float | None = None
    net_income: float | None = None
    free_cash_flow: float | None = None
    net_debt: float | None = None
    shares_outstanding: float | None = None
    # Valuation ratios
    pe_ratio: float | None = None
    pb_ratio: float | None = None
    ev_ebitda: float | None = None
    ev_sales: float | None = None
    fcf_yield: float | None = None
    # Quality ratios
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    roe: float | None = None
    roic: float | None = None
    # Growth
    revenue_growth: float | None = None
    ebitda_growth: float | None = None
    # Risk
    net_debt_to_ebitda: float | None = None
    # Data quality
    data_quality_score: float | None = None
    snapshot_date: date | None = None
    historical_fundamentals: HistoricalFundamentals = field(default_factory=HistoricalFundamentals)
    ceo_name: str | None = None
    cfo_name: str | None = None
    management_team: tuple[OwnershipExecutiveItem, ...] = ()
    major_holders: tuple[OwnershipHolderItem, ...] = ()
    top_shareholders: tuple[OwnershipHolderItem, ...] = ()
    institutional_holders: tuple[OwnershipHolderItem, ...] = ()
    insider_activity: tuple[OwnershipInsiderItem, ...] = ()


@dataclass(frozen=True)
class ValuationSummary:
    ev_ebitda: float | None
    pe_ratio: float | None
    fcf_yield: float | None
    valuation_view: str
    valuation_verdict: str


@dataclass(frozen=True)
class QualityMetricsSummary:
    profitability_score: float
    balance_sheet_score: float
    cash_flow_quality_score: float
    volatility_score: float


@dataclass(frozen=True)
class BusinessSummary:
    sector: str | None
    industry: str | None
    business_model: str | None
    market_cap: float | None
    enterprise_value: float | None
    analyst_target_price: float | None
    analyst_target_upside: float | None
    analyst_recommendation: str | None
    analyst_count: int | None


@dataclass(frozen=True)
class CapitalAllocationSummary:
    fcf_trend: str
    debt_trend: str
    reinvestment_vs_returns: str


@dataclass(frozen=True)
class DataQualitySummary:
    data_quality_score: float | None
    years_available: int
    missing_data: tuple[str, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MomentumSummary:
    performance_1m: float | None
    performance_6m: float | None
    performance_12m: float | None
    pct_vs_52w_high: float | None
    pct_vs_52w_low: float | None


@dataclass(frozen=True)
class OwnershipSummary:
    institutional_pct: float | None
    insiders_pct: float | None
    top_holders: tuple[OwnershipHolderItem, ...]


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
            executives = company_executive_repository.get_by_company(session, company_id)
            holders = company_holder_repository.get_by_company(session, company_id)
            insider_transactions = company_insider_transaction_repository.get_by_company(session, company_id)

            return _build_detail(
                company,
                latest_price,
                latest_stmt,
                snapshot,
                selected_statements,
                executives,
                holders,
                insider_transactions,
            )

    def compute_valuation_summary(
        self,
        detail: CompanyFinancialDetail,
        peer_ev_ebitda_median: float | None,
        peer_pe_median: float | None,
    ) -> ValuationSummary:
        view = _valuation_view(detail, peer_ev_ebitda_median, peer_pe_median)
        verdict = _valuation_verdict(view, detail.fcf_yield)
        return ValuationSummary(
            ev_ebitda=detail.ev_ebitda,
            pe_ratio=detail.pe_ratio,
            fcf_yield=detail.fcf_yield,
            valuation_view=view,
            valuation_verdict=verdict,
        )

    def compute_quality_metrics(self, detail: CompanyFinancialDetail) -> QualityMetricsSummary:
        profitability_score = _to_score(detail.roic, good=0.15, bad=0.02, lower_is_better=False)
        balance_sheet_score = _to_score(detail.net_debt_to_ebitda, good=1.0, bad=5.0, lower_is_better=True)
        cash_flow_quality_score = _to_score(detail.fcf_yield, good=0.06, bad=0.0, lower_is_better=False)
        volatility_score = _to_score(detail.beta, good=0.8, bad=1.8, lower_is_better=True)
        return QualityMetricsSummary(
            profitability_score=profitability_score,
            balance_sheet_score=balance_sheet_score,
            cash_flow_quality_score=cash_flow_quality_score,
            volatility_score=volatility_score,
        )

    def compute_business_summary(self, detail: CompanyFinancialDetail) -> BusinessSummary:
        return BusinessSummary(
            sector=detail.sector,
            industry=detail.industry,
            business_model=detail.business_summary,
            market_cap=detail.market_cap,
            enterprise_value=detail.enterprise_value,
            analyst_target_price=detail.analyst_target_price,
            analyst_target_upside=detail.analyst_target_upside,
            analyst_recommendation=detail.analyst_recommendation,
            analyst_count=detail.analyst_count,
        )

    def compute_allocation_metrics(self, detail: CompanyFinancialDetail) -> CapitalAllocationSummary:
        historical = detail.historical_fundamentals
        fcf_trend = _trend_from_growth_points(historical.free_cash_flow_growth_history)
        debt_trend = historical.trends.net_debt_direction or "stable"
        reinvestment_vs_returns = _reinvestment_vs_returns_label(detail.roic, detail.fcf_yield)
        return CapitalAllocationSummary(
            fcf_trend=fcf_trend,
            debt_trend=debt_trend,
            reinvestment_vs_returns=reinvestment_vs_returns,
        )

    def compute_data_quality_summary(self, detail: CompanyFinancialDetail) -> DataQualitySummary:
        warnings: list[str] = []
        if detail.data_quality_score is not None and detail.data_quality_score < 60.0:
            warnings.append("low data quality score")
        if detail.missing_fields:
            warnings.append("missing key fields")
        years_available = len(detail.historical_fundamentals.revenue_history)
        return DataQualitySummary(
            data_quality_score=detail.data_quality_score,
            years_available=years_available,
            missing_data=detail.missing_fields,
            warnings=tuple(warnings),
        )

    def compute_momentum_summary(self, company_id: int) -> MomentumSummary:
        with self.session_scope_factory() as session:
            prices = price_history_repository.get_by_company(session, company_id)
        if not prices:
            return MomentumSummary(None, None, None, None, None)
        latest = prices[0]
        latest_date = latest.date
        latest_close = latest.close
        perf_1m = _performance_since(prices, latest_date - timedelta(days=30), latest_close)
        perf_6m = _performance_since(prices, latest_date - timedelta(days=182), latest_close)
        perf_12m = _performance_since(prices, latest_date - timedelta(days=365), latest_close)
        one_year_window = [p for p in prices if p.date >= latest_date - timedelta(days=365)]
        if not one_year_window:
            one_year_window = prices
        high_52w = max((p.high if p.high is not None else p.close) for p in one_year_window)
        low_52w = min((p.low if p.low is not None else p.close) for p in one_year_window)
        pct_vs_52w_high = None if abs(high_52w) < _ZERO else (latest_close - high_52w) / high_52w
        pct_vs_52w_low = None if abs(low_52w) < _ZERO else (latest_close - low_52w) / low_52w
        return MomentumSummary(
            performance_1m=perf_1m,
            performance_6m=perf_6m,
            performance_12m=perf_12m,
            pct_vs_52w_high=pct_vs_52w_high,
            pct_vs_52w_low=pct_vs_52w_low,
        )

    def compute_ownership_summary(self, detail: CompanyFinancialDetail) -> OwnershipSummary:
        institutional_pct = _sum_holder_weights(detail.institutional_holders)
        insider_candidates = [holder for holder in detail.major_holders if holder.holder_type == "insider"]
        insiders_pct = _sum_holder_weights(tuple(insider_candidates))
        top_holders = tuple(detail.top_shareholders[:5])
        return OwnershipSummary(
            institutional_pct=institutional_pct,
            insiders_pct=insiders_pct,
            top_holders=top_holders,
        )


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


def _target_move_ratio(current_price: float | None, target_price: float | None) -> float | None:
    if current_price is None or target_price is None:
        return None
    if abs(current_price) < _ZERO:
        return None
    return (target_price - current_price) / current_price


def _confidence_level(analyst_count: int | None, data_quality_score: float | None) -> str | None:
    if analyst_count is None and data_quality_score is None:
        return None
    if analyst_count is None:
        return "medium" if (data_quality_score or 0.0) >= 60.0 else "low"
    if analyst_count >= 12:
        return "high"
    if analyst_count >= 5:
        return "medium"
    return "low"


def _missing_fields(
    *,
    analyst_target_price: float | None,
    analyst_count: int | None,
    forward_pe: float | None,
    beta: float | None,
    current_ratio: float | None,
    quick_ratio: float | None,
    dividend_yield: float | None,
    average_volume: float | None,
    shares_outstanding: float | None,
    float_shares: float | None,
    data_quality_score: float | None,
) -> tuple[str, ...]:
    field_values = {
        "target_price": analyst_target_price,
        "analyst_count": analyst_count,
        "forward_pe": forward_pe,
        "beta": beta,
        "current_ratio": current_ratio,
        "quick_ratio": quick_ratio,
        "dividend_yield": dividend_yield,
        "average_volume": average_volume,
        "shares_outstanding": shares_outstanding,
        "float_shares": float_shares,
        "data_quality_score": data_quality_score,
    }
    return tuple(field_name for field_name, value in field_values.items() if value is None)


def _executive_matches_role(executive: CompanyExecutive, role_keywords: tuple[str, ...]) -> bool:
    if executive.title is None:
        return False
    title = executive.title.lower()
    return any(keyword in title for keyword in role_keywords)


def _map_executive_item(executive: CompanyExecutive) -> OwnershipExecutiveItem:
    return OwnershipExecutiveItem(
        name=executive.name,
        title=executive.title,
        age=executive.age,
        total_pay=executive.total_pay,
    )


def _map_holder_item(holder: CompanyHolder) -> OwnershipHolderItem:
    return OwnershipHolderItem(
        holder_name=holder.holder_name,
        holder_type=holder.holder_type,
        weight=holder.weight,
        shares=holder.shares,
        market_value=holder.market_value,
        date_reported=holder.date_reported,
    )


def _map_insider_item(insider: CompanyInsiderTransaction) -> OwnershipInsiderItem:
    return OwnershipInsiderItem(
        insider_name=insider.insider_name,
        relation=insider.relation,
        transaction_text=insider.transaction_text,
        ownership=insider.ownership,
        shares=insider.shares,
        market_value=insider.market_value,
        start_date=insider.start_date,
    )


def _holder_sort_weight(holder: CompanyHolder) -> float:
    if holder.weight is None:
        return -1.0
    return holder.weight


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


def compute_growth_rates(points: list[HistoricalMetricPoint]) -> list[HistoricalMetricPoint]:
    if len(points) < 2:
        return []
    ordered = sorted(points, key=lambda p: p.fiscal_year, reverse=True)
    growth_points: list[HistoricalMetricPoint] = []
    for index, point in enumerate(ordered):
        previous = ordered[index + 1] if index + 1 < len(ordered) else None
        growth = None
        if previous is not None and abs(previous.value) >= _ZERO:
            growth = (point.value - previous.value) / abs(previous.value)
        if growth is None:
            continue
        growth_points.append(
            HistoricalMetricPoint(
                fiscal_year=point.fiscal_year,
                period_type=point.period_type,
                value=growth,
            )
        )
    return growth_points


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
    revenue_growth_history = compute_growth_rates(revenue_history)
    ebitda_growth_history = compute_growth_rates(ebitda_history)
    net_income_growth_history = compute_growth_rates(net_income_history)
    free_cash_flow_growth_history = compute_growth_rates(free_cash_flow_history)
    anomalies: list[FinancialAnomaly] = []
    for point in ebitda_history:
        if point.value < 0:
            anomalies.append(FinancialAnomaly(metric_key="ebitda", fiscal_year=point.fiscal_year, kind="negative"))
    for key, history in (
        ("revenue", revenue_growth_history),
        ("ebitda", ebitda_growth_history),
        ("net_income", net_income_growth_history),
        ("free_cash_flow", free_cash_flow_growth_history),
    ):
        for point in history:
            if point.value <= _STRONG_DROP_THRESHOLD:
                anomalies.append(FinancialAnomaly(metric_key=key, fiscal_year=point.fiscal_year, kind="strong_drop"))

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
        revenue_growth_history=revenue_growth_history,
        ebitda_growth_history=ebitda_growth_history,
        net_income_growth_history=net_income_growth_history,
        free_cash_flow_growth_history=free_cash_flow_growth_history,
        ebitda_margin_history=margin_history,
        financial_anomalies=anomalies,
        trends=trends,
    )


def _build_detail(
    company: Company,
    latest_price: PriceHistory | None,
    latest_stmt: FinancialStatement | None,
    snapshot: KpiSnapshot | None,
    selected_statements: list[FinancialStatement],
    executives: list[CompanyExecutive],
    holders: list[CompanyHolder],
    insider_transactions: list[CompanyInsiderTransaction],
) -> CompanyFinancialDetail:
    current_price = latest_price.close if latest_price is not None else None

    market_cap = _metric(snapshot, "market_cap") or company.market_cap
    enterprise_value = _metric(snapshot, "enterprise_value")
    data_quality_score = _metric(snapshot, "data_quality_score")
    target_upside = _target_move_ratio(current_price, company.analyst_target_price)
    target_downside = None if target_upside is None else min(target_upside, 0.0)
    confidence = _confidence_level(company.analyst_count, data_quality_score)

    revenue = latest_stmt.revenue if latest_stmt is not None else None
    ebitda = latest_stmt.ebitda if latest_stmt is not None else None
    ebit = latest_stmt.ebit if latest_stmt is not None else None
    net_income = latest_stmt.net_income if latest_stmt is not None else None
    free_cash_flow = latest_stmt.free_cash_flow if latest_stmt is not None else None
    net_debt = latest_stmt.net_debt if latest_stmt is not None else None
    shares_outstanding = latest_stmt.shares_outstanding if latest_stmt is not None else None
    missing_fields = _missing_fields(
        analyst_target_price=company.analyst_target_price,
        analyst_count=company.analyst_count,
        forward_pe=company.forward_pe,
        beta=company.beta,
        current_ratio=company.current_ratio,
        quick_ratio=company.quick_ratio,
        dividend_yield=company.dividend_yield,
        average_volume=company.average_daily_volume,
        shares_outstanding=shares_outstanding or company.shares_outstanding,
        float_shares=company.float_shares,
        data_quality_score=data_quality_score,
    )
    management_team = tuple(_map_executive_item(executive) for executive in executives[:12])
    ceo = next((item for item in executives if _executive_matches_role(item, ("chief executive", "ceo"))), None)
    cfo = next((item for item in executives if _executive_matches_role(item, ("chief financial", "cfo"))), None)

    major_holders = tuple(_map_holder_item(holder) for holder in holders if holder.holder_type == "major")
    institutional_holders_raw = [holder for holder in holders if holder.holder_type == "institutional"]
    institutional_holders = tuple(_map_holder_item(holder) for holder in institutional_holders_raw[:15])
    top_shareholder_candidates = [
        holder for holder in holders if holder.holder_type in {"institutional", "mutual_fund"}
    ]
    top_shareholder_candidates.sort(key=_holder_sort_weight, reverse=True)
    top_shareholders = tuple(_map_holder_item(holder) for holder in top_shareholder_candidates[:15])
    insider_activity = tuple(_map_insider_item(item) for item in insider_transactions[:20])

    return CompanyFinancialDetail(
        company_id=company.id,
        ticker=company.ticker,
        name=company.name,
        sector=company.sector,
        country=company.country,
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
        enterprise_value_yahoo=company.enterprise_value_yahoo,
        last_refresh_at=company.last_universe_refresh_at,
        analyst_target_price=company.analyst_target_price,
        analyst_target_upside=target_upside,
        analyst_target_downside=target_downside,
        analyst_recommendation=company.analyst_recommendation,
        analyst_count=company.analyst_count,
        forward_pe=company.forward_pe,
        beta=company.beta,
        average_daily_volume=company.average_daily_volume,
        confidence_level=confidence,
        provider_source=company.source_origin,
        snapshot_source=snapshot.source if snapshot is not None else None,
        missing_fields=missing_fields,
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
        data_quality_score=data_quality_score,
        snapshot_date=snapshot.snapshot_date if snapshot is not None else None,
        historical_fundamentals=_build_historical_fundamentals(selected_statements),
        ceo_name=ceo.name if ceo is not None else None,
        cfo_name=cfo.name if cfo is not None else None,
        management_team=management_team,
        major_holders=major_holders,
        top_shareholders=top_shareholders,
        institutional_holders=institutional_holders,
        insider_activity=insider_activity,
    )


def _to_score(value: float | None, *, good: float, bad: float, lower_is_better: bool) -> float:
    if value is None:
        return 0.0
    if lower_is_better:
        if value <= good:
            return 100.0
        if value >= bad:
            return 0.0
        return round((1.0 - ((value - good) / (bad - good))) * 100.0, 2)
    if value >= good:
        return 100.0
    if value <= bad:
        return 0.0
    return round(((value - bad) / (good - bad)) * 100.0, 2)


def _valuation_view(
    detail: CompanyFinancialDetail,
    peer_ev_ebitda_median: float | None,
    peer_pe_median: float | None,
) -> str:
    cheap_signals = 0
    expensive_signals = 0
    if detail.ev_ebitda is not None and peer_ev_ebitda_median is not None:
        if detail.ev_ebitda < peer_ev_ebitda_median:
            cheap_signals += 1
        elif detail.ev_ebitda > peer_ev_ebitda_median:
            expensive_signals += 1
    if detail.pe_ratio is not None and peer_pe_median is not None:
        if detail.pe_ratio < peer_pe_median:
            cheap_signals += 1
        elif detail.pe_ratio > peer_pe_median:
            expensive_signals += 1
    if cheap_signals > expensive_signals:
        return "cheap"
    if expensive_signals > cheap_signals:
        return "expensive"
    return "neutral"


def _valuation_verdict(view: str, fcf_yield: float | None) -> str:
    if view == "cheap" and fcf_yield is not None and fcf_yield > 0.04:
        return "attractive valuation"
    if view == "expensive":
        return "premium valuation"
    return "fairly valued"


def _trend_from_growth_points(points: list[HistoricalMetricPoint]) -> str:
    if not points:
        return "stable"
    latest = sorted(points, key=lambda point: point.fiscal_year, reverse=True)[0]
    if latest.value > 0.05:
        return "improving"
    if latest.value < -0.05:
        return "deteriorating"
    return "stable"


def _reinvestment_vs_returns_label(roic: float | None, fcf_yield: float | None) -> str:
    if roic is None and fcf_yield is None:
        return "insufficient data"
    if roic is not None and roic >= 0.12 and (fcf_yield is None or fcf_yield >= 0):
        return "balanced reinvestment and returns"
    if fcf_yield is not None and fcf_yield < 0:
        return "reinvestment currently pressuring returns"
    return "moderate capital efficiency"


def _performance_since(prices_desc: list[PriceHistory], target_date: date, latest_close: float) -> float | None:
    reference = next((item for item in prices_desc if item.date <= target_date), None)
    if reference is None:
        return None
    if abs(reference.close) < _ZERO:
        return None
    return (latest_close - reference.close) / reference.close


def _sum_holder_weights(holders: tuple[OwnershipHolderItem, ...]) -> float | None:
    weights = [holder.weight for holder in holders if holder.weight is not None]
    if not weights:
        return None
    return sum(weights)
