from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.repositories import company_repository, kpi_snapshot_repository
from src.services.ratio_service import CompanyRatios
from src.services.screening_service import ScreeningCriteria, ScreeningService, apply_filters


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


def _make_screening_service(db_session) -> ScreeningService:
    @contextmanager
    def session_scope():
        yield db_session

    return ScreeningService(session_scope_factory=session_scope)


def _make_company(
    db_session,
    *,
    isin: str,
    ticker: str,
    name: str,
    sector: str | None,
    market_cap: float = 200_000_000.0,
) -> Company:
    return company_repository.create(
        db_session,
        Company(
            isin=isin,
            ticker=ticker,
            name=name,
            country="France",
            sector=sector,
            currency="EUR",
            is_active=True,
            market_cap=market_cap,
            average_daily_volume=150_000.0,
        ),
    )


def test_list_universe_with_scores_returns_ranked_rows(db_session):
    alpha = _make_company(
        db_session,
        isin="FR0000900001",
        ticker="ALP.PA",
        name="Alpha",
        sector="Energy",
    )
    beta = _make_company(
        db_session,
        isin="FR0000900002",
        ticker="BET.PA",
        name="Beta",
        sector="Tech",
    )
    gamma = _make_company(
        db_session,
        isin="FR0000900003",
        ticker="GAM.PA",
        name="Gamma",
        sector="Energy",
    )
    delta = _make_company(
        db_session,
        isin="FR0000900004",
        ticker="DEL.PA",
        name="Delta",
        sector="Industrial",
    )

    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=alpha.id,
            snapshot_date=date(2024, 10, 31),
            metrics={
                "total_score": 92.0,
                "quality_score": 90.0,
                "value_score": 88.0,
                "growth_score": 85.0,
                "risk_score": 80.0,
            },
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=beta.id,
            snapshot_date=date(2024, 10, 31),
            metrics={
                "total_score": 75.0,
                "quality_score": 70.0,
                "value_score": 72.0,
                "growth_score": 68.0,
                "risk_score": 74.0,
            },
            source="s1",
        ),
    )
    kpi_snapshot_repository.create(
        db_session,
        KpiSnapshot(
            company_id=gamma.id,
            snapshot_date=date(2024, 10, 31),
            metrics={
                "quality_score": 61.0,
                "value_score": 55.0,
                "growth_score": 58.0,
                "risk_score": 60.0,
            },
            source="s1",
        ),
    )

    service = _make_screening_service(db_session)
    rows = service.list_universe_with_scores()
    by_company_id = {row.company_id: row for row in rows}

    assert [row.company_id for row in rows] == [alpha.id, beta.id, gamma.id, delta.id]

    alpha_row = by_company_id[alpha.id]
    assert alpha_row.ticker == "ALP.PA"
    assert alpha_row.name == "Alpha"
    assert alpha_row.sector == "Energy"
    assert alpha_row.total_score == 92.0
    assert alpha_row.quality_score == 90.0
    assert alpha_row.value_score == 88.0
    assert alpha_row.growth_score == 85.0
    assert alpha_row.risk_score == 80.0
    assert alpha_row.rank == 1
    assert alpha_row.sector_rank == 1

    beta_row = by_company_id[beta.id]
    assert beta_row.total_score == 75.0
    assert beta_row.rank == 2
    assert beta_row.sector_rank == 1

    gamma_row = by_company_id[gamma.id]
    assert gamma_row.total_score is None
    assert gamma_row.quality_score == 61.0
    assert gamma_row.value_score == 55.0
    assert gamma_row.growth_score == 58.0
    assert gamma_row.risk_score == 60.0
    assert gamma_row.rank is None
    assert gamma_row.sector_rank is None

    delta_row = by_company_id[delta.id]
    assert delta_row.total_score is None
    assert delta_row.quality_score is None
    assert delta_row.value_score is None
    assert delta_row.growth_score is None
    assert delta_row.risk_score is None
    assert delta_row.rank is None
    assert delta_row.sector_rank is None
