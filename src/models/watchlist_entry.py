from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, UniqueConstraint, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company

WATCHLIST_STATUS_WATCHING: str = "watching"
WATCHLIST_STATUS_REVIEW: str = "review"
WATCHLIST_STATUS_REJECTED: str = "rejected"
WATCHLIST_STATUS_CONVICTION: str = "conviction"
WATCHLIST_ALLOWED_STATUSES: tuple[str, ...] = (
    WATCHLIST_STATUS_WATCHING,
    WATCHLIST_STATUS_REVIEW,
    WATCHLIST_STATUS_REJECTED,
    WATCHLIST_STATUS_CONVICTION,
)


class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    __table_args__ = (
        UniqueConstraint("company_id", name="uq_watchlist_company"),
        CheckConstraint(
            "status in ('watching', 'review', 'rejected', 'conviction')",
            name="ck_watchlist_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    notes: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(20),
        default=WATCHLIST_STATUS_WATCHING,
        server_default=WATCHLIST_STATUS_WATCHING,
    )
    is_excluded: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
    )
    added_at: Mapped[datetime] = mapped_column(server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="watchlist_entries")
