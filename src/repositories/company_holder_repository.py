from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models.company_holder import CompanyHolder


def get_by_company(session: Session, company_id: int) -> list[CompanyHolder]:
    stmt = (
        select(CompanyHolder)
        .where(CompanyHolder.company_id == company_id)
        .order_by(CompanyHolder.sort_order.asc(), CompanyHolder.id.asc())
    )
    return list(session.execute(stmt).scalars())


def get_by_company_and_type(session: Session, company_id: int, holder_type: str) -> list[CompanyHolder]:
    stmt = (
        select(CompanyHolder)
        .where(CompanyHolder.company_id == company_id, CompanyHolder.holder_type == holder_type)
        .order_by(CompanyHolder.sort_order.asc(), CompanyHolder.id.asc())
    )
    return list(session.execute(stmt).scalars())


def replace_for_company(session: Session, company_id: int, holders: list[CompanyHolder]) -> None:
    session.execute(delete(CompanyHolder).where(CompanyHolder.company_id == company_id))
    for holder in holders:
        session.add(holder)
    session.flush()
