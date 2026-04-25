from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.company import Company
from src.models.dividend import Dividend
from src.repositories import company_repository, dividend_repository


def _make_company(session) -> Company:
    return company_repository.create(session, Company(isin="FR0000120271", name="TotalEnergies", currency="EUR"))


def _make_dividend(company_id: int, ex_date: date, amount: float = 0.79) -> Dividend:
    return Dividend(
        company_id=company_id,
        ex_date=ex_date,
        payment_date=ex_date,
        amount=amount,
        currency="EUR",
        dividend_type="cash",
    )


def test_create_and_get_by_id(db_session):
    company = _make_company(db_session)
    dividend = dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 5, 1)))
    result = dividend_repository.get_by_id(db_session, dividend.id)
    assert result is not None
    assert result.amount == pytest.approx(0.79)


def test_get_by_company_ordered_desc(db_session):
    company = _make_company(db_session)
    dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 4, 1), amount=0.74))
    dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 5, 1), amount=0.79))
    results = dividend_repository.get_by_company(db_session, company.id)
    assert results[0].ex_date == date(2024, 5, 1)


def test_get_by_company_and_ex_date(db_session):
    company = _make_company(db_session)
    dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 5, 1), amount=0.75))
    dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 5, 1), amount=0.79))
    results = dividend_repository.get_by_company_and_ex_date(db_session, company.id, date(2024, 5, 1))
    assert len(results) == 2


def test_get_by_company_in_period(db_session):
    company = _make_company(db_session)
    dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 3, 1), amount=0.7))
    dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 6, 1), amount=0.8))
    results = dividend_repository.get_by_company_in_period(db_session, company.id, date(2024, 4, 1), date(2024, 12, 31))
    assert len(results) == 1
    assert results[0].ex_date == date(2024, 6, 1)


def test_delete(db_session):
    company = _make_company(db_session)
    dividend = dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 5, 1)))
    assert dividend_repository.delete(db_session, dividend.id) is True
    assert dividend_repository.get_by_id(db_session, dividend.id) is None


def test_unique_constraint_company_ex_date_amount(db_session):
    company = _make_company(db_session)
    dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 5, 1), amount=0.79))
    with pytest.raises(IntegrityError):
        dividend_repository.create(db_session, _make_dividend(company.id, date(2024, 5, 1), amount=0.79))
    db_session.rollback()
