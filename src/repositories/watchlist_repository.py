from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.watchlist_entry import WatchlistEntry


def add(session: Session, entry: WatchlistEntry) -> WatchlistEntry:
    session.add(entry)
    session.flush()
    return entry


def get_by_company_id(session: Session, company_id: int) -> WatchlistEntry | None:
    stmt = select(WatchlistEntry).where(WatchlistEntry.company_id == company_id)
    return session.execute(stmt).scalar_one_or_none()


def list_all(session: Session) -> list[WatchlistEntry]:
    stmt = select(WatchlistEntry).order_by(WatchlistEntry.added_at.desc(), WatchlistEntry.company_id.asc())
    return list(session.execute(stmt).scalars())


def list_excluded_company_ids(session: Session) -> set[int]:
    stmt = select(WatchlistEntry.company_id).where(WatchlistEntry.is_excluded.is_(True))
    return set(session.execute(stmt).scalars())


def update_notes_by_company_id(session: Session, company_id: int, notes: str | None) -> WatchlistEntry | None:
    entry = get_by_company_id(session, company_id)
    if entry is None:
        return None
    entry.notes = notes
    session.flush()
    return entry


def update_status_by_company_id(session: Session, company_id: int, status: str) -> WatchlistEntry | None:
    entry = get_by_company_id(session, company_id)
    if entry is None:
        return None
    entry.status = status
    session.flush()
    return entry


def update_excluded_by_company_id(session: Session, company_id: int, is_excluded: bool) -> WatchlistEntry | None:
    entry = get_by_company_id(session, company_id)
    if entry is None:
        return None
    entry.is_excluded = is_excluded
    session.flush()
    return entry


def remove_by_company_id(session: Session, company_id: int) -> bool:
    entry = get_by_company_id(session, company_id)
    if entry is None:
        return False
    session.delete(entry)
    session.flush()
    return True
