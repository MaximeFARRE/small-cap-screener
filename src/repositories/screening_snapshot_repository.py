from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.screening_snapshot import ScreeningSnapshot


def add(session: Session, snapshot: ScreeningSnapshot) -> ScreeningSnapshot:
    session.add(snapshot)
    session.flush()
    return snapshot


def get_by_id(session: Session, snapshot_id: int) -> ScreeningSnapshot | None:
    stmt = select(ScreeningSnapshot).where(ScreeningSnapshot.id == snapshot_id)
    return session.execute(stmt).scalar_one_or_none()


def list_recent(session: Session, limit: int = 20) -> list[ScreeningSnapshot]:
    stmt = (
        select(ScreeningSnapshot)
        .order_by(ScreeningSnapshot.created_at.desc(), ScreeningSnapshot.id.desc())
        .limit(limit)
    )
    return list(session.execute(stmt).scalars())
