from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from src.models.kpi_snapshot import KpiSnapshot
from src.repositories.database import get_session
from src.services.ratio_service import RatioService

SessionScopeFactory = Callable[[], AbstractContextManager[Session]]


@dataclass
class KpiSnapshotServiceResult:
    company_id: int
    snapshot_date: date
    success: bool
    snapshot_id: int | None = None
    error: str | None = None
    stage: str | None = None
    metrics: dict[str, float | int | None] = field(default_factory=dict)


@dataclass
class KpiSnapshotService:
    session_scope_factory: SessionScopeFactory = get_session
    ratio_service: RatioService = field(default_factory=RatioService)
    source_name: str = "ratio_service_v1"

    def compute_and_upsert_for_company(
        self,
        company_id: int,
        snapshot_date: date,
    ) -> KpiSnapshotServiceResult:
        raise NotImplementedError


def build_snapshot_payload(
    company_id: int,
    snapshot_date: date,
    metrics: dict[str, float | int | None],
    source: str,
) -> KpiSnapshot:
    return KpiSnapshot(
        company_id=company_id,
        snapshot_date=snapshot_date,
        metrics=metrics,
        source=source,
    )
