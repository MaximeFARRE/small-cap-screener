from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class CompanyHolder(Base):
    __tablename__ = "company_holders"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    holder_type: Mapped[str] = mapped_column(String(30), nullable=False)
    holder_name: Mapped[str] = mapped_column(String(300), nullable=False)
    weight: Mapped[float | None] = mapped_column(default=None)
    shares: Mapped[float | None] = mapped_column(default=None)
    market_value: Mapped[float | None] = mapped_column(default=None)
    date_reported: Mapped[date | None] = mapped_column(default=None)
    source: Mapped[str | None] = mapped_column(String(30), default=None)
    fetched_at: Mapped[datetime | None] = mapped_column(default=None)

    company: Mapped[Company] = relationship(back_populates="holders")
