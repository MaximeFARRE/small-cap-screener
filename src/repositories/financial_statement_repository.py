from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.financial_statement import FinancialStatement, PeriodType


def create(session: Session, stmt: FinancialStatement) -> FinancialStatement:
    session.add(stmt)
    session.flush()
    return stmt


def get_by_id(session: Session, stmt_id: int) -> FinancialStatement | None:
    return session.get(FinancialStatement, stmt_id)


def get_by_company(session: Session, company_id: int) -> list[FinancialStatement]:
    q = (
        select(FinancialStatement)
        .where(FinancialStatement.company_id == company_id)
        .order_by(FinancialStatement.fiscal_year.desc())
    )
    return list(session.execute(q).scalars())


def get_by_company_and_year(
    session: Session,
    company_id: int,
    fiscal_year: int,
    period_type: PeriodType = PeriodType.ANNUAL,
) -> FinancialStatement | None:
    q = select(FinancialStatement).where(
        FinancialStatement.company_id == company_id,
        FinancialStatement.fiscal_year == fiscal_year,
        FinancialStatement.period_type == period_type,
    )
    return session.execute(q).scalar_one_or_none()


def delete(session: Session, stmt_id: int) -> bool:
    stmt = get_by_id(session, stmt_id)
    if stmt is None:
        return False
    session.delete(stmt)
    session.flush()
    return True
