from src.services.ratio_service import CompanyRatios
from src.services.screening_service import ScreeningCriteria, apply_filters


def _make_ratios(company_id: int, **kwargs) -> CompanyRatios:
    defaults = dict(
        fiscal_year=2023,
        price=20.0,
        mkt_cap=10_000_000.0,
        ev=12_000_000.0,
        pe_ratio=12.0,
        pb_ratio=1.2,
        ev_ebitda=7.0,
        roe=0.12,
        net_margin=0.08,
        ebit_margin=0.10,
        debt_to_equity=0.4,
        net_debt_to_ebitda=1.5,
    )
    return CompanyRatios(company_id=company_id, **{**defaults, **kwargs})


def test_no_criteria_returns_all_sorted_by_score():
    candidates = [_make_ratios(1), _make_ratios(2), _make_ratios(3)]
    results = apply_filters(candidates, ScreeningCriteria())
    assert len(results) == 3


def test_results_sorted_by_score_descending():
    cheap = _make_ratios(1, pe_ratio=8.0, roe=0.20)
    expensive = _make_ratios(2, pe_ratio=22.0, roe=0.03)
    results = apply_filters([expensive, cheap], ScreeningCriteria())
    assert results[0].ratios.company_id == 1


def test_max_pe_filter_excludes_above_threshold():
    results = apply_filters(
        [_make_ratios(1, pe_ratio=10.0), _make_ratios(2, pe_ratio=20.0)],
        ScreeningCriteria(max_pe=15.0),
    )
    assert len(results) == 1
    assert results[0].ratios.company_id == 1


def test_min_roe_filter_excludes_below_threshold():
    results = apply_filters(
        [_make_ratios(1, roe=0.20), _make_ratios(2, roe=0.05)],
        ScreeningCriteria(min_roe=0.10),
    )
    assert len(results) == 1
    assert results[0].ratios.company_id == 1


def test_multiple_criteria_applied_together():
    results = apply_filters(
        [
            _make_ratios(1, pe_ratio=10.0, roe=0.18, net_debt_to_ebitda=1.0),
            _make_ratios(2, pe_ratio=10.0, roe=0.18, net_debt_to_ebitda=5.0),
        ],
        ScreeningCriteria(max_pe=15.0, min_roe=0.10, max_net_debt_to_ebitda=3.0),
    )
    assert len(results) == 1
    assert results[0].ratios.company_id == 1


def test_none_ratio_value_is_not_filtered_out():
    results = apply_filters(
        [_make_ratios(1, pe_ratio=None)],
        ScreeningCriteria(max_pe=15.0),
    )
    assert len(results) == 1


def test_empty_candidates_returns_empty():
    assert apply_filters([], ScreeningCriteria(max_pe=15.0)) == []


def test_result_contains_score():
    results = apply_filters([_make_ratios(1)], ScreeningCriteria())
    assert 0.0 <= results[0].score <= 100.0
