from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repositories.database import Base

if TYPE_CHECKING:
    from src.models.dividend import Dividend
    from src.models.financial_statement import FinancialStatement
    from src.models.kpi_snapshot import KpiSnapshot
    from src.models.price_history import PriceHistory
    from src.models.split import Split


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    isin: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    ticker: Mapped[str | None] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str | None] = mapped_column(String(100))
    sector: Mapped[str | None] = mapped_column(String(100))
    market: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(default=True)
    market_cap: Mapped[float | None]
    average_daily_volume: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    financial_statements: Mapped[list["FinancialStatement"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    kpi_snapshots: Mapped[list["KpiSnapshot"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    dividends: Mapped[list["Dividend"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    splits: Mapped[list["Split"]] = relationship(back_populates="company", cascade="all, delete-orphan")
