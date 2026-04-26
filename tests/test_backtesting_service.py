from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.models.price_history import PriceHistory
from src.services.backtesting_service import BacktestingService, _compute_forward_return


def _scope(db_session):
    @contextmanager
    def scope():
        yield db_session

    return scope


def _make_service(db_session) -> BacktestingService:
    return BacktestingService(session_scope_factory=_scope(db_session))


def _add_company(db_session, *, index: int) -> Company:
    company = Company(
        isin=f"FR000000{index:04d}",
        ticker=f"T{index:03d}.PA",
        name=f"Company {index}",
        sector="Tech",
        market="ENX",
        country="France",
        currency="EUR",
        is_active=True,
        market_cap=500_000_000.0,
    )
    db_session.add(company)
    db_session.flush()
    return company


def _add_snapshot(db_session, company_id: int, *, snapshot_date: date, total_score: float) -> None:
    db_session.add(
        KpiSnapshot(
            company_id=company_id,
            snapshot_date=snapshot_date,
            metrics={
                "total_score": total_score,
                "quality_score": total_score,
                "value_score": total_score,
                "growth_score": total_score,
                "risk_score": total_score,
            },
            source="test",
        )
    )
    db_session.flush()


def _add_price(db_session, company_id: int, *, record_date: date, close: float) -> None:
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


def test_bucket_assignment_uses_top_middle_bottom_percentages(db_session):
    snapshot_date = date(2024, 1, 1)
    returns = [0.20, 0.18, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, -0.08, -0.10]
    companies = [_add_company(db_session, index=index) for index in range(10)]
    for index, company in enumerate(companies):
        _add_snapshot(db_session, company.id, snapshot_date=snapshot_date, total_score=100.0 - index)
        _add_price(db_session, company.id, record_date=date(2024, 1, 2), close=100.0)
        _add_price(db_session, company.id, record_date=date(2024, 4, 2), close=100.0 * (1.0 + returns[index]))

    analysis = _make_service(db_session).analyze_ranking_validation(forward_days=90, max_snapshots=1)
    result = analysis.snapshot_results[0]

    assert result.top_bucket.company_count == 2
    assert result.middle_bucket.company_count == 6
    assert result.bottom_bucket.company_count == 2
    assert result.top_bucket.average_return is not None and result.top_bucket.average_return > 0.18
    assert result.bottom_bucket.average_return is not None and result.bottom_bucket.average_return < 0.0


def test_forward_return_uses_first_prices_on_or_after_dates():
    prices = [
        PriceHistory(
            company_id=1, date=date(2024, 1, 2), open=100, high=100, low=100, close=100, adjusted_close=100, volume=1
        ),
        PriceHistory(
            company_id=1, date=date(2024, 1, 3), open=101, high=101, low=101, close=101, adjusted_close=101, volume=1
        ),
        PriceHistory(
            company_id=1, date=date(2024, 2, 5), open=112, high=112, low=112, close=112, adjusted_close=112, volume=1
        ),
    ]

    value = _compute_forward_return(
        prices_desc=prices,
        snapshot_date=date(2024, 1, 1),
        forward_days=30,
    )

    assert value is not None
    assert abs(value - 0.12) < 1e-9


def test_benchmark_comparison_uses_universe_equal_weight_proxy(db_session):
    snapshot_date = date(2024, 1, 1)
    returns = [0.20, 0.10, 0.05, 0.00, -0.10]
    companies = [_add_company(db_session, index=100 + index) for index in range(5)]
    for index, company in enumerate(companies):
        _add_snapshot(db_session, company.id, snapshot_date=snapshot_date, total_score=100.0 - index)
        _add_price(db_session, company.id, record_date=date(2024, 1, 2), close=100.0)
        _add_price(db_session, company.id, record_date=date(2024, 4, 2), close=100.0 * (1.0 + returns[index]))

    analysis = _make_service(db_session).analyze_ranking_validation(forward_days=90, max_snapshots=1)
    result = analysis.snapshot_results[0]

    assert analysis.benchmark_name == "universe_equal_weight_proxy"
    assert result.benchmark_return is not None
    assert abs(result.benchmark_return - 0.05) < 1e-9
    assert analysis.top_excess_vs_benchmark is not None
    assert abs(analysis.top_excess_vs_benchmark - 0.15) < 1e-9


def test_incomplete_data_is_handled_without_crash(db_session):
    snapshot_date = date(2024, 1, 1)
    companies = [_add_company(db_session, index=200 + index) for index in range(5)]
    for index, company in enumerate(companies):
        _add_snapshot(db_session, company.id, snapshot_date=snapshot_date, total_score=100.0 - index)
        _add_price(db_session, company.id, record_date=date(2024, 1, 2), close=100.0)

    _add_price(db_session, companies[0].id, record_date=date(2024, 4, 2), close=110.0)
    _add_price(db_session, companies[1].id, record_date=date(2024, 4, 2), close=105.0)

    analysis = _make_service(db_session).analyze_ranking_validation(forward_days=90, max_snapshots=1)
    result = analysis.snapshot_results[0]

    assert result.valid_forward_returns == 2
    assert result.bottom_bucket.average_return is None
    assert result.top_minus_bottom is None
    assert analysis.evaluated_snapshots == 0
    assert analysis.score_validation == "insufficient_data"
