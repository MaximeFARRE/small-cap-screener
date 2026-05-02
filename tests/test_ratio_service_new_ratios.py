import math

import pytest

from src.models.financial_statement import FinancialStatement
from src.services import ratio_service as rs

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stmt(**kwargs) -> FinancialStatement:
    defaults = dict(
        company_id=1,
        fiscal_year=2023,
        revenue=10_000_000.0,
        ebit=1_500_000.0,
        ebitda=2_000_000.0,
        net_income=1_000_000.0,
        gross_profit=4_000_000.0,
        total_assets=20_000_000.0,
        total_equity=8_000_000.0,
        total_debt=3_000_000.0,
        net_debt=2_000_000.0,
        free_cash_flow=900_000.0,
        shares_outstanding=500_000.0,
    )
    return FinancialStatement(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# CAGR 3y
# ---------------------------------------------------------------------------


def test_revenue_cagr_3y_positive_growth():
    result = rs.revenue_cagr_3y(12_000_000.0, 8_000_000.0)
    assert result == pytest.approx((12_000_000.0 / 8_000_000.0) ** (1 / 3) - 1.0)


def test_ebitda_cagr_3y_positive_growth():
    result = rs.ebitda_cagr_3y(2_700_000.0, 2_000_000.0)
    assert result == pytest.approx((2_700_000.0 / 2_000_000.0) ** (1 / 3) - 1.0)


def test_revenue_cagr_3y_flat():
    assert rs.revenue_cagr_3y(10_000_000.0, 10_000_000.0) == pytest.approx(0.0)


def test_revenue_cagr_3y_none_when_missing():
    assert rs.revenue_cagr_3y(None, 8_000_000.0) is None
    assert rs.revenue_cagr_3y(12_000_000.0, None) is None


def test_revenue_cagr_3y_none_when_zero_base():
    assert rs.revenue_cagr_3y(12_000_000.0, 0.0) is None


def test_ebitda_cagr_3y_none_when_negative_base():
    assert rs.ebitda_cagr_3y(2_000_000.0, -500_000.0) is None


def test_revenue_cagr_3y_contraction():
    result = rs.revenue_cagr_3y(7_000_000.0, 10_000_000.0)
    assert result == pytest.approx((7_000_000.0 / 10_000_000.0) ** (1 / 3) - 1.0)
    assert result < 0.0


# ---------------------------------------------------------------------------
# YoY growth ratios
# ---------------------------------------------------------------------------


def test_net_income_growth():
    assert rs.net_income_growth(1_200_000.0, 1_000_000.0) == pytest.approx(0.20)


def test_fcf_growth():
    assert rs.fcf_growth(1_100_000.0, 1_000_000.0) == pytest.approx(0.10)


def test_gross_profit_growth():
    assert rs.gross_profit_growth(4_400_000.0, 4_000_000.0) == pytest.approx(0.10)


def test_net_debt_growth_increase():
    assert rs.net_debt_growth(3_000_000.0, 2_000_000.0) == pytest.approx(0.50)


def test_net_debt_growth_decrease():
    assert rs.net_debt_growth(1_500_000.0, 2_000_000.0) == pytest.approx(-0.25)


def test_net_debt_growth_with_negative_previous():
    # previous net_debt = -1M (net cash), current = 500k: change = 1.5M / 1M = +150%
    assert rs.net_debt_growth(500_000.0, -1_000_000.0) == pytest.approx(1.5)


def test_net_income_growth_none_when_missing():
    assert rs.net_income_growth(None, 1_000_000.0) is None
    assert rs.net_income_growth(1_200_000.0, None) is None


def test_fcf_growth_none_when_zero_previous():
    assert rs.fcf_growth(1_000_000.0, 0.0) is None


def test_gross_profit_growth_none_when_negative_previous():
    assert rs.gross_profit_growth(4_000_000.0, -100_000.0) is None


def test_net_debt_growth_none_when_zero_previous():
    assert rs.net_debt_growth(1_000_000.0, 0.0) is None


# ---------------------------------------------------------------------------
# Value / efficiency ratios
# ---------------------------------------------------------------------------


def test_ps_ratio():
    assert rs.ps_ratio(12_000_000.0, 10_000_000.0) == pytest.approx(1.2)


def test_ps_ratio_none_when_zero_revenue():
    assert rs.ps_ratio(12_000_000.0, 0.0) is None


def test_ps_ratio_none_when_negative_revenue():
    assert rs.ps_ratio(12_000_000.0, -1_000_000.0) is None


def test_ev_sales():
    assert rs.ev_sales(14_000_000.0, 10_000_000.0) == pytest.approx(1.4)


def test_ev_sales_none_when_zero_revenue():
    assert rs.ev_sales(14_000_000.0, 0.0) is None


def test_fcf_margin():
    assert rs.fcf_margin(900_000.0, 10_000_000.0) == pytest.approx(0.09)


def test_fcf_margin_negative_fcf():
    assert rs.fcf_margin(-200_000.0, 10_000_000.0) == pytest.approx(-0.02)


def test_fcf_margin_none_when_zero_revenue():
    assert rs.fcf_margin(900_000.0, 0.0) is None


def test_cash_conversion_ratio():
    assert rs.cash_conversion_ratio(900_000.0, 1_000_000.0) == pytest.approx(0.90)


def test_cash_conversion_ratio_above_one():
    assert rs.cash_conversion_ratio(1_200_000.0, 1_000_000.0) == pytest.approx(1.20)


def test_cash_conversion_ratio_none_when_zero_net_income():
    assert rs.cash_conversion_ratio(900_000.0, 0.0) is None


def test_cash_conversion_ratio_with_negative_net_income():
    result = rs.cash_conversion_ratio(900_000.0, -500_000.0)
    assert result == pytest.approx(-1.8)


def test_asset_turnover():
    assert rs.asset_turnover(10_000_000.0, 20_000_000.0) == pytest.approx(0.5)


def test_asset_turnover_none_when_zero_assets():
    assert rs.asset_turnover(10_000_000.0, 0.0) is None


def test_asset_turnover_none_when_missing():
    assert rs.asset_turnover(None, 20_000_000.0) is None
    assert rs.asset_turnover(10_000_000.0, None) is None


# ---------------------------------------------------------------------------
# compute_all integration
# ---------------------------------------------------------------------------


def test_compute_all_includes_cagr_with_three_year_stmt():
    stmt = _stmt()
    prev = _stmt(revenue=9_000_000.0, ebitda=1_800_000.0)
    stmt_3y = _stmt(revenue=7_000_000.0, ebitda=1_400_000.0)

    ratios = rs.compute_all(1, 2023, 20.0, stmt, prev, stmt_3y)

    assert ratios.revenue_cagr_3y == pytest.approx((10_000_000.0 / 7_000_000.0) ** (1 / 3) - 1.0)
    assert ratios.ebitda_cagr_3y == pytest.approx((2_000_000.0 / 1_400_000.0) ** (1 / 3) - 1.0)


def test_compute_all_cagr_none_without_three_year_stmt():
    stmt = _stmt()
    ratios = rs.compute_all(1, 2023, 20.0, stmt)
    assert ratios.revenue_cagr_3y is None
    assert ratios.ebitda_cagr_3y is None


def test_compute_all_includes_growth_ratios_with_previous_stmt():
    stmt = _stmt()
    prev = _stmt(
        revenue=9_000_000.0,
        net_income=900_000.0,
        free_cash_flow=800_000.0,
        gross_profit=3_600_000.0,
        net_debt=1_600_000.0,
    )

    ratios = rs.compute_all(1, 2023, 20.0, stmt, prev)

    assert ratios.net_income_growth == pytest.approx((1_000_000.0 - 900_000.0) / 900_000.0)
    assert ratios.fcf_growth == pytest.approx((900_000.0 - 800_000.0) / 800_000.0)
    assert ratios.gross_profit_growth == pytest.approx((4_000_000.0 - 3_600_000.0) / 3_600_000.0)
    assert ratios.net_debt_growth == pytest.approx((2_000_000.0 - 1_600_000.0) / 1_600_000.0)


def test_compute_all_growth_none_without_previous_stmt():
    ratios = rs.compute_all(1, 2023, 20.0, _stmt())
    assert ratios.net_income_growth is None
    assert ratios.fcf_growth is None
    assert ratios.gross_profit_growth is None
    assert ratios.net_debt_growth is None


def test_compute_all_includes_value_efficiency_ratios():
    stmt = _stmt()
    ratios = rs.compute_all(1, 2023, 20.0, stmt)

    mkt_cap = 20.0 * 500_000.0  # price * shares = 10_000_000
    assert ratios.ps_ratio == pytest.approx(mkt_cap / 10_000_000.0)
    assert ratios.fcf_margin == pytest.approx(900_000.0 / 10_000_000.0)
    assert ratios.cash_conversion_ratio == pytest.approx(900_000.0 / 1_000_000.0)
    assert ratios.asset_turnover == pytest.approx(10_000_000.0 / 20_000_000.0)
    assert ratios.ev_sales is not None


def test_compute_all_value_efficiency_none_on_missing_data():
    stmt = _stmt(revenue=None, free_cash_flow=None, net_income=None, total_assets=None)
    ratios = rs.compute_all(1, 2023, 20.0, stmt)

    assert ratios.ps_ratio is None
    assert ratios.ev_sales is None
    assert ratios.fcf_margin is None
    assert ratios.cash_conversion_ratio is None
    assert ratios.asset_turnover is None


def test_cagr_3y_result_is_finite():
    result = rs.revenue_cagr_3y(12_000_000.0, 8_000_000.0)
    assert result is not None
    assert math.isfinite(result)
