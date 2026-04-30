from fastapi import APIRouter, Depends

from api.dependencies import get_screening_service
from api.schemas.signals import ScoreMoverSchema, SignalsSchema, TopCompanySchema
from src.services.screening_service import ScreeningService, UniverseScreeningFilters

router = APIRouter(prefix="/signals", tags=["signals"])

_MOVER_THRESHOLD: float = 5.0
_TOP_N: int = 5


@router.get("", response_model=SignalsSchema)
def get_signals(
    screening: ScreeningService = Depends(get_screening_service),
) -> SignalsSchema:
    snapshots = screening.list_recent_screening_snapshots(limit=1)
    has_snapshot = len(snapshots) > 0

    movers_up: list[ScoreMoverSchema] = []
    movers_down: list[ScoreMoverSchema] = []
    snapshot_name: str | None = None

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

    movers_up.sort(key=lambda r: r.total_score_change or 0, reverse=True)
    movers_down.sort(key=lambda r: r.total_score_change or 0)

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
        snapshot_name=snapshot_name,
        has_snapshot=has_snapshot,
    )
