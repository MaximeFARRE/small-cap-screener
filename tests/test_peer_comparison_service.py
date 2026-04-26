from __future__ import annotations

from contextlib import contextmanager
from datetime import date

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.services.peer_comparison_service import PeerComparisonService


def _scope(db_session):
    @contextmanager
    def scope():
        yield db_session

    return scope


def _make_service(db_session) -> PeerComparisonService:
    return PeerComparisonService(session_scope_factory=_scope(db_session))


def _add_company(
    db_session,
    *,
    isin: str,
    ticker: str,
    name: str,
    sector: str | None,
    market_cap: float = 500_000_000.0,
) -> Company:
    company = Company(
        isin=isin,
        ticker=ticker,
        name=name,
        sector=sector,
        market="ENX",
        country="France",
        currency="EUR",
        is_active=True,
        market_cap=market_cap,
    )
    db_session.add(company)
    db_session.flush()
    return company


def _add_snapshot(
    db_session,
    company_id: int,
    *,
    total_score: float | None,
    quality_score: float | None = None,
    value_score: float | None = None,
    growth_score: float | None = None,
    risk_score: float | None = None,
    ev_ebitda: float | None = None,
    pe_ratio: float | None = None,
    gross_margin: float | None = None,
    operating_margin: float | None = None,
    revenue_growth: float | None = None,
    ebitda_growth: float | None = None,
    data_quality_score: float | None = None,
) -> None:
    metrics: dict[str, float] = {}
    if total_score is not None:
        metrics["total_score"] = total_score
    if quality_score is not None:
        metrics["quality_score"] = quality_score
    if value_score is not None:
        metrics["value_score"] = value_score
    if growth_score is not None:
        metrics["growth_score"] = growth_score
    if risk_score is not None:
        metrics["risk_score"] = risk_score
    if ev_ebitda is not None:
        metrics["ev_ebitda"] = ev_ebitda
    if pe_ratio is not None:
        metrics["pe_ratio"] = pe_ratio
    if gross_margin is not None:
        metrics["gross_margin"] = gross_margin
    if operating_margin is not None:
        metrics["operating_margin"] = operating_margin
    if revenue_growth is not None:
        metrics["revenue_growth"] = revenue_growth
    if ebitda_growth is not None:
        metrics["ebitda_growth"] = ebitda_growth
    if data_quality_score is not None:
        metrics["data_quality_score"] = data_quality_score
    db_session.add(
        KpiSnapshot(
            company_id=company_id,
            snapshot_date=date(2026, 4, 26),
            metrics=metrics,
            source="test",
        )
    )
    db_session.flush()


def _metric(result, key: str):
    return next(metric for metric in result.metrics if metric.key == key)


def test_peer_selection_excludes_company_itself_and_other_sectors(db_session):
    target = _add_company(db_session, isin="FR0000000001", ticker="AAA.PA", name="Alpha", sector="Tech")
    peer_a = _add_company(db_session, isin="FR0000000002", ticker="BBB.PA", name="Beta", sector="Tech")
    peer_b = _add_company(db_session, isin="FR0000000003", ticker="CCC.PA", name="Gamma", sector="Tech")
    outsider = _add_company(db_session, isin="FR0000000004", ticker="DDD.PA", name="Delta", sector="Healthcare")

    _add_snapshot(db_session, target.id, total_score=70.0, quality_score=72.0)
    _add_snapshot(db_session, peer_a.id, total_score=60.0, quality_score=62.0)
    _add_snapshot(db_session, peer_b.id, total_score=80.0, quality_score=82.0)
    _add_snapshot(db_session, outsider.id, total_score=90.0, quality_score=92.0)

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    assert result.sector == "Tech"
    assert result.sector_company_count == 3
    assert result.sector_scored_count == 3
    assert result.company_sector_rank == 2
    assert result.peer_count == 2
    assert {row.company_id for row in result.peer_rows} == {peer_a.id, peer_b.id}
    assert target.id not in {row.company_id for row in result.peer_rows}
    assert outsider.id not in {row.company_id for row in result.peer_rows}


def test_sector_medians_and_relative_positions_are_computed(db_session):
    target = _add_company(db_session, isin="FR0000000011", ticker="TGT.PA", name="Target", sector="Tech")
    peer_a = _add_company(db_session, isin="FR0000000012", ticker="PA.PA", name="PeerA", sector="Tech")
    peer_b = _add_company(db_session, isin="FR0000000013", ticker="PB.PA", name="PeerB", sector="Tech")
    peer_c = _add_company(db_session, isin="FR0000000014", ticker="PC.PA", name="PeerC", sector="Tech")

    _add_snapshot(db_session, target.id, total_score=65.0, ev_ebitda=16.0, pe_ratio=18.0, operating_margin=0.11)
    _add_snapshot(db_session, peer_a.id, total_score=50.0, ev_ebitda=10.0, pe_ratio=12.0, operating_margin=0.08)
    _add_snapshot(db_session, peer_b.id, total_score=70.0, ev_ebitda=14.0, pe_ratio=20.0, operating_margin=0.12)
    _add_snapshot(db_session, peer_c.id, total_score=90.0, ev_ebitda=18.0, pe_ratio=22.0, operating_margin=0.14)

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    total_score_metric = _metric(result, "total_score")
    assert total_score_metric.company_value == 65.0
    assert total_score_metric.sector_median == 70.0
    assert total_score_metric.position == "en dessous"

    ev_ebitda_metric = _metric(result, "ev_ebitda")
    assert ev_ebitda_metric.company_value == 16.0
    assert ev_ebitda_metric.sector_median == 14.0
    assert ev_ebitda_metric.position == "au-dessus"

    pe_ratio_metric = _metric(result, "pe_ratio")
    assert pe_ratio_metric.company_value == 18.0
    assert pe_ratio_metric.sector_median == 20.0
    assert pe_ratio_metric.position == "en dessous"


def test_medians_ignore_missing_peer_values(db_session):
    target = _add_company(db_session, isin="FR0000000021", ticker="MTA.PA", name="Target", sector="Tech")
    peer_a = _add_company(db_session, isin="FR0000000022", ticker="MTB.PA", name="PeerA", sector="Tech")
    peer_b = _add_company(db_session, isin="FR0000000023", ticker="MTC.PA", name="PeerB", sector="Tech")

    _add_snapshot(db_session, target.id, total_score=55.0, pe_ratio=15.0)
    _add_snapshot(db_session, peer_a.id, total_score=50.0, pe_ratio=None, ev_ebitda=None)
    _add_snapshot(db_session, peer_b.id, total_score=60.0, pe_ratio=11.0, ev_ebitda=None)

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    pe_ratio_metric = _metric(result, "pe_ratio")
    assert pe_ratio_metric.sector_median == 11.0
    assert pe_ratio_metric.position == "au-dessus"

    ev_ebitda_metric = _metric(result, "ev_ebitda")
    assert ev_ebitda_metric.sector_median is None
    assert ev_ebitda_metric.position is None


def test_empty_sector_panel_returns_no_peers(db_session):
    target = _add_company(db_session, isin="FR0000000031", ticker="UNI.PA", name="Unique", sector="Utilities")
    _add_snapshot(db_session, target.id, total_score=58.0, quality_score=61.0)

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    assert result.sector == "Utilities"
    assert result.sector_company_count == 1
    assert result.peer_count == 0
    assert result.peer_rows == []
    assert all(metric.sector_median is None for metric in result.metrics)
