from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from src.models.company import Company
from src.repositories import company_repository
from src.services.demo_dataset_service import DemoDatasetService
from src.services.screening_service import ScreeningService, UniverseScreeningFilters

_DEMO_SEED_PATH = Path("data/demo/seed_universe_fr_small_caps.csv")


def _make_session_scope(db_session):
    @contextmanager
    def session_scope():
        yield db_session

    return session_scope


def test_build_demo_dataset_is_reproducible_and_exploitable(db_session):
    session_scope = _make_session_scope(db_session)
    service = DemoDatasetService(session_scope_factory=session_scope)

    summary = service.build_demo_dataset(
        seed_csv_path=_DEMO_SEED_PATH,
        reset_existing=True,
        initialize_storage=False,
    )

    assert summary.total_companies == 7
    assert summary.scored_companies == 6
    assert summary.unscored_companies == 1
    assert summary.watchlist_entries == 4
    assert summary.excluded_entries == 1
    assert summary.top_ranked_tickers == ("ALPS.PA", "BRET.PA", "DORD.PA")

    screening_service = ScreeningService(session_scope_factory=session_scope)
    default_rows = screening_service.filter_universe_with_scores(UniverseScreeningFilters())
    with_excluded_rows = screening_service.filter_universe_with_scores(
        UniverseScreeningFilters(include_excluded=True),
    )

    assert "DORD.PA" not in [row.ticker for row in default_rows]
    assert "DORD.PA" in [row.ticker for row in with_excluded_rows]
    assert len(default_rows) == 6
    assert len(with_excluded_rows) == 7


def test_build_demo_dataset_reset_existing_replaces_previous_records(db_session):
    session_scope = _make_session_scope(db_session)
    service = DemoDatasetService(session_scope_factory=session_scope)

    service.build_demo_dataset(
        seed_csv_path=_DEMO_SEED_PATH,
        reset_existing=True,
        initialize_storage=False,
    )

    company_repository.create(
        db_session,
        Company(
            isin="FR0000999000",
            ticker="DUMMY.PA",
            name="Dummy Company",
            country="France",
            sector="Technology",
            market="PAR",
            currency="EUR",
            is_active=True,
            market_cap=100_000_000.0,
            average_daily_volume=100_000.0,
        ),
    )

    summary = service.build_demo_dataset(
        seed_csv_path=_DEMO_SEED_PATH,
        reset_existing=True,
        initialize_storage=False,
    )

    assert summary.total_companies == 7
    assert company_repository.get_by_ticker(db_session, "DUMMY.PA") is None
