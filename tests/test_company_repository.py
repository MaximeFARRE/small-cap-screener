from src.models.company import Company
from src.repositories import company_repository
from src.repositories.seed_universe_repository import SeedUniverseEntry


def _make_company(**kwargs) -> Company:
    defaults = {"isin": "FR0000120271", "name": "TotalEnergies", "currency": "EUR"}
    return Company(**{**defaults, **kwargs})


def test_create_and_get_by_id(db_session):
    company = company_repository.create(db_session, _make_company())
    result = company_repository.get_by_id(db_session, company.id)
    assert result is not None
    assert result.name == "TotalEnergies"


def test_get_by_isin(db_session):
    company_repository.create(db_session, _make_company())
    result = company_repository.get_by_isin(db_session, "FR0000120271")
    assert result is not None
    assert result.isin == "FR0000120271"


def test_get_by_isin_not_found(db_session):
    assert company_repository.get_by_isin(db_session, "NOTEXIST") is None


def test_get_all_ordered_by_name(db_session):
    company_repository.create(db_session, _make_company(isin="FR0000000001", name="Beta"))
    company_repository.create(db_session, _make_company(isin="FR0000000002", name="Alpha"))
    results = company_repository.get_all(db_session)
    assert [c.name for c in results] == ["Alpha", "Beta"]


def test_search_by_name_case_insensitive(db_session):
    company_repository.create(db_session, _make_company(isin="FR0000000001", name="TotalEnergies SA"))
    company_repository.create(db_session, _make_company(isin="FR0000000002", name="Renault"))
    results = company_repository.search_by_name(db_session, "total")
    assert len(results) == 1
    assert results[0].name == "TotalEnergies SA"


def test_search_by_name_no_match(db_session):
    company_repository.create(db_session, _make_company())
    assert company_repository.search_by_name(db_session, "xyz") == []


def test_update(db_session):
    company = company_repository.create(db_session, _make_company())
    company.sector = "Energy"
    company_repository.update(db_session, company)
    result = company_repository.get_by_id(db_session, company.id)
    assert result.sector == "Energy"


def test_delete(db_session):
    company = company_repository.create(db_session, _make_company())
    assert company_repository.delete(db_session, company.id) is True
    assert company_repository.get_by_id(db_session, company.id) is None


def test_delete_nonexistent(db_session):
    assert company_repository.delete(db_session, 9999) is False


def _seed_entry(**kwargs) -> SeedUniverseEntry:
    defaults = {
        "name": "TotalEnergies",
        "ticker": "TTE.PA",
        "isin": "FR0000120271",
        "exchange": "PAR",
        "country": "France",
        "sector": "Energy",
        "currency": "EUR",
    }
    return SeedUniverseEntry(**{**defaults, **kwargs})


def test_bulk_upsert_from_seed_first_import(db_session):
    entries = [
        _seed_entry(),
        _seed_entry(name="Air Liquide", ticker="AI.PA", isin="FR0000120073", sector="Chemicals"),
    ]

    upserted = company_repository.bulk_upsert_from_seed(db_session, entries)

    assert len(upserted) == 2
    companies = company_repository.get_all(db_session)
    assert len(companies) == 2
    assert {c.ticker for c in companies} == {"TTE.PA", "AI.PA"}


def test_bulk_upsert_from_seed_reimport_same_seed(db_session):
    entries = [
        _seed_entry(),
        _seed_entry(name="Air Liquide", ticker="AI.PA", isin="FR0000120073", sector="Chemicals"),
    ]

    company_repository.bulk_upsert_from_seed(db_session, entries)
    company_repository.bulk_upsert_from_seed(db_session, entries)

    companies = company_repository.get_all(db_session)
    assert len(companies) == 2


def test_bulk_upsert_from_seed_prevents_inconsistent_duplicates(db_session):
    company_repository.create(
        db_session,
        _make_company(isin="FR0000000001", ticker="DUP.PA", name="Duplicate A", sector="Old", market="OLD"),
    )
    company_repository.create(
        db_session,
        _make_company(isin="FR0000000002", ticker="OTHER.PA", name="Duplicate B", sector="Old", market="OLD"),
    )

    company_repository.bulk_upsert_from_seed(
        db_session,
        [
            _seed_entry(
                name="Unified Company",
                ticker="DUP.PA",
                isin="FR0000000002",
                exchange="PAR",
                sector="Industrial",
            )
        ],
    )

    companies = company_repository.get_all(db_session)
    assert len(companies) == 1
    assert companies[0].isin == "FR0000000002"
    assert companies[0].ticker == "DUP.PA"
    assert companies[0].name == "Unified Company"


def test_bulk_upsert_from_seed_updates_existing_company(db_session):
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000120271",
            ticker="OLD.PA",
            name="Old Name",
            sector="Old Sector",
            market="OLD",
            currency="USD",
        ),
    )

    company_repository.bulk_upsert_from_seed(
        db_session,
        [
            _seed_entry(
                name="TotalEnergies SE",
                ticker="TTE.PA",
                isin="FR0000120271",
                exchange="PAR",
                sector="Energy",
                currency="EUR",
            )
        ],
    )

    company = company_repository.get_by_isin(db_session, "FR0000120271")
    assert company is not None
    assert company.name == "TotalEnergies SE"
    assert company.ticker == "TTE.PA"
    assert company.sector == "Energy"
    assert company.market == "PAR"
    assert company.currency == "EUR"


def test_filter_small_caps_by_market_cap(db_session):
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000101",
            ticker="SMALL.PA",
            name="Small Cap",
            country="France",
            is_active=True,
            market_cap=150_000_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000102",
            ticker="BIG.PA",
            name="Big Cap",
            country="France",
            is_active=True,
            market_cap=2_000_000_000.0,
        ),
    )

    results = company_repository.filter_small_caps(db_session, max_market_cap=500_000_000.0)

    assert len(results) == 1
    assert results[0].ticker == "SMALL.PA"


def test_get_investable_universe_excludes_inactive(db_session):
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000201",
            ticker="ACTIVE.PA",
            name="Active Co",
            country="France",
            is_active=True,
            market_cap=200_000_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000202",
            ticker="INACTIVE.PA",
            name="Inactive Co",
            country="France",
            is_active=False,
            market_cap=180_000_000.0,
        ),
    )

    results = company_repository.get_investable_universe(db_session, max_market_cap=500_000_000.0)

    assert len(results) == 1
    assert results[0].ticker == "ACTIVE.PA"


def test_get_investable_universe_excludes_invalid_ticker_but_allows_missing_isin(db_session):
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000301",
            ticker="VALID.PA",
            name="Valid Co",
            country="France",
            is_active=True,
            market_cap=100_000_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000302",
            ticker="",
            name="Empty Ticker",
            country="France",
            is_active=True,
            market_cap=120_000_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin=None,
            ticker="NOISIN.PA",
            name="No ISIN",
            country="France",
            is_active=True,
            market_cap=130_000_000.0,
        ),
    )

    results = company_repository.get_investable_universe(db_session, max_market_cap=500_000_000.0)

    assert [company.ticker for company in results] == ["NOISIN.PA", "VALID.PA"]


def test_get_investable_universe_is_stable(db_session):
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000401",
            ticker="ALPHA.PA",
            name="Alpha",
            country="France",
            is_active=True,
            market_cap=250_000_000.0,
            average_daily_volume=200_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000402",
            ticker="BETA.PA",
            name="Beta",
            country="France",
            is_active=True,
            market_cap=300_000_000.0,
            average_daily_volume=50_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000403",
            ticker="GAMMA.PA",
            name="Gamma",
            country="France",
            is_active=True,
            market_cap=1_200_000_000.0,
            average_daily_volume=300_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="DE0000000404",
            ticker="DELTA.DE",
            name="Delta",
            country="Germany",
            is_active=True,
            market_cap=200_000_000.0,
            average_daily_volume=220_000.0,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000405",
            ticker="EPSI.PA",
            name="Epsilon",
            country="France",
            is_active=True,
            market_cap=240_000_000.0,
            average_daily_volume=None,
        ),
    )
    company_repository.create(
        db_session,
        _make_company(
            isin="FR0000000406",
            ticker="ZETA.PA",
            name="Zeta",
            country="France",
            is_active=False,
            market_cap=180_000_000.0,
            average_daily_volume=190_000.0,
        ),
    )

    results = company_repository.get_investable_universe(
        db_session,
        max_market_cap=500_000_000.0,
        min_average_daily_volume=100_000.0,
    )

    assert [company.name for company in results] == ["Alpha", "Epsilon"]
