from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.price_history import PriceHistory
from src.services.company_charts_service import CompanyChartsService, ScoreBreakdownInput
from src.services.company_detail_service import (
    CompanyFinancialDetail,
    HistoricalFundamentals,
    HistoricalFundamentalsTrends,
    HistoricalMetricPoint,
)


def _scope(db_session):
    @contextmanager
    def scope():
        yield db_session

    return scope


def _make_service(db_session) -> CompanyChartsService:
    return CompanyChartsService(session_scope_factory=_scope(db_session))


def _add_company(db_session) -> Company:
    company = Company(
        isin="FR0000131104",
        ticker="MC.PA",
        name="LVMH",
        sector="Consumer Discretionary",
        market="ENX",
        country="France",
        currency="EUR",
        is_active=True,
        market_cap=350_000_000_000.0,
    )
    db_session.add(company)
    db_session.flush()
    return company


def _add_price(db_session, company_id: int, record_date: date, close: float) -> None:
    db_session.add(
        PriceHistory(
            company_id=company_id,
            date=record_date,
            open=close,
            high=close,
            low=close,
            close=close,
            adjusted_close=close,
            volume=100_000,
        )
    )
    db_session.flush()


def _build_financial_detail() -> CompanyFinancialDetail:
    return CompanyFinancialDetail(
        company_id=1,
        ticker="MC.PA",
        name="LVMH",
        sector="Consumer Discretionary",
        currency="EUR",
        current_price=720.0,
        market_cap=350_000_000_000.0,
        enterprise_value=365_000_000_000.0,
        fiscal_year=2023,
        period_type="annual",
        revenue=80_000_000_000.0,
        ebitda=20_000_000_000.0,
        ebit=18_000_000_000.0,
        net_income=12_000_000_000.0,
        free_cash_flow=9_000_000_000.0,
        net_debt=10_000_000_000.0,
        shares_outstanding=2_500_000_000.0,
        pe_ratio=25.0,
        pb_ratio=4.0,
        ev_ebitda=18.0,
        ev_sales=4.6,
        fcf_yield=0.03,
        gross_margin=0.6,
        operating_margin=0.25,
        net_margin=0.15,
        roe=0.18,
        roic=0.12,
        revenue_growth=0.08,
        ebitda_growth=0.1,
        net_debt_to_ebitda=0.5,
        data_quality_score=0.9,
        snapshot_date=date(2024, 3, 1),
        historical_fundamentals=HistoricalFundamentals(
            revenue_history=[
                HistoricalMetricPoint(fiscal_year=2023, period_type="annual", value=300.0),
                HistoricalMetricPoint(fiscal_year=2021, period_type="annual", value=100.0),
                HistoricalMetricPoint(fiscal_year=2022, period_type="annual", value=200.0),
            ],
            operating_income_history=[
                HistoricalMetricPoint(fiscal_year=2023, period_type="annual", value=60.0),
                HistoricalMetricPoint(fiscal_year=2022, period_type="annual", value=30.0),
                HistoricalMetricPoint(fiscal_year=2021, period_type="annual", value=20.0),
            ],
            net_income_history=[],
            free_cash_flow_history=[],
            net_debt_history=[],
            trends=HistoricalFundamentalsTrends(
                revenue_cagr=None,
                operating_income_cagr=None,
                net_income_cagr=None,
                free_cash_flow_cagr=None,
                revenue_direction=None,
                margin_direction=None,
                net_debt_direction=None,
            ),
        ),
    )


def test_prepare_price_history_returns_chronological_limited_points(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id, date(2024, 1, 1), close=100.0)
    _add_price(db_session, company.id, date(2024, 1, 2), close=110.0)
    _add_price(db_session, company.id, date(2024, 1, 3), close=120.0)

    points = _make_service(db_session).prepare_price_history(company.id, max_price_points=2)

    assert [point.point_date for point in points] == [date(2024, 1, 2), date(2024, 1, 3)]
    assert [point.value for point in points] == [110.0, 120.0]


def test_prepare_fundamentals_returns_revenue_operating_income_and_margin(db_session):
    detail = _build_financial_detail()

    fundamentals = _make_service(db_session).prepare_fundamentals(detail)

    assert [point.fiscal_year for point in fundamentals.revenue_points] == [2021, 2022, 2023]
    assert [point.value for point in fundamentals.revenue_points] == [100.0, 200.0, 300.0]
    assert [point.value for point in fundamentals.operating_income_points] == [20.0, 30.0, 60.0]
    assert [round(point.value, 4) for point in fundamentals.margin_points] == [0.2, 0.15, 0.2]


def test_prepare_score_breakdown_preserves_expected_order(db_session):
    breakdown = ScoreBreakdownInput(quality=82.5, value=None, growth=70.0, risk=66.0)

    points = _make_service(db_session).prepare_score_breakdown(breakdown)

    assert [point.key for point in points] == ["quality", "growth", "risk"]
    assert [point.score for point in points] == [82.5, 70.0, 66.0]


def test_build_company_charts_data_handles_missing_data(db_session):
    service = _make_service(db_session)

    chart_data = service.build_company_charts_data(
        9999,
        financial_detail=None,
        score_breakdown=None,
    )

    assert chart_data.price_points == []
    assert chart_data.fundamentals.revenue_points == []
    assert chart_data.fundamentals.operating_income_points == []
    assert chart_data.fundamentals.margin_points == []
    assert chart_data.score_breakdown == []
