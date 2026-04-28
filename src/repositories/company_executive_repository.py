from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models.company_executive import CompanyExecutive


def create(session: Session, executive: CompanyExecutive) -> CompanyExecutive:
    session.add(executive)
    session.flush()
    return executive


def get_by_company(session: Session, company_id: int) -> list[CompanyExecutive]:
    stmt = (
        select(CompanyExecutive)
        .where(CompanyExecutive.company_id == company_id)
        .order_by(CompanyExecutive.sort_order.asc(), CompanyExecutive.id.asc())
    )
    return list(session.execute(stmt).scalars())


def replace_for_company(session: Session, company_id: int, executives: list[CompanyExecutive]) -> None:
    session.execute(delete(CompanyExecutive).where(CompanyExecutive.company_id == company_id))
    for executive in executives:
        session.add(executive)
    session.flush()
