from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.company import Company


def create(session: Session, company: Company) -> Company:
    session.add(company)
    session.flush()
    return company


def get_by_id(session: Session, company_id: int) -> Company | None:
    return session.get(Company, company_id)


def get_by_isin(session: Session, isin: str) -> Company | None:
    stmt = select(Company).where(Company.isin == isin)
    return session.execute(stmt).scalar_one_or_none()


def get_all(session: Session) -> list[Company]:
    stmt = select(Company).order_by(Company.name)
    return list(session.execute(stmt).scalars())


def search_by_name(session: Session, query: str) -> list[Company]:
    stmt = select(Company).where(Company.name.ilike(f"%{query}%")).order_by(Company.name)
    return list(session.execute(stmt).scalars())


def update(session: Session, company: Company) -> Company:
    session.flush()
    return company


def delete(session: Session, company_id: int) -> bool:
    company = get_by_id(session, company_id)
    if company is None:
        return False
    session.delete(company)
    session.flush()
    return True
