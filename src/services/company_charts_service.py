from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from src.repositories import price_history_repository
from src.repositories.database import get_session
from src.services.company_detail_service import CompanyFinancialDetail

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]
_DEFAULT_MAX_PRICE_POINTS = 260
_ZERO = 1e-9
_SCORE_ORDER: tuple[tuple[str, str], ...] = (
    ("quality", "Quality"),
    ("value", "Value"),
    ("growth", "Growth"),
    ("risk", "Risk"),
)


@dataclass(frozen=True)
class DatedChartPoint:
    point_date: date
    value: float


@dataclass(frozen=True)
class YearlyChartPoint:
    fiscal_year: int
    value: float


@dataclass(frozen=True)
class ScoreBreakdownPoint:
    key: str
    label: str
    score: float


@dataclass(frozen=True)
class FundamentalChartsData:
    revenue_points: list[YearlyChartPoint]
    operating_income_points: list[YearlyChartPoint]
    margin_points: list[YearlyChartPoint]
    debt_points: list[YearlyChartPoint]


@dataclass(frozen=True)
class CompanyChartsData:
    price_points: list[DatedChartPoint]
    fundamentals: FundamentalChartsData
    score_breakdown: list[ScoreBreakdownPoint]


@dataclass(frozen=True)
class ScoreBreakdownInput:
    quality: float | None
    value: float | None
    growth: float | None
    risk: float | None


@dataclass
class CompanyChartsService:
    session_scope_factory: SessionScopeFactory = field(default=get_session)

    def build_company_charts_data(
        self,
        company_id: int,
        *,
        financial_detail: CompanyFinancialDetail | None,
        score_breakdown: ScoreBreakdownInput | None,
        max_price_points: int = _DEFAULT_MAX_PRICE_POINTS,
    ) -> CompanyChartsData:
        return CompanyChartsData(
            price_points=self.prepare_price_history(company_id, max_price_points=max_price_points),
            fundamentals=self.prepare_fundamentals(financial_detail),
            score_breakdown=self.prepare_score_breakdown(score_breakdown),
        )

    def prepare_price_history(
        self, company_id: int, *, max_price_points: int = _DEFAULT_MAX_PRICE_POINTS
    ) -> list[DatedChartPoint]:
        with self.session_scope_factory() as session:
            records = price_history_repository.get_by_company(session, company_id)
        if max_price_points <= 0:
            return []
        selected = records[:max_price_points]
        selected.sort(key=lambda entry: entry.date)
        return [DatedChartPoint(point_date=entry.date, value=entry.close) for entry in selected]

    def prepare_fundamentals(self, financial_detail: CompanyFinancialDetail | None) -> FundamentalChartsData:
        if financial_detail is None:
            return FundamentalChartsData(
                revenue_points=[],
                operating_income_points=[],
                margin_points=[],
                debt_points=[],
            )

        revenue_points = _to_yearly_points(financial_detail.historical_fundamentals.revenue_history)
        operating_income_points = _to_yearly_points(financial_detail.historical_fundamentals.operating_income_history)
        debt_points = _to_yearly_points(financial_detail.historical_fundamentals.net_debt_history)
        margin_points = _build_margin_points(revenue_points, operating_income_points)
        return FundamentalChartsData(
            revenue_points=revenue_points,
            operating_income_points=operating_income_points,
            margin_points=margin_points,
            debt_points=debt_points,
        )

    def prepare_score_breakdown(self, score_breakdown: ScoreBreakdownInput | None) -> list[ScoreBreakdownPoint]:
        if score_breakdown is None:
            return []
        values = {
            "quality": score_breakdown.quality,
            "value": score_breakdown.value,
            "growth": score_breakdown.growth,
            "risk": score_breakdown.risk,
        }
        points: list[ScoreBreakdownPoint] = []
        for key, label in _SCORE_ORDER:
            score = values[key]
            if score is None:
                continue
            points.append(ScoreBreakdownPoint(key=key, label=label, score=score))
        return points


def _to_yearly_points(history: list[object]) -> list[YearlyChartPoint]:
    points = [YearlyChartPoint(fiscal_year=point.fiscal_year, value=point.value) for point in history]
    points.sort(key=lambda point: point.fiscal_year)
    return points


def _build_margin_points(
    revenue_points: list[YearlyChartPoint],
    operating_income_points: list[YearlyChartPoint],
) -> list[YearlyChartPoint]:
    revenue_by_year = {point.fiscal_year: point.value for point in revenue_points}
    operating_by_year = {point.fiscal_year: point.value for point in operating_income_points}
    years = sorted(set(revenue_by_year) & set(operating_by_year))
    margins: list[YearlyChartPoint] = []
    for year in years:
        revenue = revenue_by_year[year]
        operating_income = operating_by_year[year]
        if abs(revenue) < _ZERO:
            continue
        margins.append(YearlyChartPoint(fiscal_year=year, value=operating_income / revenue))
    return margins
