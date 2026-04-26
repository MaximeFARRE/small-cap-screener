from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock

import pytest

from src.models.company import Company
from src.repositories import company_repository
from src.repositories.providers.base import CompanyProfile, TickerNotFoundError
from src.services.financial_data_service import CompanyDataRefreshResult
from src.services.kpi_snapshot_service import KpiSnapshotServiceResult
from src.services.ticker_ingestion_service import (
    TickerIngestionService,
    validate_ingestion_identifier,
    validate_ticker_format,
)

# ---------------------------------------------------------------------------
# validate_ticker_format
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ticker",
    ["MC.PA", "ALAMY.PA", "BNP", "GOOGL", "A", "A123456789", "MC.PAR"],
)
def test_validate_ticker_format_valid(ticker):
    assert validate_ticker_format(ticker) is None


@pytest.mark.parametrize(
    "ticker",
    [
        "",
        "MC PA",
        "MC.PA.FR",
        "A" * 21,
        "mc-pa",
        "!!BAD",
    ],
)
def test_validate_ticker_format_invalid(ticker):
    assert validate_ticker_format(ticker) is not None


@pytest.mark.parametrize(
    "identifier",
    ["MC.PA", "ALAMY.PA", "BNP", "FR0000120271", "US0378331005"],
)
def test_validate_ingestion_identifier_valid(identifier):
    assert validate_ingestion_identifier(identifier) is None


@pytest.mark.parametrize(
    "identifier",
    ["", "bad ticker", "FR0000120271X", "FR00001202711", "mc-pa"],
)
def test_validate_ingestion_identifier_invalid(identifier):
    assert validate_ingestion_identifier(identifier) is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_scope(db_session):
    @contextmanager
    def scope():
        yield db_session

    return scope


def _make_profile(ticker: str, isin: str | None = None) -> CompanyProfile:
    return CompanyProfile(
        ticker=ticker,
        name=f"{ticker} Corp",
        sector="Industrials",
        industry="Capital Goods",
        market="ENX",
        country="France",
        currency="EUR",
        website=None,
        isin=isin,
    )


def _make_financial_service(profile: CompanyProfile, *, refresh_success: bool = True) -> MagicMock:
    svc = MagicMock()
    svc.provider.get_company_profile.return_value = profile
    svc.provider.search_by_isin.return_value = profile.ticker
    svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1,
        ticker=profile.ticker,
        success=refresh_success,
        prices_added=10,
        statements_added=3,
        error=None if refresh_success else "fetch failed",
        stage=None if refresh_success else "fetch",
    )
    return svc


def _make_kpi_service(*, success: bool = True, snapshot_id: int = 42) -> MagicMock:
    svc = MagicMock()
    svc.compute_and_upsert_for_company.return_value = KpiSnapshotServiceResult(
        company_id=1,
        snapshot_date=date.today(),
        success=success,
        snapshot_id=snapshot_id if success else None,
        error=None if success else "no price data",
    )
    return svc


# ---------------------------------------------------------------------------
# ingest_ticker — format validation
# ---------------------------------------------------------------------------


def test_ingest_ticker_invalid_format(db_session):
    svc = TickerIngestionService(
        financial_data_service=MagicMock(),
        kpi_snapshot_service=MagicMock(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("BAD TICKER")
    assert not result.success
    assert result.stage == "validate"
    assert result.error is not None


# ---------------------------------------------------------------------------
# ingest_ticker — provider errors
# ---------------------------------------------------------------------------


def test_ingest_ticker_not_found(db_session):
    fin_svc = MagicMock()
    fin_svc.provider.get_company_profile.side_effect = TickerNotFoundError("not found")
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=MagicMock(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("XXXX.PA")
    assert not result.success
    assert result.stage == "fetch"
    assert "introuvable" in (result.error or "").lower()


def test_ingest_ticker_provider_error(db_session):
    fin_svc = MagicMock()
    fin_svc.provider.get_company_profile.side_effect = RuntimeError("network failure")
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=MagicMock(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("MC.PA")
    assert not result.success
    assert result.stage == "fetch"


# ---------------------------------------------------------------------------
# ingest_ticker — company creation / reuse
# ---------------------------------------------------------------------------


def test_ingest_ticker_creates_new_company(db_session):
    profile = _make_profile("MC.PA", isin="FR0000131104")
    fin_svc = _make_financial_service(profile)
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1, ticker="MC.PA", success=True, prices_added=5, statements_added=2
    )
    kpi_svc = _make_kpi_service()
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=kpi_svc,
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("MC.PA")
    assert result.success
    assert result.created is True
    assert result.kpi_snapshot_id == 42
    companies = company_repository.get_all(db_session)
    assert len(companies) == 1
    assert companies[0].ticker == "MC.PA"
    assert companies[0].isin == "FR0000131104"


def test_ingest_ticker_stores_none_isin_when_provider_has_no_isin(db_session):
    profile = _make_profile("ALAMY.PA", isin=None)
    fin_svc = _make_financial_service(profile)
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1, ticker="ALAMY.PA", success=True, prices_added=2, statements_added=1
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("ALAMY.PA")
    assert result.success
    companies = company_repository.get_all(db_session)
    assert companies[0].isin is None


def test_ingest_ticker_ignores_invalid_provider_isin_and_continues(db_session, caplog):
    profile = _make_profile("VLA.PA", isin="YFVLAPA")
    fin_svc = _make_financial_service(profile)
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1, ticker="VLA.PA", success=True, prices_added=2, statements_added=1
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )

    with caplog.at_level("WARNING", logger="src.services.ticker_ingestion_service"):
        result = svc.ingest_ticker("VLA.PA")

    assert result.success
    companies = company_repository.get_all(db_session)
    assert companies[0].isin is None
    assert any("ignored invalid provider isin" in message for message in caplog.messages)


def test_ingest_ticker_cleans_existing_invalid_isin_before_refresh(db_session, caplog):
    existing = Company(
        isin="YFVLAPA",
        ticker="VLA.PA",
        name="Valneva",
        currency="EUR",
        is_active=True,
    )
    db_session.add(existing)
    db_session.flush()

    profile = _make_profile("VLA.PA", isin=None)
    fin_svc = _make_financial_service(profile)
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=existing.id, ticker="VLA.PA", success=True, prices_added=2, statements_added=1
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )

    with caplog.at_level("WARNING", logger="src.services.ticker_ingestion_service"):
        result = svc.ingest_ticker("VLA.PA")

    assert result.success
    updated = company_repository.get_by_id(db_session, existing.id)
    assert updated is not None
    assert updated.isin is None
    assert any("cleared invalid existing isin" in message for message in caplog.messages)


def test_ingest_ticker_reuses_existing_company(db_session):
    existing = Company(
        isin="FR0000131104",
        ticker="MC.PA",
        name="LVMH",
        currency="EUR",
        is_active=True,
    )
    db_session.add(existing)
    db_session.flush()

    profile = _make_profile("MC.PA", isin="FR0000131104")
    fin_svc = _make_financial_service(profile)
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=existing.id, ticker="MC.PA", success=True, prices_added=1, statements_added=0
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("MC.PA")
    assert result.success
    assert result.created is False
    assert len(company_repository.get_all(db_session)) == 1


# ---------------------------------------------------------------------------
# ingest_ticker — downstream failures
# ---------------------------------------------------------------------------


def test_ingest_ticker_refresh_failure(db_session):
    profile = _make_profile("MC.PA")
    fin_svc = _make_financial_service(profile, refresh_success=False)
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("MC.PA")
    assert not result.success
    assert result.stage == "fetch"
    assert result.error == "fetch failed"


def test_ingest_ticker_kpi_failure_still_succeeds(db_session):
    profile = _make_profile("MC.PA")
    fin_svc = _make_financial_service(profile)
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1, ticker="MC.PA", success=True, prices_added=3, statements_added=1
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(success=False),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("MC.PA")
    assert result.success
    assert result.kpi_snapshot_id is None
    assert any("KPI" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# resolver integration — suffix fallback end-to-end
# ---------------------------------------------------------------------------


def test_ingest_ticker_resolves_suffix_automatically(db_session):
    """User types 'MC' without suffix; ingestion resolves to 'MC.PA'."""
    profile = _make_profile("MC.PA", isin="FR0000131104")
    fin_svc = MagicMock()
    fin_svc.provider.get_company_profile.side_effect = [
        TickerNotFoundError("MC bare not found"),
        profile,  # MC.PA found
    ]
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1, ticker="MC.PA", success=True, prices_added=5, statements_added=2
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("MC")
    assert result.success
    assert result.ticker == "MC"
    assert result.resolved_ticker == "MC.PA"
    companies = company_repository.get_all(db_session)
    assert companies[0].ticker == "MC.PA"


def test_ingest_ticker_exposes_resolved_ticker_on_success(db_session):
    profile = _make_profile("MC.PA")
    fin_svc = _make_financial_service(profile)
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1, ticker="MC.PA", success=True, prices_added=2, statements_added=1
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )
    result = svc.ingest_ticker("MC.PA")
    assert result.success
    assert result.resolved_ticker == "MC.PA"


def test_ingest_identifier_accepts_isin_only(db_session):
    profile = _make_profile("VLA.PA", isin="FR0004056851")
    fin_svc = _make_financial_service(profile)
    fin_svc.provider.get_company_profile.return_value = profile
    fin_svc.refresh_company_data.return_value = CompanyDataRefreshResult(
        company_id=1, ticker="VLA.PA", success=True, prices_added=2, statements_added=1
    )
    svc = TickerIngestionService(
        financial_data_service=fin_svc,
        kpi_snapshot_service=_make_kpi_service(),
        session_scope_factory=_make_session_scope(db_session),
    )

    result = svc.ingest_identifier("FR0004056851")

    assert result.success
    assert result.resolved_ticker == "VLA.PA"
    companies = company_repository.get_all(db_session)
    assert len(companies) == 1
    assert companies[0].ticker == "VLA.PA"
    assert companies[0].isin == "FR0004056851"
