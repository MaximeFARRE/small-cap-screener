"""Shared fixtures for API integration tests.

Each test gets a fresh in-memory SQLite database.
FastAPI dependency_overrides replace the singleton services with test-scoped ones.
"""

import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

# Ensure project root is on sys.path so `api` and `src` are importable.
_ROOT = Path(__file__).resolve().parents[2]
_ROOT_STR = str(_ROOT)
sys.path.insert(0, _ROOT_STR)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import src.models.company  # noqa: F401
import src.models.company_executive  # noqa: F401
import src.models.company_holder  # noqa: F401
import src.models.company_insider_transaction  # noqa: F401
import src.models.dividend  # noqa: F401
import src.models.financial_statement  # noqa: F401
import src.models.kpi_snapshot  # noqa: F401
import src.models.price_history  # noqa: F401
import src.models.screening_snapshot  # noqa: F401
import src.models.split  # noqa: F401
import src.models.watchlist_entry  # noqa: F401
from api.dependencies import (
    get_company_detail_service,
    get_db_session,
    get_kpi_service,
    get_peer_service,
    get_scoring_service,
    get_screening_service,
    get_watchlist_service,
)
from api.main import app
from src.repositories.database import Base
from src.services.company_detail_service import CompanyDetailService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.peer_comparison_service import PeerComparisonService
from src.services.scoring_service import ScoringService
from src.services.screening_service import ScreeningService
from src.services.watchlist_service import WatchlistService


def _make_session_factory(session: Session):
    @contextmanager
    def _factory() -> Generator[Session, None, None]:
        yield session

    return _factory


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    factory = _make_session_factory(db_session)

    scoring = ScoringService()
    kpi = KpiSnapshotService(session_scope_factory=factory, scoring_service=scoring)
    screening = ScreeningService(
        session_scope_factory=factory,
        scoring_service=scoring,
        kpi_snapshot_service=kpi,
    )
    detail = CompanyDetailService(session_scope_factory=factory)
    watchlist = WatchlistService(
        session_scope_factory=factory,
        scoring_service=scoring,
        kpi_snapshot_service=kpi,
    )
    peers = PeerComparisonService(
        session_scope_factory=factory,
        screening_service=screening,
    )

    app.dependency_overrides[get_db_session] = lambda: db_session
    app.dependency_overrides[get_scoring_service] = lambda: scoring
    app.dependency_overrides[get_kpi_service] = lambda: kpi
    app.dependency_overrides[get_screening_service] = lambda: screening
    app.dependency_overrides[get_company_detail_service] = lambda: detail
    app.dependency_overrides[get_watchlist_service] = lambda: watchlist
    app.dependency_overrides[get_peer_service] = lambda: peers

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
