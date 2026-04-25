from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.dividend import Dividend


def create(session: Session, dividend: Dividend) -> Dividend:
    session.add(dividend)
    session.flush()
    return dividend


def get_by_id(session: Session, dividend_id: int) -> Dividend | None:
    return session.get(Dividend, dividend_id)


def get_by_company_id(session: Session, company_id: int) -> list[Dividend]:
    stmt = select(Dividend).where(Dividend.company_id == company_id).order_by(Dividend.ex_date.desc())
    return list(session.execute(stmt).scalars())


def get_by_company(session: Session, company_id: int) -> list[Dividend]:
    return get_by_company_id(session, company_id)


def get_by_company_and_ex_date(session: Session, company_id: int, ex_date: date) -> Dividend | None:
    stmt = select(Dividend).where(Dividend.company_id == company_id, Dividend.ex_date == ex_date)
    return session.execute(stmt).scalar_one_or_none()


def get_latest_by_company(session: Session, company_id: int) -> Dividend | None:
    stmt = select(Dividend).where(Dividend.company_id == company_id).order_by(Dividend.ex_date.desc()).limit(1)
    return session.execute(stmt).scalar_one_or_none()


def upsert(session: Session, dividend: Dividend) -> Dividend:
    existing = get_by_company_and_ex_date(session, dividend.company_id, dividend.ex_date)
    if existing is None:
        return create(session, dividend)
    existing.payment_date = dividend.payment_date
    existing.amount = dividend.amount
    existing.currency = dividend.currency
    existing.dividend_type = dividend.dividend_type
    session.flush()
    return existing


def get_by_company_in_period(session: Session, company_id: int, start_date: date, end_date: date) -> list[Dividend]:
    stmt = (
        select(Dividend)
        .where(
            Dividend.company_id == company_id,
            Dividend.ex_date >= start_date,
            Dividend.ex_date <= end_date,
        )
        .order_by(Dividend.ex_date.desc())
    )
    return list(session.execute(stmt).scalars())


def delete(session: Session, dividend_id: int) -> bool:
    dividend = get_by_id(session, dividend_id)
    if dividend is None:
        return False
    session.delete(dividend)
    session.flush()
    return True
