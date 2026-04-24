from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.price_history import PriceHistory


def create(session: Session, record: PriceHistory) -> PriceHistory:
    session.add(record)
    session.flush()
    return record


def get_by_id(session: Session, record_id: int) -> PriceHistory | None:
    return session.get(PriceHistory, record_id)


def get_by_company(session: Session, company_id: int) -> list[PriceHistory]:
    stmt = select(PriceHistory).where(PriceHistory.company_id == company_id).order_by(PriceHistory.date.desc())
    return list(session.execute(stmt).scalars())


def get_by_company_and_date(session: Session, company_id: int, record_date: date) -> PriceHistory | None:
    stmt = select(PriceHistory).where(
        PriceHistory.company_id == company_id,
        PriceHistory.date == record_date,
    )
    return session.execute(stmt).scalar_one_or_none()


def get_latest(session: Session, company_id: int) -> PriceHistory | None:
    stmt = select(PriceHistory).where(PriceHistory.company_id == company_id).order_by(PriceHistory.date.desc()).limit(1)
    return session.execute(stmt).scalar_one_or_none()


def delete(session: Session, record_id: int) -> bool:
    record = get_by_id(session, record_id)
    if record is None:
        return False
    session.delete(record)
    session.flush()
    return True
