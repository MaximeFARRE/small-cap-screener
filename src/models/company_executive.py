from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class CompanyExecutive(Base):
    __tablename__ = "company_executives"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), default=None)
    age: Mapped[int | None] = mapped_column(default=None)
    total_pay: Mapped[float | None] = mapped_column(default=None)
    year_born: Mapped[int | None] = mapped_column(default=None)
    fiscal_year: Mapped[int | None] = mapped_column(default=None)
    source: Mapped[str | None] = mapped_column(String(30), default=None)
    fetched_at: Mapped[datetime | None] = mapped_column(default=None)

    company: Mapped[Company] = relationship(back_populates="executives")
