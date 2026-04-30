from fastapi import APIRouter, Depends

from api.dependencies import get_screening_service, get_watchlist_service
from api.schemas.signals import ScoreMoverSchema, SignalsSchema, TopCompanySchema
from src.services.screening_service import ScreeningService, UniverseScreeningFilters
from src.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/signals", tags=["signals"])

_MOVER_THRESHOLD: float = 5.0
_TOP_N: int = 5


@router.get("", response_model=SignalsSchema)
def get_signals(
    screening: ScreeningService = Depends(get_screening_service),
    watchlist: WatchlistService = Depends(get_watchlist_service),
) -> SignalsSchema:
    snapshots = screening.list_recent_screening_snapshots(limit=1)
    has_snapshot = len(snapshots) > 0

    movers_up: list[ScoreMoverSchema] = []
    movers_down: list[ScoreMoverSchema] = []
    watchlist_alerts: list[ScoreMoverSchema] = []
    snapshot_name: str | None = None
    watchlist_company_ids = {entry.company_id for entry in watchlist.list_watchlist_workflow()}

    if has_snapshot:
        latest = snapshots[0]
        snapshot_name = latest.name
        comparison = screening.compare_snapshot_to_current(
            latest.snapshot_id,
            UniverseScreeningFilters(),
        )
        for row in comparison:
            change = row.total_score_change
            if change is None:
                continue
            schema = ScoreMoverSchema(
                company_id=row.company_id,
                ticker=row.ticker,
                name=row.name,
                sector=row.sector,
                snapshot_total_score=row.snapshot_total_score,
                current_total_score=row.current_total_score,
                total_score_change=change,
                snapshot_rank=row.snapshot_rank,
                current_rank=row.current_rank,
            )
            if change >= _MOVER_THRESHOLD:
                movers_up.append(schema)
            elif change <= -_MOVER_THRESHOLD:
                movers_down.append(schema)

            if (
                row.company_id is not None
                and row.company_id in watchlist_company_ids
                and abs(change) >= _MOVER_THRESHOLD
            ):
                watchlist_alerts.append(schema)

    movers_up.sort(key=lambda r: r.total_score_change or 0, reverse=True)
    movers_down.sort(key=lambda r: r.total_score_change or 0)
    watchlist_alerts.sort(
        key=lambda r: abs(r.total_score_change or 0),
        reverse=True,
    )

    universe = screening.filter_universe_with_scores(
        UniverseScreeningFilters(scored_only=True, top_n=_TOP_N * 4),
    )

    quality_sorted = sorted(
        universe,
        key=lambda e: e.quality_score or 0,
        reverse=True,
    )[:_TOP_N]

    value_sorted = sorted(
        universe,
        key=lambda e: e.value_score or 0,
        reverse=True,
    )[:_TOP_N]

    top_quality = [
        TopCompanySchema(
            company_id=e.company_id,
            ticker=e.ticker,
            name=e.name,
            sector=e.sector,
            total_score=e.total_score,
            quality_score=e.quality_score,
            value_score=e.value_score,
            rank=e.rank,
        )
        for e in quality_sorted
    ]

    top_value = [
        TopCompanySchema(
            company_id=e.company_id,
            ticker=e.ticker,
            name=e.name,
            sector=e.sector,
            total_score=e.total_score,
            quality_score=e.quality_score,
            value_score=e.value_score,
            rank=e.rank,
        )
        for e in value_sorted
    ]

    return SignalsSchema(
        movers_up=movers_up,
        movers_down=movers_down,
        top_quality=top_quality,
        top_value=top_value,
        watchlist_alerts=watchlist_alerts,
        snapshot_name=snapshot_name,
        has_snapshot=has_snapshot,
    )
