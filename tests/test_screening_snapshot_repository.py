from datetime import datetime

from src.models.screening_snapshot import ScreeningSnapshot
from src.repositories import screening_snapshot_repository


def _make_snapshot(
    *,
    name: str,
    created_at: datetime | None = None,
    filters: dict | None = None,
    company_ids: list[int] | None = None,
    scores: dict | None = None,
) -> ScreeningSnapshot:
    kwargs: dict[str, object] = {
        "name": name,
        "filters": {} if filters is None else filters,
        "company_ids": [] if company_ids is None else company_ids,
        "scores": {} if scores is None else scores,
    }
    if created_at is not None:
        kwargs["created_at"] = created_at
    return ScreeningSnapshot(**kwargs)


def test_add_and_get_by_id(db_session):
    added = screening_snapshot_repository.add(
        db_session,
        _make_snapshot(
            name="snapshot a",
            filters={"sector": "energy"},
            company_ids=[1, 2],
            scores={"company_count": 2, "results": [{"ticker": "ALP.PA"}]},
        ),
    )

    fetched = screening_snapshot_repository.get_by_id(db_session, added.id)

    assert fetched is not None
    assert fetched.id == added.id
    assert fetched.name == "snapshot a"
    assert fetched.filters == {"sector": "energy"}
    assert fetched.company_ids == [1, 2]
    assert fetched.scores["company_count"] == 2


def test_list_recent_returns_newest_first(db_session):
    older = screening_snapshot_repository.add(
        db_session,
        _make_snapshot(name="older", created_at=datetime(2024, 1, 1, 10, 0, 0)),
    )
    newer = screening_snapshot_repository.add(
        db_session,
        _make_snapshot(name="newer", created_at=datetime(2024, 2, 1, 10, 0, 0)),
    )

    listed = screening_snapshot_repository.list_recent(db_session, limit=10)

    assert listed[0].id == newer.id
    assert listed[1].id == older.id


def test_list_recent_respects_limit(db_session):
    screening_snapshot_repository.add(db_session, _make_snapshot(name="s1", created_at=datetime(2024, 1, 1, 10, 0, 0)))
    screening_snapshot_repository.add(db_session, _make_snapshot(name="s2", created_at=datetime(2024, 1, 2, 10, 0, 0)))
    screening_snapshot_repository.add(db_session, _make_snapshot(name="s3", created_at=datetime(2024, 1, 3, 10, 0, 0)))

    listed = screening_snapshot_repository.list_recent(db_session, limit=2)

    assert len(listed) == 2
    assert [snapshot.name for snapshot in listed] == ["s3", "s2"]
