from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock

from src.models.company import SOURCE_MANUAL, SOURCE_SEED, Company
from src.services.financial_data_service import CompanyDataRefreshResult
from src.services.kpi_snapshot_service import KpiSnapshotServiceResult
from src.services.universe_discovery_service import (
    UniverseDiscoveryService,
    UniverseRefreshResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_scope(db_session):
    @contextmanager
    def scope():
        yield db_session

    return scope


def _add_company(session, *, ticker: str, source: str | None = None) -> Company:
    company = Company(
        isin=f"ISIN{ticker}",
        ticker=ticker,
        name=f"{ticker} Corp",
        currency="EUR",
        is_active=True,
        source_origin=source,
    )
    session.add(company)
    session.flush()
    return company


def _make_data_result(company_id: int, ticker: str, *, success: bool = True) -> CompanyDataRefreshResult:
    return CompanyDataRefreshResult(
        company_id=company_id,
        ticker=ticker,
        success=success,
        prices_added=5 if success else 0,
        statements_added=2 if success else 0,
        error=None if success else "fetch error",
        stage=None if success else "fetch",
    )


def _make_kpi_result(company_id: int, *, success: bool = True) -> KpiSnapshotServiceResult:
    return KpiSnapshotServiceResult(
        company_id=company_id,
        snapshot_date=date.today(),
        success=success,
        snapshot_id=99 if success else None,
        error=None if success else "no data",
    )


def _make_service(db_session, *, data_result=None, kpi_result=None) -> UniverseDiscoveryService:
    fin_svc = MagicMock()
    kpi_svc = MagicMock()
    if data_result is not None:
        fin_svc.refresh_company_data.return_value = data_result
    if kpi_result is not None:
        kpi_svc.compute_and_upsert_for_company.return_value = kpi_result
    return UniverseDiscoveryService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=kpi_svc,
        session_scope_factory=_make_session_scope(db_session),
    )


# ---------------------------------------------------------------------------
# refresh_company — success path
# ---------------------------------------------------------------------------


def test_refresh_company_success(db_session):
    company = _add_company(db_session, ticker="MC.PA")
    svc = _make_service(
        db_session,
        data_result=_make_data_result(company.id, "MC.PA"),
        kpi_result=_make_kpi_result(company.id),
    )
    result = svc.refresh_company(company.id)

    assert result.success
    assert result.ticker == "MC.PA"
    assert result.prices_added == 5
    assert result.statements_added == 2
    assert result.kpi_snapshot_id == 99
    assert result.error is None


def test_refresh_company_stamps_last_refresh_at(db_session):
    company = _add_company(db_session, ticker="MC.PA")
    assert company.last_universe_refresh_at is None

    svc = _make_service(
        db_session,
        data_result=_make_data_result(company.id, "MC.PA"),
        kpi_result=_make_kpi_result(company.id),
    )
    svc.refresh_company(company.id)

    db_session.refresh(company)
    assert company.last_universe_refresh_at is not None


# ---------------------------------------------------------------------------
# refresh_company — data failure propagates
# ---------------------------------------------------------------------------


def test_refresh_company_data_failure(db_session):
    company = _add_company(db_session, ticker="MC.PA")
    svc = _make_service(
        db_session,
        data_result=_make_data_result(company.id, "MC.PA", success=False),
        kpi_result=_make_kpi_result(company.id),
    )
    result = svc.refresh_company(company.id)

    assert not result.success
    assert result.stage == "fetch"
    assert result.error == "fetch error"
    svc.kpi_snapshot_service.compute_and_upsert_for_company.assert_not_called()


# ---------------------------------------------------------------------------
# refresh_company — kpi failure is a warning, not a failure
# ---------------------------------------------------------------------------


def test_refresh_company_kpi_failure_still_succeeds(db_session):
    company = _add_company(db_session, ticker="MC.PA")
    svc = _make_service(
        db_session,
        data_result=_make_data_result(company.id, "MC.PA"),
        kpi_result=_make_kpi_result(company.id, success=False),
    )
    result = svc.refresh_company(company.id)

    assert result.success
    assert result.kpi_snapshot_id is None
    assert any("KPI" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# batch_refresh_universe
# ---------------------------------------------------------------------------


def test_batch_refresh_universe_returns_correct_counts(db_session):
    c1 = _add_company(db_session, ticker="MC.PA")
    c2 = _add_company(db_session, ticker="BNP.PA")

    fin_svc = MagicMock()
    kpi_svc = MagicMock()
    fin_svc.refresh_company_data.side_effect = [
        _make_data_result(c1.id, "MC.PA"),
        _make_data_result(c2.id, "BNP.PA", success=False),
    ]
    kpi_svc.compute_and_upsert_for_company.return_value = _make_kpi_result(c1.id)

    svc = UniverseDiscoveryService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=kpi_svc,
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.batch_refresh_universe()

    assert isinstance(result, UniverseRefreshResult)
    assert result.total == 2
    assert result.succeeded == 1
    assert result.failed == 1
    assert result.skipped == 0
    assert len(result.results) == 2


def test_batch_refresh_universe_tolerates_unexpected_exception(db_session):
    _add_company(db_session, ticker="MC.PA")

    fin_svc = MagicMock()
    kpi_svc = MagicMock()
    fin_svc.refresh_company_data.side_effect = RuntimeError("network exploded")

    svc = UniverseDiscoveryService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=kpi_svc,
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.batch_refresh_universe()

    assert result.total == 1
    assert result.failed == 1
    assert result.succeeded == 0
    assert "network exploded" in result.results[0].error


def test_batch_refresh_universe_empty_db(db_session):
    fin_svc = MagicMock()
    kpi_svc = MagicMock()
    svc = UniverseDiscoveryService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=kpi_svc,
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.batch_refresh_universe()

    assert result.total == 0
    assert result.succeeded == 0
    assert result.failed == 0
    assert result.results == []


def test_batch_refresh_skips_inactive_companies(db_session):
    _add_company(db_session, ticker="MC.PA")
    inactive = Company(isin="ISININACTIVE", ticker="INACTIVE", name="Inactive Corp", currency="EUR", is_active=False)
    db_session.add(inactive)
    db_session.flush()

    fin_svc = MagicMock()
    kpi_svc = MagicMock()
    fin_svc.refresh_company_data.return_value = _make_data_result(1, "MC.PA")
    kpi_svc.compute_and_upsert_for_company.return_value = _make_kpi_result(1)

    svc = UniverseDiscoveryService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=kpi_svc,
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.batch_refresh_universe()

    assert result.total == 1


# ---------------------------------------------------------------------------
# source_origin tracking
# ---------------------------------------------------------------------------


def test_manual_ingestion_sets_source_origin(db_session):
    company = _add_company(db_session, ticker="MC.PA", source=SOURCE_MANUAL)
    assert company.source_origin == SOURCE_MANUAL


def test_seed_sets_source_origin(db_session):
    company = _add_company(db_session, ticker="MC.PA", source=SOURCE_SEED)
    assert company.source_origin == SOURCE_SEED
