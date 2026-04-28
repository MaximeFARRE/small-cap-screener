from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class CompanyInsiderTransaction(Base):
    __tablename__ = "company_insider_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    insider_name: Mapped[str | None] = mapped_column(String(200), default=None)
    relation: Mapped[str | None] = mapped_column(String(200), default=None)
    transaction_text: Mapped[str | None] = mapped_column(String(500), default=None)
    ownership: Mapped[str | None] = mapped_column(String(100), default=None)
    shares: Mapped[float | None] = mapped_column(default=None)
    market_value: Mapped[float | None] = mapped_column(default=None)
    start_date: Mapped[date | None] = mapped_column(default=None)
    source: Mapped[str | None] = mapped_column(String(30), default=None)
    fetched_at: Mapped[datetime | None] = mapped_column(default=None)

    company: Mapped[Company] = relationship(back_populates="insider_transactions")
