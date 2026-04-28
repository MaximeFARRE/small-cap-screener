from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.company_executive import CompanyExecutive
from src.models.company_holder import CompanyHolder
from src.models.company_insider_transaction import CompanyInsiderTransaction
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
    period_type: str | PeriodType = PeriodType.ANNUAL,
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
        period_type=period_type,
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


def _add_executive(
    db_session,
    company_id: int,
    *,
    sort_order: int,
    name: str,
    title: str,
) -> CompanyExecutive:
    executive = CompanyExecutive(
        company_id=company_id,
        sort_order=sort_order,
        name=name,
        title=title,
    )
    db_session.add(executive)
    db_session.flush()
    return executive


def _add_holder(
    db_session,
    company_id: int,
    *,
    sort_order: int,
    holder_type: str,
    holder_name: str,
    weight: float | None,
) -> CompanyHolder:
    holder = CompanyHolder(
        company_id=company_id,
        sort_order=sort_order,
        holder_type=holder_type,
        holder_name=holder_name,
        weight=weight,
    )
    db_session.add(holder)
    db_session.flush()
    return holder


def _add_insider_tx(
    db_session,
    company_id: int,
    *,
    sort_order: int,
    insider_name: str,
    relation: str,
    transaction_text: str,
) -> CompanyInsiderTransaction:
    transaction = CompanyInsiderTransaction(
        company_id=company_id,
        sort_order=sort_order,
        insider_name=insider_name,
        relation=relation,
        transaction_text=transaction_text,
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction


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


def test_ownership_payload_is_exposed_in_company_detail(db_session):
    company = _add_company(db_session)
    _add_executive(
        db_session,
        company.id,
        sort_order=0,
        name="John Leader",
        title="Chief Executive Officer",
    )
    _add_executive(
        db_session,
        company.id,
        sort_order=1,
        name="Jane Finance",
        title="Chief Financial Officer",
    )
    _add_holder(
        db_session,
        company.id,
        sort_order=0,
        holder_type="institutional",
        holder_name="BlackRock",
        weight=0.08,
    )
    _add_holder(
        db_session,
        company.id,
        sort_order=1,
        holder_type="mutual_fund",
        holder_name="Vanguard Fund",
        weight=0.04,
    )
    _add_holder(
        db_session,
        company.id,
        sort_order=2,
        holder_type="major",
        holder_name="% held by institutions",
        weight=0.72,
    )
    _add_insider_tx(
        db_session,
        company.id,
        sort_order=0,
        insider_name="Jane Finance",
        relation="CFO",
        transaction_text="Sale",
    )

    detail = _make_service(db_session).get_financial_detail(company.id)

    assert detail is not None
    assert detail.ceo_name == "John Leader"
    assert detail.cfo_name == "Jane Finance"
    assert len(detail.management_team) == 2
    assert len(detail.major_holders) == 1
    assert len(detail.top_shareholders) == 2
    assert detail.top_shareholders[0].holder_name == "BlackRock"
    assert len(detail.institutional_holders) == 1
    assert len(detail.insider_activity) == 1


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
# Historical fundamentals
# ---------------------------------------------------------------------------


def test_historical_fundamentals_with_complete_annual_history(db_session):
    company = _add_company(db_session)
    _add_price(db_session, company.id)
    _add_snapshot(db_session, company.id)
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2021,
        revenue=100.0,
        ebitda=15.0,
        net_income=8.0,
        fcf=6.0,
        net_debt=30.0,
    )
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2022,
        revenue=120.0,
        ebitda=20.0,
        net_income=10.0,
        fcf=8.0,
        net_debt=25.0,
    )
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2023,
        revenue=144.0,
        ebitda=28.8,
        net_income=12.0,
        fcf=10.0,
        net_debt=20.0,
    )

    detail = _make_service(db_session).get_financial_detail(company.id)

    assert detail is not None
    historical = detail.historical_fundamentals
    assert [point.fiscal_year for point in historical.revenue_history] == [2023, 2022, 2021]
    assert abs((historical.trends.revenue_cagr or 0.0) - 0.2) < 1e-6
    assert historical.trends.revenue_direction == "positive"
    assert historical.trends.margin_direction == "positive"
    assert historical.trends.net_debt_direction == "positive"


def test_historical_fundamentals_fallback_to_non_annual_when_gap_exists(db_session):
    company = _add_company(db_session)
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2023,
        period_type=PeriodType.ANNUAL,
        revenue=300.0,
    )
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2022,
        period_type=PeriodType.HALF_YEAR,
        revenue=200.0,
    )
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2021,
        period_type=PeriodType.ANNUAL,
        revenue=100.0,
    )

    detail = _make_service(db_session).get_financial_detail(company.id)

    assert detail is not None
    history = detail.historical_fundamentals.revenue_history
    assert [point.fiscal_year for point in history] == [2023, 2022, 2021]
    assert history[0].period_type == PeriodType.ANNUAL.value
    assert history[1].period_type == PeriodType.HALF_YEAR.value
    assert history[2].period_type == PeriodType.ANNUAL.value


def test_historical_fundamentals_cagr_none_when_insufficient_periods(db_session):
    company = _add_company(db_session)
    _add_statement(db_session, company.id, fiscal_year=2023, revenue=200.0, ebitda=None, ebit=30.0)
    _add_statement(db_session, company.id, fiscal_year=2022, revenue=100.0, ebitda=None, ebit=15.0)

    detail = _make_service(db_session).get_financial_detail(company.id)

    assert detail is not None
    trends = detail.historical_fundamentals.trends
    assert trends.revenue_cagr is None
    assert trends.operating_income_cagr is None


def test_historical_selection_prioritizes_annual_over_half_year_same_year(db_session):
    company = _add_company(db_session)
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2023,
        period_type=PeriodType.HALF_YEAR,
        revenue=999.0,
    )
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2023,
        period_type=PeriodType.ANNUAL,
        revenue=500.0,
    )
    _add_statement(
        db_session,
        company.id,
        fiscal_year=2022,
        period_type=PeriodType.ANNUAL,
        revenue=400.0,
    )

    detail = _make_service(db_session).get_financial_detail(company.id)

    assert detail is not None
    assert detail.fiscal_year == 2023
    assert detail.revenue == 500.0
    history = detail.historical_fundamentals.revenue_history
    assert len(history) == 2
    assert all(point.period_type == PeriodType.ANNUAL.value for point in history)


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
