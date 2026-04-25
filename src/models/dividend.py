from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class Dividend(Base):
    __tablename__ = "dividends"
    __table_args__ = (UniqueConstraint("company_id", "ex_date", name="uq_dividend_company_ex_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    ex_date: Mapped[date] = mapped_column(Date, index=True)
    payment_date: Mapped[date | None] = mapped_column(Date)
    amount: Mapped[float]
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    dividend_type: Mapped[str | None] = mapped_column(String(20))

    company: Mapped["Company"] = relationship(back_populates="dividends")
