from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Date, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.company import Company


class KpiSnapshot(Base):
    """Calculated KPIs for one company at a specific snapshot date."""

    __tablename__ = "kpi_snapshots"
    __table_args__ = (UniqueConstraint("company_id", "snapshot_date", name="uq_kpi_company_snapshot_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    company: Mapped["Company"] = relationship(back_populates="kpi_snapshots")
