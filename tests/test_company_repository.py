from src.models.company import Company
from src.repositories import company_repository


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
