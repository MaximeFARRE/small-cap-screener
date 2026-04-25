from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (UniqueConstraint("company_id", name="uq_watchlist_company"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    notes: Mapped[str | None] = mapped_column(String(500))
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="watchlist_entries")
