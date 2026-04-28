from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.models.company_insider_transaction import CompanyInsiderTransaction


def get_by_company(session: Session, company_id: int) -> list[CompanyInsiderTransaction]:
    stmt = (
        select(CompanyInsiderTransaction)
        .where(CompanyInsiderTransaction.company_id == company_id)
        .order_by(CompanyInsiderTransaction.sort_order.asc(), CompanyInsiderTransaction.id.asc())
    )
    return list(session.execute(stmt).scalars())


def replace_for_company(
    session: Session,
    company_id: int,
    transactions: list[CompanyInsiderTransaction],
) -> None:
    session.execute(delete(CompanyInsiderTransaction).where(CompanyInsiderTransaction.company_id == company_id))
    for transaction in transactions:
        session.add(transaction)
    session.flush()
