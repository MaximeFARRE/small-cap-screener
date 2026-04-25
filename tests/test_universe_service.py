from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import select

from src.models.company import Company
from src.services.universe_service import UniverseService


def _write_seed_csv(path, rows: list[tuple[str, str, str, str, str, str, str]]) -> None:
    content = "name,ticker,isin,exchange,country,sector,currency\n"
    content += "".join(",".join(row) + "\n" for row in rows)
    path.write_text(content, encoding="utf-8")


def _make_service(db_session, max_market_cap: float = 500_000_000.0, min_avg_daily_volume: float | None = 100_000.0):
    @contextmanager
    def session_scope():
        yield db_session

    return UniverseService(
        session_scope_factory=session_scope,
        default_country="France",
        default_max_market_cap=max_market_cap,
        default_min_average_daily_volume=min_avg_daily_volume,
    )


def test_load_seed_universe_complete(db_session, tmp_path):
    csv_path = tmp_path / "seed.csv"
    _write_seed_csv(
        csv_path,
        [
            ("Alpha", "ALPHA.PA", "FR0000001001", "PAR", "France", "Industrial", "EUR"),
            ("Beta", "BETA.PA", "FR0000001002", "PAR", "France", "Retail", "EUR"),
            ("Gamma", "GAMMA.DE", "DE0000001003", "XETRA", "Germany", "Industrial", "EUR"),
        ],
    )
    service = _make_service(db_session)

    imported = service.load_seed_universe(csv_path)

    assert len(imported) == 3
    assert {company.ticker for company in imported} == {"ALPHA.PA", "BETA.PA", "GAMMA.DE"}


def test_refresh_investable_universe_is_coherent(db_session, tmp_path):
    csv_path = tmp_path / "seed_filter.csv"
    _write_seed_csv(
        csv_path,
        [
            ("Alpha", "ALPHA.PA", "FR0000002001", "PAR", "France", "Industrial", "EUR"),
            ("Beta", "BETA.PA", "FR0000002002", "PAR", "France", "Retail", "EUR"),
            ("Gamma", "GAMMA.PA", "FR0000002003", "PAR", "France", "Energy", "EUR"),
            ("Delta", "DELTA.DE", "DE0000002004", "XETRA", "Germany", "Industrial", "EUR"),
            ("Epsilon", "EPSI.PA", "FR0000002005", "PAR", "France", "Tech", "EUR"),
        ],
    )
    service = _make_service(db_session)
    service.load_seed_universe(csv_path)

    companies = list(db_session.execute(select(Company)).scalars())
    by_ticker = {company.ticker: company for company in companies}
    by_ticker["ALPHA.PA"].market_cap = 300_000_000.0
    by_ticker["ALPHA.PA"].average_daily_volume = 200_000.0
    by_ticker["BETA.PA"].market_cap = 900_000_000.0
    by_ticker["BETA.PA"].average_daily_volume = 250_000.0
    by_ticker["GAMMA.PA"].is_active = False
    by_ticker["GAMMA.PA"].market_cap = 200_000_000.0
    by_ticker["GAMMA.PA"].average_daily_volume = 250_000.0
    by_ticker["DELTA.DE"].market_cap = 100_000_000.0
    by_ticker["DELTA.DE"].average_daily_volume = 180_000.0
    by_ticker["EPSI.PA"].market_cap = 250_000_000.0
    by_ticker["EPSI.PA"].average_daily_volume = 50_000.0
    db_session.flush()

    investable = service.refresh_investable_universe(
        max_market_cap=500_000_000.0,
        min_average_daily_volume=100_000.0,
    )

    assert [company.name for company in investable] == ["Alpha"]
