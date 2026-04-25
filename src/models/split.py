from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class Split(Base):
    __tablename__ = "splits"
    __table_args__ = (UniqueConstraint("company_id", "split_date", "ratio_from", "ratio_to", name="uq_split_unique"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    split_date: Mapped[date] = mapped_column(Date, index=True)
    ratio_from: Mapped[float]
    ratio_to: Mapped[float]

    company: Mapped["Company"] = relationship(back_populates="splits")
