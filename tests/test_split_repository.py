from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.company import Company
from src.models.split import Split
from src.repositories import company_repository, split_repository


def _make_company(session) -> Company:
    return company_repository.create(session, Company(isin="FR0000120271", name="TotalEnergies", currency="EUR"))


def _make_split(company_id: int, split_date: date, ratio_from: float = 1.0, ratio_to: float = 2.0) -> Split:
    return Split(
        company_id=company_id,
        split_date=split_date,
        ratio_from=ratio_from,
        ratio_to=ratio_to,
    )


def test_create_and_get_by_id(db_session):
    company = _make_company(db_session)
    split = split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1)))
    result = split_repository.get_by_id(db_session, split.id)
    assert result is not None
    assert result.ratio_to == pytest.approx(2.0)


def test_get_by_company_id_ordered_desc(db_session):
    company = _make_company(db_session)
    split_repository.create(db_session, _make_split(company.id, date(2023, 7, 1), ratio_from=1.0, ratio_to=2.0))
    split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1), ratio_from=2.0, ratio_to=3.0))
    results = split_repository.get_by_company_id(db_session, company.id)
    assert results[0].split_date == date(2024, 7, 1)


def test_get_by_company_and_date(db_session):
    company = _make_company(db_session)
    split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1), ratio_from=1.0, ratio_to=2.0))
    result = split_repository.get_by_company_and_date(db_session, company.id, date(2024, 7, 1))
    assert result is not None
    assert result.ratio_to == pytest.approx(2.0)


def test_get_latest_by_company(db_session):
    company = _make_company(db_session)
    split_repository.create(db_session, _make_split(company.id, date(2023, 7, 1), ratio_from=1.0, ratio_to=2.0))
    split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1), ratio_from=2.0, ratio_to=3.0))
    latest = split_repository.get_latest_by_company(db_session, company.id)
    assert latest is not None
    assert latest.split_date == date(2024, 7, 1)


def test_upsert_updates_existing_split(db_session):
    company = _make_company(db_session)
    split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1), ratio_from=1.0, ratio_to=2.0))

    updated = split_repository.upsert(
        db_session,
        _make_split(company.id, date(2024, 7, 1), ratio_from=1.0, ratio_to=4.0),
    )

    assert updated.ratio_to == pytest.approx(4.0)
    splits = split_repository.get_by_company_id(db_session, company.id)
    assert len(splits) == 1


def test_get_by_company_in_period(db_session):
    company = _make_company(db_session)
    split_repository.create(db_session, _make_split(company.id, date(2023, 7, 1), ratio_from=1.0, ratio_to=2.0))
    split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1), ratio_from=2.0, ratio_to=3.0))
    results = split_repository.get_by_company_in_period(db_session, company.id, date(2024, 1, 1), date(2024, 12, 31))
    assert len(results) == 1
    assert results[0].split_date == date(2024, 7, 1)


def test_delete(db_session):
    company = _make_company(db_session)
    split = split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1)))
    assert split_repository.delete(db_session, split.id) is True
    assert split_repository.get_by_id(db_session, split.id) is None


def test_unique_constraint_company_split_date(db_session):
    company = _make_company(db_session)
    split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1), ratio_from=1.0, ratio_to=2.0))
    with pytest.raises(IntegrityError):
        split_repository.create(db_session, _make_split(company.id, date(2024, 7, 1), ratio_from=2.0, ratio_to=3.0))
    db_session.rollback()
