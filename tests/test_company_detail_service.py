from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.financial_statement import FinancialStatement, PeriodType
from src.models.kpi_snapshot import KpiSnapshot
from src.models.price_history import PriceHistory
from src.services.company_detail_service import CompanyDetailService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _scope(db_session):
    @contextmanager
    def scope():
        yield db_session

    return scope


def _make_service(db_session) -> CompanyDetailService:
    return CompanyDetailService(session_scope_factory=_scope(db_session))


def _add_company(db_session, *, ticker="MC.PA", isin="FR0000131104") -> Company:
    company = Company(
        isin=isin,
        ticker=ticker,
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


def _add_price(db_session, company_id: int, close: float = 720.0) -> PriceHistory:
    price = PriceHistory(
        company_id=company_id,
        date=date(2024, 3, 1),
        open=715.0,
        high=730.0,
        low=710.0,
        close=close,
        adjusted_close=close,
        volume=500_000,
    )
    db_session.add(price)
    db_session.flush()
    return price


def _add_statement(
    db_session,
    company_id: int,
    fiscal_year: int = 2023,
    *,
    revenue=50_000_000_000.0,
    ebitda=10_000_000_000.0,
    ebit=8_000_000_000.0,
    net_income=6_000_000_000.0,
    fcf=5_000_000_000.0,
    net_debt=15_000_000_000.0,
    shares=5_000_000_000.0,
) -> FinancialStatement:
    stmt = FinancialStatement(
        company_id=company_id,
        fiscal_year=fiscal_year,
        period_type=PeriodType.ANNUAL,
        revenue=revenue,
        ebitda=ebitda,
        ebit=ebit,
        net_income=net_income,
        total_assets=100_000_000_000.0,
        total_equity=35_000_000_000.0,
        total_debt=20_000_000_000.0,
        net_debt=net_debt,
        free_cash_flow=fcf,
        shares_outstanding=shares,
    )
    db_session.add(stmt)
    db_session.flush()
    return stmt


def _add_snapshot(db_session, company_id: int, *, metrics: dict | None = None) -> KpiSnapshot:
    default_metrics = {
        "fiscal_year": 2023,
        "price": 720.0,
        "market_cap": 3_600_000_000_000.0,
        "enterprise_value": 3_615_000_000_000.0,
        "pe_ratio": 60.0,
        "pb_ratio": 5.0,
        "ev_ebitda": 361.5,
        "fcf_yield": 0.014,
        "roe": 0.17,
        "roic": 0.12,
        "gross_margin": 0.65,
        "operating_margin": 0.16,
        "revenue_growth": 0.08,
        "ebitda_growth": 0.10,
        "net_debt_to_ebitda": 1.5,
        "data_quality_score": 0.85,
        "total_score": 72.0,
        "quality_score": 80.0,
        "value_score": 45.0,
        "growth_score": 65.0,
        "risk_score": 75.0,
    }
    snap = KpiSnapshot(
        company_id=company_id,
        snapshot_date=date(2024, 3, 1),
        metrics=metrics if metrics is not None else default_metrics,
        source="ratio_service_v1",
    )
    db_session.add(snap)
    db_session.flush()
    return snap


# ---------------------------------------------------------------------------
# Full company — all data present
# ---------------------------------------------------------------------------


def test_full_company(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_statement(db_session, company.id)
    _add_snapshot(db_session, company.id)

    svc = _make_service(db_session)
    detail = svc.get_financial_detail(company.id)

    assert detail is not None
    assert detail.company_id == company.id
    assert detail.ticker == "MC.PA"
    assert detail.current_price == 720.0
    assert detail.fiscal_year == 2023
    assert detail.revenue == 50_000_000_000.0
    assert detail.ebitda == 10_000_000_000.0
    assert detail.net_income == 6_000_000_000.0
    assert detail.free_cash_flow == 5_000_000_000.0
    assert detail.net_debt == 15_000_000_000.0
    assert detail.pe_ratio == 60.0
    assert detail.pb_ratio == 5.0
    assert detail.ev_ebitda == 361.5
    assert detail.roe == 0.17
    assert detail.data_quality_score == 0.85
    assert detail.snapshot_date == date(2024, 3, 1)


def test_ev_sales_computed(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_statement(db_session, company.id, revenue=50_000_000_000.0)
    _add_snapshot(db_session, company.id)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.ev_sales is not None
    assert abs(detail.ev_sales - detail.enterprise_value / 50_000_000_000.0) < 1e-6


def test_net_margin_computed(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_statement(db_session, company.id, net_income=5_000_000_000.0, revenue=50_000_000_000.0)
    _add_snapshot(db_session, company.id)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert abs(detail.net_margin - 0.10) < 1e-6


# ---------------------------------------------------------------------------
# Partial data cases
# ---------------------------------------------------------------------------


def test_no_price(db_session):
    company = _add_company(db_session)
    _add_statement(db_session, company.id)
    _add_snapshot(db_session, company.id)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.current_price is None
    assert detail.revenue == 50_000_000_000.0


def test_no_snapshot(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_statement(db_session, company.id)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.pe_ratio is None
    assert detail.roe is None
    assert detail.data_quality_score is None
    assert detail.snapshot_date is None
    assert detail.revenue == 50_000_000_000.0
    assert detail.current_price == 720.0


def test_no_statement(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_snapshot(db_session, company.id)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.fiscal_year is None
    assert detail.revenue is None
    assert detail.ebitda is None
    assert detail.ev_sales is None
    assert detail.current_price == 720.0


def test_no_data_at_all(db_session):
    company = _add_company(db_session)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.current_price is None
    assert detail.revenue is None
    assert detail.pe_ratio is None
    assert detail.data_quality_score is None


def test_company_not_found(db_session):
    svc = _make_service(db_session)
    detail = svc.get_financial_detail(99999)
    assert detail is None


# ---------------------------------------------------------------------------
# Latest annual statement selection
# ---------------------------------------------------------------------------


def test_picks_latest_annual_statement(db_session):
    company = _add_company(db_session)
    _add_statement(db_session, company.id, fiscal_year=2021, revenue=40_000_000_000.0)
    _add_statement(db_session, company.id, fiscal_year=2023, revenue=50_000_000_000.0)
    _add_statement(db_session, company.id, fiscal_year=2022, revenue=45_000_000_000.0)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.fiscal_year == 2023
    assert detail.revenue == 50_000_000_000.0


# ---------------------------------------------------------------------------
# Graceful None propagation
# ---------------------------------------------------------------------------


def test_ev_sales_none_when_no_revenue(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_statement(db_session, company.id, revenue=None)
    _add_snapshot(db_session, company.id)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.ev_sales is None


def test_net_margin_none_when_no_revenue(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_statement(db_session, company.id, revenue=None)
    _add_snapshot(db_session, company.id)

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.net_margin is None


def test_snapshot_metrics_missing_keys_return_none(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_statement(db_session, company.id)
    _add_snapshot(db_session, company.id, metrics={"total_score": 50.0})

    detail = _make_service(db_session).get_financial_detail(company.id)
    assert detail is not None
    assert detail.pe_ratio is None
    assert detail.roe is None
    assert detail.data_quality_score is None
