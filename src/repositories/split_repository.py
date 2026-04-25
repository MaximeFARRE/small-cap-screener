from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.split import Split


def create(session: Session, split: Split) -> Split:
    session.add(split)
    session.flush()
    return split


def get_by_id(session: Session, split_id: int) -> Split | None:
    return session.get(Split, split_id)


def get_by_company(session: Session, company_id: int) -> list[Split]:
    stmt = select(Split).where(Split.company_id == company_id).order_by(Split.split_date.desc())
    return list(session.execute(stmt).scalars())


def get_by_company_and_date(session: Session, company_id: int, split_date: date) -> list[Split]:
    stmt = select(Split).where(Split.company_id == company_id, Split.split_date == split_date).order_by(Split.id)
    return list(session.execute(stmt).scalars())


def get_by_company_in_period(session: Session, company_id: int, start_date: date, end_date: date) -> list[Split]:
    stmt = (
        select(Split)
        .where(
            Split.company_id == company_id,
            Split.split_date >= start_date,
            Split.split_date <= end_date,
        )
        .order_by(Split.split_date.desc())
    )
    return list(session.execute(stmt).scalars())


def delete(session: Session, split_id: int) -> bool:
    split = get_by_id(session, split_id)
    if split is None:
        return False
    session.delete(split)
    session.flush()
    return True
