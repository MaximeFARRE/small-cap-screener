from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.company import Company
from src.models.kpi_snapshot import KpiSnapshot
from src.repositories import company_repository, kpi_snapshot_repository


def _make_company(session) -> Company:
    return company_repository.create(session, Company(isin="FR0000120271", name="TotalEnergies", currency="EUR"))


def _make_snapshot(company_id: int, snapshot_date: date, score: float = 80.0) -> KpiSnapshot:
    return KpiSnapshot(
        company_id=company_id,
        snapshot_date=snapshot_date,
        metrics={"quality_score": score},
        source="manual",
    )


def test_create_and_get_by_id(db_session):
    company = _make_company(db_session)
    snapshot = kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 1, 31)))
    result = kpi_snapshot_repository.get_by_id(db_session, snapshot.id)
    assert result is not None
    assert result.metrics["quality_score"] == 80.0


def test_get_by_company_ordered_desc(db_session):
    company = _make_company(db_session)
    kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 1, 1), score=70.0))
    kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 2, 1), score=90.0))
    snapshots = kpi_snapshot_repository.get_by_company(db_session, company.id)
    assert snapshots[0].snapshot_date == date(2024, 2, 1)


def test_get_by_company_and_date(db_session):
    company = _make_company(db_session)
    kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 1, 31), score=88.0))
    result = kpi_snapshot_repository.get_by_company_and_date(db_session, company.id, date(2024, 1, 31))
    assert result is not None
    assert result.metrics["quality_score"] == 88.0


def test_get_latest(db_session):
    company = _make_company(db_session)
    kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 1, 31), score=75.0))
    kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 2, 29), score=85.0))
    latest = kpi_snapshot_repository.get_latest(db_session, company.id)
    assert latest is not None
    assert latest.snapshot_date == date(2024, 2, 29)


def test_delete(db_session):
    company = _make_company(db_session)
    snapshot = kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 1, 31)))
    assert kpi_snapshot_repository.delete(db_session, snapshot.id) is True
    assert kpi_snapshot_repository.get_by_id(db_session, snapshot.id) is None


def test_unique_constraint_company_snapshot_date(db_session):
    company = _make_company(db_session)
    kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 1, 31), score=70.0))
    with pytest.raises(IntegrityError):
        kpi_snapshot_repository.create(db_session, _make_snapshot(company.id, date(2024, 1, 31), score=90.0))
    db_session.rollback()
