import pytest

from src.services import scoring_service as ss
from src.services.ratio_service import CompanyRatios


def _make_ratios(**kwargs) -> CompanyRatios:
    defaults = dict(
        company_id=1,
        fiscal_year=2023,
        price=20.0,
        mkt_cap=10_000_000.0,
        ev=12_000_000.0,
        pe_ratio=10.0,
        ev_ebitda=6.0,
        pb_ratio=1.0,
        price_to_fcf=10.0,
        roe=0.15,
        net_margin=0.10,
        ebit_margin=0.10,
        net_debt_to_ebitda=1.0,
    )
    return CompanyRatios(**{**defaults, **kwargs})


def test_perfect_score_is_100():
    ratios = _make_ratios()
    assert ss.compute_score(ratios) == pytest.approx(100.0)


def test_worst_score_is_0():
    ratios = _make_ratios(
        pe_ratio=25.0,
        ev_ebitda=15.0,
        pb_ratio=3.0,
        price_to_fcf=25.0,
        roe=0.0,
        net_margin=0.0,
        ebit_margin=0.0,
        net_debt_to_ebitda=4.0,
    )
    assert ss.compute_score(ratios) == pytest.approx(0.0)


def test_score_is_between_0_and_100():
    ratios = _make_ratios(pe_ratio=17.5, ev_ebitda=10.5, roe=0.075)
    score = ss.compute_score(ratios)
    assert 0.0 <= score <= 100.0


def test_missing_metrics_do_not_crash():
    ratios = _make_ratios(pe_ratio=None, ev_ebitda=None, pb_ratio=None)
    score = ss.compute_score(ratios)
    assert 0.0 <= score <= 100.0


def test_all_metrics_none_returns_zero():
    ratios = CompanyRatios(
        company_id=1, fiscal_year=2023, price=1.0, mkt_cap=0.0, ev=0.0
    )
    assert ss.compute_score(ratios) == pytest.approx(0.0)


def test_better_ratios_yield_higher_score():
    cheap = _make_ratios(pe_ratio=8.0, roe=0.20)
    expensive = _make_ratios(pe_ratio=22.0, roe=0.05)
    assert ss.compute_score(cheap) > ss.compute_score(expensive)


def test_high_leverage_lowers_score():
    low_debt = _make_ratios(net_debt_to_ebitda=0.5)
    high_debt = _make_ratios(net_debt_to_ebitda=3.5)
    assert ss.compute_score(low_debt) > ss.compute_score(high_debt)
