import pytest

from src.models.financial_statement import FinancialStatement
from src.services import ratio_service as rs

# --- helpers ---


def test_market_cap():
    assert rs.market_cap(10.0, 1_000_000) == pytest.approx(10_000_000.0)


def test_enterprise_value():
    assert rs.enterprise_value(10_000_000.0, 2_000_000.0) == pytest.approx(12_000_000.0)


def test_enterprise_value_negative_net_debt():
    assert rs.enterprise_value(10_000_000.0, -1_000_000.0) == pytest.approx(9_000_000.0)


# --- valuation ---


def test_pe_ratio():
    assert rs.pe_ratio(20.0, 1_000_000.0, 500_000.0) == pytest.approx(10.0)


def test_pe_ratio_none_when_zero_eps():
    assert rs.pe_ratio(20.0, 0.0, 500_000.0) is None


def test_pe_ratio_none_when_missing_data():
    assert rs.pe_ratio(20.0, None, 500_000.0) is None
    assert rs.pe_ratio(20.0, 1_000_000.0, None) is None


def test_pb_ratio():
    assert rs.pb_ratio(12_000_000.0, 8_000_000.0) == pytest.approx(1.5)


def test_pb_ratio_none_when_zero_equity():
    assert rs.pb_ratio(12_000_000.0, 0.0) is None


def test_ev_ebitda():
    assert rs.ev_ebitda(12_000_000.0, 2_000_000.0) == pytest.approx(6.0)


def test_ev_ebitda_none_when_zero():
    assert rs.ev_ebitda(12_000_000.0, 0.0) is None


def test_ev_ebit():
    assert rs.ev_ebit(12_000_000.0, 1_500_000.0) == pytest.approx(8.0)


def test_price_to_fcf():
    assert rs.price_to_fcf(10_000_000.0, 1_000_000.0) == pytest.approx(10.0)


def test_price_to_fcf_none_when_negative_fcf():
    # negative FCF → not meaningful, should still compute (not None)
    result = rs.price_to_fcf(10_000_000.0, -500_000.0)
    assert result == pytest.approx(-20.0)


def test_fcf_yield():
    assert rs.fcf_yield(1_000_000.0, 10_000_000.0) == pytest.approx(0.10)


def test_fcf_yield_none_when_zero_market_cap():
    assert rs.fcf_yield(1_000_000.0, 0.0) is None


# --- profitability ---


def test_roe():
    assert rs.roe(1_000_000.0, 5_000_000.0) == pytest.approx(0.20)


def test_roe_none_when_zero_equity():
    assert rs.roe(1_000_000.0, 0.0) is None


def test_roa():
    assert rs.roa(1_000_000.0, 10_000_000.0) == pytest.approx(0.10)


def test_ebit_margin():
    assert rs.ebit_margin(1_500_000.0, 10_000_000.0) == pytest.approx(0.15)


def test_ebitda_margin():
    assert rs.ebitda_margin(2_000_000.0, 10_000_000.0) == pytest.approx(0.20)


def test_net_margin():
    assert rs.net_margin(800_000.0, 10_000_000.0) == pytest.approx(0.08)


def test_net_margin_none_when_zero_revenue():
    assert rs.net_margin(800_000.0, 0.0) is None


def test_roic_with_explicit_invested_capital():
    result = rs.roic(
        ebit=2_000_000.0,
        invested_capital=10_000_000.0,
        total_equity=None,
        net_debt=None,
        total_debt=None,
        tax_rate=0.25,
    )
    assert result == pytest.approx(0.15)


def test_roce():
    assert rs.roce(2_000_000.0, 20_000_000.0, 5_000_000.0) == pytest.approx(2_000_000.0 / 15_000_000.0)


def test_gross_margin():
    assert rs.gross_margin(4_000_000.0, 10_000_000.0) == pytest.approx(0.40)


def test_operating_margin():
    assert rs.operating_margin(1_500_000.0, 10_000_000.0) == pytest.approx(0.15)


# --- leverage ---


def test_debt_to_equity():
    assert rs.debt_to_equity(3_000_000.0, 6_000_000.0) == pytest.approx(0.5)


def test_net_debt_to_ebitda():
    assert rs.net_debt_to_ebitda(4_000_000.0, 2_000_000.0) == pytest.approx(2.0)


def test_net_debt_to_ebitda_none_when_zero_ebitda():
    assert rs.net_debt_to_ebitda(4_000_000.0, 0.0) is None


def test_current_ratio():
    assert rs.current_ratio(6_000_000.0, 3_000_000.0) == pytest.approx(2.0)


def test_interest_coverage():
    assert rs.interest_coverage(2_000_000.0, 500_000.0) == pytest.approx(4.0)


# --- growth ---


def test_revenue_growth():
    assert rs.revenue_growth(12_000_000.0, 10_000_000.0) == pytest.approx(0.20)


def test_ebitda_growth():
    assert rs.ebitda_growth(2_400_000.0, 2_000_000.0) == pytest.approx(0.20)


def test_growth_none_when_previous_zero():
    assert rs.revenue_growth(12_000_000.0, 0.0) is None
    assert rs.ebitda_growth(2_400_000.0, 0.0) is None


# --- incoherent data ---


def test_roic_none_when_non_positive_invested_capital():
    result = rs.roic(
        ebit=2_000_000.0,
        invested_capital=-1_000_000.0,
        total_equity=None,
        net_debt=None,
        total_debt=None,
    )
    assert result is None


def test_current_ratio_none_when_non_positive_liabilities():
    assert rs.current_ratio(1_000_000.0, 0.0) is None
    assert rs.current_ratio(1_000_000.0, -100_000.0) is None


def test_interest_coverage_none_when_non_positive_interest_expense():
    assert rs.interest_coverage(1_000_000.0, 0.0) is None
    assert rs.interest_coverage(1_000_000.0, -50_000.0) is None


# --- compute_all ---


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


def test_compute_all_returns_complete_ratios():
    stmt = _make_stmt()
    ratios = rs.compute_all(1, 2023, 20.0, stmt)
    assert ratios.company_id == 1
    assert ratios.mkt_cap == pytest.approx(10_000_000.0)
    assert ratios.pe_ratio == pytest.approx(10.0)
    assert ratios.roe == pytest.approx(0.125)
    assert ratios.net_margin == pytest.approx(0.10)
    assert ratios.ev_ebitda is not None


def test_compute_all_handles_missing_fields():
    stmt = _make_stmt(net_income=None, ebitda=None)
    ratios = rs.compute_all(1, 2023, 20.0, stmt)
    assert ratios.pe_ratio is None
    assert ratios.ev_ebitda is None
    assert ratios.roe is None
    assert ratios.net_margin is None


def test_compute_all_includes_new_v1_ratios():
    stmt = _make_stmt()
    prev_stmt = _make_stmt(revenue=9_000_000.0, ebitda=1_800_000.0)
    ratios = rs.compute_all(
        1,
        2023,
        20.0,
        stmt,
        previous_stmt=prev_stmt,
        gross_profit=4_500_000.0,
        current_assets=6_000_000.0,
        current_liabilities=3_000_000.0,
        interest_expense=500_000.0,
        invested_capital=10_000_000.0,
    )
    assert ratios.fcf_yield == pytest.approx(0.09)
    assert ratios.roic is not None
    assert ratios.roce is not None
    assert ratios.gross_margin == pytest.approx(0.45)
    assert ratios.operating_margin == pytest.approx(0.15)
    assert ratios.revenue_growth == pytest.approx((10_000_000.0 - 9_000_000.0) / 9_000_000.0)
    assert ratios.ebitda_growth == pytest.approx((2_000_000.0 - 1_800_000.0) / 1_800_000.0)
    assert ratios.current_ratio == pytest.approx(2.0)
    assert ratios.interest_coverage == pytest.approx(3.0)


def test_compute_all_handles_incoherent_inputs():
    stmt = _make_stmt()
    ratios = rs.compute_all(
        1,
        2023,
        20.0,
        stmt,
        gross_profit=4_500_000.0,
        current_assets=6_000_000.0,
        current_liabilities=-1.0,
        interest_expense=-10.0,
        invested_capital=-1.0,
    )
    assert ratios.roic is None
    assert ratios.current_ratio is None
    assert ratios.interest_coverage is None
