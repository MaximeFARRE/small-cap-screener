import enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class PeriodType(enum.StrEnum):
    ANNUAL = "annual"
    HALF_YEAR = "half_year"


class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    fiscal_year: Mapped[int]
    period_type: Mapped[str] = mapped_column(
        String(20), default=PeriodType.ANNUAL, nullable=False
    )

    revenue: Mapped[float | None]
    ebit: Mapped[float | None]
    ebitda: Mapped[float | None]
    net_income: Mapped[float | None]
    total_assets: Mapped[float | None]
    total_equity: Mapped[float | None]
    total_debt: Mapped[float | None]
    net_debt: Mapped[float | None]
    free_cash_flow: Mapped[float | None]
    shares_outstanding: Mapped[float | None]

    company: Mapped["Company"] = relationship(back_populates="financial_statements")
