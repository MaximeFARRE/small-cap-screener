from datetime import date

from src.models.company import Company
from src.models.price_history import PriceHistory
from src.repositories import company_repository, price_history_repository


def _make_company(session) -> Company:
    return company_repository.create(session, Company(isin="FR0000120271", name="TotalEnergies", currency="EUR"))


def _make_record(company_id: int, record_date: date, close: float = 50.0) -> PriceHistory:
    return PriceHistory(
        company_id=company_id,
        date=record_date,
        open=49.0,
        high=51.0,
        low=48.5,
        close=close,
    )


def test_create_and_get_by_id(db_session):
    company = _make_company(db_session)
    record = price_history_repository.create(db_session, _make_record(company.id, date(2024, 1, 2)))
    result = price_history_repository.get_by_id(db_session, record.id)
    assert result is not None
    assert result.close == 50.0


def test_get_by_company_ordered_desc(db_session):
    company = _make_company(db_session)
    price_history_repository.create(db_session, _make_record(company.id, date(2024, 1, 1)))
    price_history_repository.create(db_session, _make_record(company.id, date(2024, 1, 3)))
    records = price_history_repository.get_by_company(db_session, company.id)
    assert records[0].date == date(2024, 1, 3)


def test_get_by_company_and_date(db_session):
    company = _make_company(db_session)
    price_history_repository.create(db_session, _make_record(company.id, date(2024, 1, 2), close=55.0))
    result = price_history_repository.get_by_company_and_date(db_session, company.id, date(2024, 1, 2))
    assert result is not None
    assert result.close == 55.0


def test_get_by_company_and_date_not_found(db_session):
    company = _make_company(db_session)
    assert price_history_repository.get_by_company_and_date(db_session, company.id, date(2024, 1, 1)) is None


def test_get_latest(db_session):
    company = _make_company(db_session)
    price_history_repository.create(db_session, _make_record(company.id, date(2024, 1, 1), close=40.0))
    price_history_repository.create(db_session, _make_record(company.id, date(2024, 1, 5), close=60.0))
    latest = price_history_repository.get_latest(db_session, company.id)
    assert latest is not None
    assert latest.close == 60.0


def test_delete(db_session):
    company = _make_company(db_session)
    record = price_history_repository.create(db_session, _make_record(company.id, date(2024, 1, 2)))
    assert price_history_repository.delete(db_session, record.id) is True
    assert price_history_repository.get_by_id(db_session, record.id) is None


def test_delete_nonexistent(db_session):
    assert price_history_repository.delete(db_session, 9999) is False
