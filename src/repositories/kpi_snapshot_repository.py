from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.kpi_snapshot import KpiSnapshot


def create(session: Session, snapshot: KpiSnapshot) -> KpiSnapshot:
    session.add(snapshot)
    session.flush()
    return snapshot


def get_by_id(session: Session, snapshot_id: int) -> KpiSnapshot | None:
    return session.get(KpiSnapshot, snapshot_id)


def get_by_company(session: Session, company_id: int) -> list[KpiSnapshot]:
    stmt = select(KpiSnapshot).where(KpiSnapshot.company_id == company_id).order_by(KpiSnapshot.snapshot_date.desc())
    return list(session.execute(stmt).scalars())


def get_by_company_and_date(session: Session, company_id: int, snapshot_date: date) -> KpiSnapshot | None:
    stmt = select(KpiSnapshot).where(
        KpiSnapshot.company_id == company_id,
        KpiSnapshot.snapshot_date == snapshot_date,
    )
    return session.execute(stmt).scalar_one_or_none()


def get_latest(session: Session, company_id: int) -> KpiSnapshot | None:
    stmt = (
        select(KpiSnapshot)
        .where(KpiSnapshot.company_id == company_id)
        .order_by(KpiSnapshot.snapshot_date.desc())
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def delete(session: Session, snapshot_id: int) -> bool:
    snapshot = get_by_id(session, snapshot_id)
    if snapshot is None:
        return False
    session.delete(snapshot)
    session.flush()
    return True
