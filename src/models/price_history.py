from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("company_id", "date", name="uq_price_company_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)

    open: Mapped[float | None]
    high: Mapped[float | None]
    low: Mapped[float | None]
    close: Mapped[float]
    adjusted_close: Mapped[float | None]
    volume: Mapped[int | None]

    company: Mapped["Company"] = relationship(back_populates="price_history")
