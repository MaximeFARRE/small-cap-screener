from src.models.financial_statement import FinancialStatement
from src.services.ratio_service import RatioService


def _make_stmt(**kwargs) -> FinancialStatement:
    defaults = dict(
        company_id=1,
        fiscal_year=2023,
        revenue=10_000_000.0,
        ebit=1_500_000.0,
        ebitda=2_000_000.0,
        net_income=1_000_000.0,
        total_assets=20_000_000.0,
        total_equity=8_000_000.0,
        total_debt=3_000_000.0,
        net_debt=2_000_000.0,
        free_cash_flow=900_000.0,
        shares_outstanding=500_000.0,
    )
    return FinancialStatement(**{**defaults, **kwargs})


def test_ratio_service_compute_all_v1_fields():
    service = RatioService()
    stmt = _make_stmt()
    prev = _make_stmt(revenue=9_500_000.0, ebitda=1_800_000.0)

    ratios = service.compute_all(
        company_id=1,
        fiscal_year=2023,
        price=20.0,
        stmt=stmt,
        previous_stmt=prev,
        gross_profit=4_200_000.0,
        current_assets=6_000_000.0,
        current_liabilities=3_000_000.0,
        interest_expense=600_000.0,
    )

    assert ratios.pe_ratio is not None
    assert ratios.ev_ebitda is not None
    assert ratios.ev_ebit is not None
    assert ratios.pb_ratio is not None
    assert ratios.fcf_yield is not None
    assert ratios.roe is not None
    assert ratios.roic is not None
    assert ratios.roce is not None
    assert ratios.gross_margin is not None
    assert ratios.operating_margin is not None
    assert ratios.revenue_growth is not None
    assert ratios.ebitda_growth is not None
    assert ratios.net_debt_to_ebitda is not None
    assert ratios.current_ratio is not None
    assert ratios.interest_coverage is not None


def test_ratio_service_handles_missing_values():
    service = RatioService()
    stmt = _make_stmt(net_income=None, ebit=None, ebitda=None, free_cash_flow=None)

    ratios = service.compute_all(
        company_id=1,
        fiscal_year=2023,
        price=20.0,
        stmt=stmt,
        previous_stmt=None,
        gross_profit=None,
        current_assets=None,
        current_liabilities=None,
        interest_expense=None,
    )

    assert ratios.pe_ratio is None
    assert ratios.ev_ebitda is None
    assert ratios.ev_ebit is None
    assert ratios.fcf_yield is None
    assert ratios.roe is None
    assert ratios.roic is None
    assert ratios.roce is None
    assert ratios.gross_margin is None
    assert ratios.revenue_growth is None
    assert ratios.ebitda_growth is None
    assert ratios.current_ratio is None
    assert ratios.interest_coverage is None


def test_ratio_service_prevents_division_by_zero():
    service = RatioService()

    assert service.current_ratio(1_000_000.0, 0.0) is None
    assert service.interest_coverage(1_000_000.0, 0.0) is None
    assert service.roe(1_000_000.0, 0.0) is None
    assert service.fcf_yield(1_000_000.0, 0.0) is None
