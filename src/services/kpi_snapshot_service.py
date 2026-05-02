from __future__ import annotations

import logging
import math
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
from src.services.scoring_service import CompanyTotalScore, RankedCompanyTotalScore, ScoringService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_LOGGER = logging.getLogger(__name__)
DATA_QUALITY_SCORE_KEY: str = "data_quality_score"
_DATA_QUALITY_WEIGHT_FINANCIAL_COMPLETENESS: float = 0.40
_DATA_QUALITY_WEIGHT_PRICE_AVAILABILITY: float = 0.20
_DATA_QUALITY_WEIGHT_MARKET_CAP: float = 0.20
_DATA_QUALITY_WEIGHT_RATIO_COMPLETENESS: float = 0.20
_DATA_QUALITY_FINANCIAL_FIELDS: tuple[str, ...] = (
    "revenue",
    "ebit",
    "ebitda",
    "net_income",
    "total_assets",
    "total_equity",
    "total_debt",
    "net_debt",
    "free_cash_flow",
    "shares_outstanding",
)
_DATA_QUALITY_RATIO_FIELDS: tuple[str, ...] = (
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "ev_ebit",
    "fcf_yield",
    "roe",
    "roic",
    "operating_margin",
    "net_debt_to_ebitda",
)
_DATA_QUALITY_GROWTH_FIELDS: tuple[str, ...] = ("revenue_growth", "ebitda_growth")


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
    price_source: str


@dataclass
class CompanyKpiContextLoadResult:
    context: CompanyKpiContext | None
    error: str | None = None


@dataclass
class KpiSnapshotService:
    session_scope_factory: SessionScopeFactory = get_session
    ratio_service: RatioService = field(default_factory=RatioService)
    scoring_service: ScoringService = field(default_factory=ScoringService)
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
                _LOGGER.warning(
                    "kpi snapshot load failed | stage=load company_id=%s snapshot_date=%s error=%s",
                    company_id,
                    snapshot_date,
                    load.error,
                )
                return KpiSnapshotServiceResult(
                    company_id=company_id,
                    snapshot_date=snapshot_date,
                    success=False,
                    error=load.error,
                    stage="load",
                )
            context = load.context

            stmt = context.latest_statement
            ratios = self.ratio_service.compute_all(
                company_id=company_id,
                fiscal_year=stmt.fiscal_year,
                price=context.price,
                stmt=stmt,
                previous_stmt=context.previous_statement,
                gross_profit=stmt.gross_profit,
                current_assets=stmt.current_assets,
                current_liabilities=stmt.current_liabilities,
                interest_expense=stmt.interest_expense,
            )
            metrics = _ratios_to_metrics_payload(ratios, context.company, stmt, context.previous_statement)
            metrics[DATA_QUALITY_SCORE_KEY] = _compute_data_quality_score(
                company=context.company,
                latest_statement=context.latest_statement,
                previous_statement=context.previous_statement,
                price_source=context.price_source,
                ratio_metrics=metrics,
            )

            snapshot = build_snapshot_payload(
                company_id=company_id,
                snapshot_date=snapshot_date,
                metrics=metrics,
                source=self.source_name,
            )
            scored_snapshot = self.scoring_service.apply_scores(snapshot)
            stored = kpi_snapshot_repository.upsert(session, scored_snapshot)
            _LOGGER.info(
                (
                    "kpi snapshot upserted | stage=compute company_id=%s snapshot_id=%s "
                    "snapshot_date=%s source=%s data_quality_score=%s total_score=%s"
                ),
                company_id,
                stored.id,
                snapshot_date,
                self.source_name,
                stored.metrics.get(DATA_QUALITY_SCORE_KEY),
                stored.metrics.get("total_score"),
            )
            return KpiSnapshotServiceResult(
                company_id=company_id,
                snapshot_date=snapshot_date,
                success=True,
                snapshot_id=stored.id,
                metrics=stored.metrics,
            )

    def refresh_universe_kpi_snapshots(
        self,
        snapshot_date: date,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> UniverseKpiSnapshotRefreshResult:
        target_max_market_cap = self.default_max_market_cap if max_market_cap is None else max_market_cap
        target_min_avg_daily_volume = (
            self.default_min_average_daily_volume if min_average_daily_volume is None else min_average_daily_volume
        )
        target_country = self.default_country if country is None else country

        with self.session_scope_factory() as session:
            investable = company_repository.get_investable_universe(
                session,
                max_market_cap=target_max_market_cap,
                min_average_daily_volume=target_min_avg_daily_volume,
                country=target_country,
            )
            companies = [(company.id, company.ticker) for company in investable]
        _LOGGER.info(
            "kpi snapshot universe refresh started | stage=refresh total=%s snapshot_date=%s",
            len(companies),
            snapshot_date,
        )

        success_count = 0
        errors: list[UniverseKpiSnapshotError] = []

        for company_id, ticker in companies:
            try:
                result = self.compute_and_upsert_for_company(
                    company_id=company_id,
                    snapshot_date=snapshot_date,
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                _LOGGER.error(
                    (
                        "kpi snapshot refresh unexpected error | stage=unexpected company_id=%s "
                        "ticker=%s snapshot_date=%s error=%s"
                    ),
                    company_id,
                    ticker,
                    snapshot_date,
                    exc,
                )
                errors.append(
                    UniverseKpiSnapshotError(
                        company_id=company_id,
                        ticker=ticker,
                        error=str(exc),
                        stage="unexpected",
                    )
                )
                continue

            if result.success:
                success_count += 1
                continue

            _LOGGER.warning(
                ("kpi snapshot refresh failed | stage=%s company_id=%s ticker=%s snapshot_date=%s error=%s"),
                result.stage,
                company_id,
                ticker,
                snapshot_date,
                result.error,
            )
            errors.append(
                UniverseKpiSnapshotError(
                    company_id=company_id,
                    ticker=ticker,
                    error=result.error or "unknown error",
                    stage=result.stage,
                )
            )

        failed_count = len(errors)
        _LOGGER.info(
            (
                "kpi snapshot universe refresh completed | stage=refresh total=%s "
                "success_count=%s failed_count=%s snapshot_date=%s"
            ),
            len(companies),
            success_count,
            failed_count,
            snapshot_date,
        )
        return UniverseKpiSnapshotRefreshResult(
            total=len(companies),
            success_count=success_count,
            failed_count=failed_count,
            errors=errors,
        )

    def rank_universe_by_total_score(
        self,
        max_market_cap: float | None = None,
        min_average_daily_volume: float | None = None,
        country: str | None = None,
    ) -> list[RankedCompanyTotalScore]:
        target_max_market_cap = self.default_max_market_cap if max_market_cap is None else max_market_cap
        target_min_avg_daily_volume = (
            self.default_min_average_daily_volume if min_average_daily_volume is None else min_average_daily_volume
        )
        target_country = self.default_country if country is None else country

        with self.session_scope_factory() as session:
            investable = company_repository.get_investable_universe(
                session,
                max_market_cap=target_max_market_cap,
                min_average_daily_volume=target_min_avg_daily_volume,
                country=target_country,
            )
            company_scores = _load_universe_company_total_scores(
                session=session,
                investable=investable,
                scoring_service=self.scoring_service,
            )
        return self.scoring_service.rank_companies_by_total_score(company_scores)


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
    price, price_source = _derive_company_price(session, company, latest_statement)
    if price is None:
        return CompanyKpiContextLoadResult(context=None, error="no usable price data")
    if price_source is None:
        return CompanyKpiContextLoadResult(context=None, error="price source unavailable")

    return CompanyKpiContextLoadResult(
        context=CompanyKpiContext(
            company=company,
            latest_statement=latest_statement,
            previous_statement=previous_statement,
            price=price,
            price_source=price_source,
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
) -> tuple[float | None, str | None]:
    latest_price = price_history_repository.get_latest(session, company.id)
    if latest_price is not None:
        return latest_price.close, "price_history"
    if company.market_cap is not None and latest_statement.shares_outstanding is not None:
        if latest_statement.shares_outstanding > 0:
            return company.market_cap / latest_statement.shares_outstanding, "market_cap_fallback"
    return None, None


def _ratios_to_metrics_payload(
    ratios: CompanyRatios,
    company: Company,
    stmt: FinancialStatement,
    previous_stmt: FinancialStatement | None = None,
) -> dict[str, float | int | None]:
    payload: dict[str, float | int | None] = {
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
        "ebitda_margin": ratios.ebitda_margin,
        "revenue_growth": ratios.revenue_growth,
        "ebitda_growth": ratios.ebitda_growth,
        "net_debt_to_ebitda": ratios.net_debt_to_ebitda,
        "current_ratio": ratios.current_ratio,
        "interest_coverage": ratios.interest_coverage,
        "beta": company.beta,
        "analyst_target_price": company.analyst_target_price,
        "analyst_recommendation": company.analyst_recommendation,
        "analyst_count": company.analyst_count,
        "forward_pe": company.forward_pe,
        "asset_turnover": ratios.asset_turnover,
        "roa": ratios.roa,
        "ebit_margin": ratios.ebit_margin,
        "net_margin": ratios.net_margin,
        "debt_to_equity": ratios.debt_to_equity,
        "fcf_margin": ratios.fcf_margin,
        "cash_conversion_ratio": ratios.cash_conversion_ratio,
        "ev_sales": ratios.ev_sales,
        "price_to_fcf": ratios.price_to_fcf,
        "ps_ratio": ratios.ps_ratio,
        "revenue_cagr_3y": ratios.revenue_cagr_3y,
        "ebitda_cagr_3y": ratios.ebitda_cagr_3y,
        "net_income_growth": ratios.net_income_growth,
        "fcf_growth": ratios.fcf_growth,
        "gross_profit_growth": ratios.gross_profit_growth,
        "net_debt_growth": ratios.net_debt_growth,
    }
    payload["gross_profitability"] = _safe_divide(stmt.gross_profit, stmt.total_assets)
    payload["cfo_to_net_income"] = _safe_divide(stmt.operating_cash_flow, stmt.net_income)
    payload["cfo_to_ebit"] = _safe_divide(stmt.operating_cash_flow, stmt.ebit)
    payload["accrual_ratio"] = _accrual_ratio(stmt.net_income, stmt.operating_cash_flow, stmt.total_assets)
    payload["ev_fcf"] = _safe_divide(ratios.ev, stmt.free_cash_flow) if ratios.ev else None
    payload["altman_z_proxy"] = _altman_z_proxy(stmt, ratios.mkt_cap)
    payload["ronic"] = _ronic(stmt, previous_stmt)
    payload["capex_to_revenue"] = _capex_to_revenue_ratio(stmt)
    payload["shares_growth"] = _shares_growth(stmt, previous_stmt)
    payload["cfo_margin"] = _cfo_margin(stmt)
    payload["cfo_streak_negative"] = _cfo_streak_negative(stmt, previous_stmt)
    return payload


def _safe_divide(num: float | None, den: float | None) -> float | None:
    if num is None or den is None:
        return None
    if not math.isfinite(num) or not math.isfinite(den):
        return None
    if abs(den) < 1e-9:
        return None
    if den <= 0:
        return None
    return num / den


def _accrual_ratio(
    net_income: float | None,
    operating_cash_flow: float | None,
    total_assets: float | None,
) -> float | None:
    if net_income is None or operating_cash_flow is None or total_assets is None:
        return None
    if not math.isfinite(net_income) or not math.isfinite(operating_cash_flow):
        return None
    if total_assets is None or not math.isfinite(total_assets) or total_assets <= 0:
        return None
    return (net_income - operating_cash_flow) / total_assets


def _altman_z_proxy(stmt: FinancialStatement, market_cap: float) -> float | None:
    ta = stmt.total_assets
    if ta is None or ta <= 0:
        return None
    ca = stmt.current_assets
    cl = stmt.current_liabilities
    ebit = stmt.ebit
    td = stmt.total_debt
    rev = stmt.revenue
    if any(v is None for v in (ca, cl, ebit, rev)):
        return None
    wc_ta = (ca - cl) / ta
    ebit_ta = ebit / ta
    rev_ta = rev / ta
    eq_debt = 0.0
    if td is not None and td > 0 and market_cap > 0:
        eq_debt = market_cap / td
    z = 1.2 * wc_ta + 3.3 * ebit_ta + 0.6 * eq_debt + 1.0 * rev_ta
    if not math.isfinite(z):
        return None
    return z


def _ronic(
    stmt: FinancialStatement,
    previous_stmt: FinancialStatement | None,
) -> float | None:
    if previous_stmt is None:
        return None
    curr_eq = stmt.total_equity
    prev_eq = previous_stmt.total_equity
    if curr_eq is None or prev_eq is None:
        return None
    curr_nd = stmt.net_debt or 0.0
    prev_nd = previous_stmt.net_debt or 0.0
    delta_cap = (curr_eq + curr_nd) - (prev_eq + prev_nd)
    if delta_cap <= 0:
        return None
    curr_ebit = stmt.ebit
    prev_ebit = previous_stmt.ebit
    if curr_ebit is not None and prev_ebit is not None:
        result = (curr_ebit - prev_ebit) / delta_cap
        if math.isfinite(result):
            return result
    curr_ebitda = stmt.ebitda
    prev_ebitda = previous_stmt.ebitda
    if curr_ebitda is not None and prev_ebitda is not None:
        result = (curr_ebitda - prev_ebitda) / delta_cap
        if math.isfinite(result):
            return result
    return None


def _capex_to_revenue_ratio(stmt: FinancialStatement) -> float | None:
    capex = stmt.capex
    revenue = stmt.revenue
    if capex is None or revenue is None:
        return None
    if not math.isfinite(capex) or not math.isfinite(revenue):
        return None
    if revenue <= 0:
        return None
    return abs(capex) / revenue


def _shares_growth(
    stmt: FinancialStatement,
    previous_stmt: FinancialStatement | None,
) -> float | None:
    if previous_stmt is None:
        return None
    curr = stmt.shares_outstanding
    prev = previous_stmt.shares_outstanding
    if curr is None or prev is None:
        return None
    if not math.isfinite(curr) or not math.isfinite(prev):
        return None
    if prev <= 0:
        return None
    return (curr - prev) / prev


def _cfo_margin(stmt: FinancialStatement) -> float | None:
    cfo = stmt.operating_cash_flow
    revenue = stmt.revenue
    if cfo is None or revenue is None:
        return None
    if not math.isfinite(cfo) or not math.isfinite(revenue):
        return None
    if revenue <= 0:
        return None
    return cfo / revenue


def _cfo_streak_negative(
    stmt: FinancialStatement,
    previous_stmt: FinancialStatement | None,
) -> int:
    curr_cfo = stmt.operating_cash_flow
    curr_neg = curr_cfo is not None and math.isfinite(curr_cfo) and curr_cfo < 0
    if not curr_neg:
        return 0
    if previous_stmt is None:
        return 1
    prev_cfo = previous_stmt.operating_cash_flow
    prev_neg = prev_cfo is not None and math.isfinite(prev_cfo) and prev_cfo < 0
    return 2 if prev_neg else 1


def _load_universe_company_total_scores(
    session: Session,
    investable: list[Company],
    scoring_service: ScoringService,
) -> list[CompanyTotalScore]:
    company_scores: list[CompanyTotalScore] = []
    for company in investable:
        snapshot = kpi_snapshot_repository.get_latest_by_company(session, company.id)
        company_scores.append(
            CompanyTotalScore(
                company_id=company.id,
                ticker=company.ticker,
                total_score=scoring_service.get_snapshot_total_score(snapshot),
                sector=company.sector,
            )
        )
    return company_scores


def _compute_data_quality_score(
    *,
    company: Company,
    latest_statement: FinancialStatement,
    previous_statement: FinancialStatement | None,
    price_source: str,
    ratio_metrics: dict[str, float | int | None],
) -> float:
    financial_completeness = _ratio_from_count(
        sum(
            1
            for field_name in _DATA_QUALITY_FINANCIAL_FIELDS
            if _is_quality_number(getattr(latest_statement, field_name))
        ),
        len(_DATA_QUALITY_FINANCIAL_FIELDS),
    )
    price_availability = _price_source_quality(price_source)
    market_cap_quality = 100.0 if _is_positive_quality_number(company.market_cap) else 0.0
    ratio_fields = list(_DATA_QUALITY_RATIO_FIELDS)
    if previous_statement is not None:
        ratio_fields.extend(_DATA_QUALITY_GROWTH_FIELDS)
    ratio_completeness = _ratio_from_count(
        sum(1 for field_name in ratio_fields if _is_quality_number(ratio_metrics.get(field_name))),
        len(ratio_fields),
    )
    score = (
        financial_completeness * _DATA_QUALITY_WEIGHT_FINANCIAL_COMPLETENESS
        + price_availability * _DATA_QUALITY_WEIGHT_PRICE_AVAILABILITY
        + market_cap_quality * _DATA_QUALITY_WEIGHT_MARKET_CAP
        + ratio_completeness * _DATA_QUALITY_WEIGHT_RATIO_COMPLETENESS
    )
    return round(score, 2)


def _ratio_from_count(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (count / total) * 100.0


def _price_source_quality(value: str) -> float:
    if value == "price_history":
        return 100.0
    if value == "market_cap_fallback":
        return 60.0
    return 0.0


def _is_quality_number(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(numeric)


def _is_positive_quality_number(value: object) -> bool:
    if not _is_quality_number(value):
        return False
    return float(value) > 0.0
