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
    market: str = "XPAR",
    market_cap: float = 500_000_000.0,
) -> Company:
    company = Company(
        isin=isin,
        ticker=ticker,
        name=name,
        sector=sector,
        market=market,
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
    ev_ebitda: float | None = None,
    pe_ratio: float | None = None,
    fcf_yield: float | None = None,
    revenue_growth: float | None = None,
    ebitda_margin: float | None = None,
    roic: float | None = None,
    roe: float | None = None,
    net_debt_to_ebitda: float | None = None,
) -> None:
    metrics: dict[str, float] = {}
    if total_score is not None:
        metrics["total_score"] = total_score
    if ev_ebitda is not None:
        metrics["ev_ebitda"] = ev_ebitda
    if pe_ratio is not None:
        metrics["pe_ratio"] = pe_ratio
    if fcf_yield is not None:
        metrics["fcf_yield"] = fcf_yield
    if revenue_growth is not None:
        metrics["revenue_growth"] = revenue_growth
    if ebitda_margin is not None:
        metrics["ebitda_margin"] = ebitda_margin
    if roic is not None:
        metrics["roic"] = roic
    if roe is not None:
        metrics["roe"] = roe
    if net_debt_to_ebitda is not None:
        metrics["net_debt_to_ebitda"] = net_debt_to_ebitda
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


def test_peer_selection_uses_sector_market_and_market_cap_bucket(db_session):
    target = _add_company(
        db_session,
        isin="FR0000000001",
        ticker="AAA.PA",
        name="Alpha",
        sector="Tech",
        market="XPAR",
        market_cap=450_000_000.0,
    )
    same_bucket_market = _add_company(
        db_session,
        isin="FR0000000002",
        ticker="BBB.PA",
        name="Beta",
        sector="Tech",
        market="XPAR",
        market_cap=600_000_000.0,
    )
    same_bucket_other_market = _add_company(
        db_session,
        isin="FR0000000003",
        ticker="CCC.PA",
        name="Gamma",
        sector="Tech",
        market="ALXP",
        market_cap=700_000_000.0,
    )
    other_bucket = _add_company(
        db_session,
        isin="FR0000000004",
        ticker="DDD.PA",
        name="Delta",
        sector="Tech",
        market="XPAR",
        market_cap=2_500_000_000.0,
    )
    other_sector = _add_company(
        db_session,
        isin="FR0000000005",
        ticker="EEE.PA",
        name="Epsilon",
        sector="Healthcare",
        market="XPAR",
        market_cap=450_000_000.0,
    )

    _add_snapshot(db_session, target.id, total_score=70.0)
    _add_snapshot(db_session, same_bucket_market.id, total_score=60.0)
    _add_snapshot(db_session, same_bucket_other_market.id, total_score=65.0)
    _add_snapshot(db_session, other_bucket.id, total_score=80.0)
    _add_snapshot(db_session, other_sector.id, total_score=90.0)

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    assert result.sector == "tech"
    assert result.market_cap_bucket == "mid"
    assert result.peer_count == 2
    assert {row.company_id for row in result.peer_rows} == {same_bucket_market.id, same_bucket_other_market.id}
    assert target.id not in {row.company_id for row in result.peer_rows}


def test_metric_median_percentile_and_premium_discount_are_computed(db_session):
    target = _add_company(db_session, isin="FR0000000011", ticker="TGT.PA", name="Target", sector="Tech")
    peer_a = _add_company(db_session, isin="FR0000000012", ticker="PA.PA", name="PeerA", sector="Tech")
    peer_b = _add_company(db_session, isin="FR0000000013", ticker="PB.PA", name="PeerB", sector="Tech")
    peer_c = _add_company(db_session, isin="FR0000000014", ticker="PC.PA", name="PeerC", sector="Tech")

    _add_snapshot(db_session, target.id, total_score=65.0, pe_ratio=18.0, revenue_growth=0.16, roic=0.14)
    _add_snapshot(db_session, peer_a.id, total_score=50.0, pe_ratio=12.0, revenue_growth=0.05, roic=0.08)
    _add_snapshot(db_session, peer_b.id, total_score=70.0, pe_ratio=20.0, revenue_growth=0.12, roic=0.11)
    _add_snapshot(db_session, peer_c.id, total_score=90.0, pe_ratio=22.0, revenue_growth=0.20, roic=0.16)

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    pe_metric = _metric(result, "pe_ratio")
    assert pe_metric.sector_median == 20.0
    assert round(pe_metric.premium_discount_vs_peers or 0.0, 2) == -10.0
    assert round(pe_metric.percentile_rank or 0.0, 2) == round((2 / 3) * 100, 2)

    growth_metric = _metric(result, "revenue_growth")
    assert growth_metric.sector_median == 0.12
    assert growth_metric.percentile_rank is not None
    assert growth_metric.percentile_rank > 0.0


def test_analyst_assessment_exposes_expected_flags(db_session):
    target = _add_company(db_session, isin="FR0000000021", ticker="ANA.PA", name="Analyst", sector="Tech")
    peer_a = _add_company(db_session, isin="FR0000000022", ticker="ANB.PA", name="PeerA", sector="Tech")
    peer_b = _add_company(db_session, isin="FR0000000023", ticker="ANC.PA", name="PeerB", sector="Tech")

    _add_snapshot(
        db_session,
        target.id,
        total_score=72.0,
        ev_ebitda=9.0,
        pe_ratio=13.0,
        revenue_growth=0.18,
        roic=0.14,
        net_debt_to_ebitda=3.2,
    )
    _add_snapshot(
        db_session,
        peer_a.id,
        total_score=60.0,
        ev_ebitda=12.0,
        pe_ratio=16.0,
        revenue_growth=0.09,
        roic=0.09,
        net_debt_to_ebitda=1.8,
    )
    _add_snapshot(
        db_session,
        peer_b.id,
        total_score=65.0,
        ev_ebitda=13.0,
        pe_ratio=17.0,
        revenue_growth=0.11,
        roic=0.10,
        net_debt_to_ebitda=2.0,
    )

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    assert result.analyst_assessment.cheaper_than_peers is True
    assert result.analyst_assessment.higher_quality_than_peers is True
    assert result.analyst_assessment.growth_premium_justified is True
    assert result.analyst_assessment.balance_sheet_weaker is True


def test_low_coverage_does_not_crash_and_returns_partial_metrics(db_session):
    target = _add_company(db_session, isin="FR0000000031", ticker="LOW.PA", name="Low", sector="Utilities")
    peer = _add_company(db_session, isin="FR0000000032", ticker="LOW2.PA", name="Peer", sector="Utilities")

    _add_snapshot(db_session, target.id, total_score=55.0, pe_ratio=15.0)
    _add_snapshot(db_session, peer.id, total_score=50.0)

    result = _make_service(db_session).get_company_peer_comparison(target.id)

    assert result.peer_count == 1
    pe_metric = _metric(result, "pe_ratio")
    assert pe_metric.sector_median is None
    assert pe_metric.percentile_rank is None
    assert result.analyst_assessment.cheaper_than_peers is None
