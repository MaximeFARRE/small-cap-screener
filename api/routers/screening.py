from fastapi import APIRouter, Depends, HTTPException, Query

from api.dependencies import get_screening_service
from api.schemas.screening import (
    CompanyRowSchema,
    SaveSnapshotRequest,
    ScreeningFiltersSchema,
    SnapshotComparisonRowSchema,
    SnapshotSummarySchema,
    SnapshotViewSchema,
)
from src.services.screening_service import (
    ScreeningService,
    UniverseScreeningFilters,
)

router = APIRouter(prefix="/screening", tags=["screening"])


def _to_service_filters(f: ScreeningFiltersSchema) -> UniverseScreeningFilters:
    return UniverseScreeningFilters(
        sector=f.sector,
        min_total_score=f.min_total_score,
        min_data_quality_score=f.min_data_quality_score,
        max_pe=f.max_pe,
        min_growth=f.min_growth,
        min_margin=f.min_margin,
        min_market_cap=f.min_market_cap,
        max_market_cap=f.max_market_cap,
        stale_only=f.stale_only,
        scored_only=f.scored_only,
        watchlist_scope=f.watchlist_scope,  # type: ignore[arg-type]
        watchlist_status=f.watchlist_status,
        include_excluded=f.include_excluded,
        top_n=f.top_n,
        sort_by=f.sort_by,  # type: ignore[arg-type]
        descending=f.descending,
    )


@router.get("/universe", response_model=list[CompanyRowSchema])
def get_universe(
    sector: str | None = Query(None),
    min_total_score: float | None = Query(None),
    scored_only: bool = Query(False),
    watchlist_scope: str = Query("all"),
    sort_by: str = Query("rank"),
    top_n: int | None = Query(None),
    screening: ScreeningService = Depends(get_screening_service),
) -> list[CompanyRowSchema]:
    filters = UniverseScreeningFilters(
        sector=sector,
        min_total_score=min_total_score,
        scored_only=scored_only,
        watchlist_scope=watchlist_scope,  # type: ignore[arg-type]
        sort_by=sort_by,  # type: ignore[arg-type]
        top_n=top_n,
    )
    entries = screening.filter_universe_with_scores(filters)
    return [CompanyRowSchema.model_validate(e) for e in entries]


@router.post("/universe/filter", response_model=list[CompanyRowSchema])
def filter_universe(
    body: ScreeningFiltersSchema,
    screening: ScreeningService = Depends(get_screening_service),
) -> list[CompanyRowSchema]:
    entries = screening.filter_universe_with_scores(_to_service_filters(body))
    return [CompanyRowSchema.model_validate(e) for e in entries]


@router.get("/snapshots", response_model=list[SnapshotSummarySchema])
def list_snapshots(
    limit: int = Query(20, ge=1, le=100),
    screening: ScreeningService = Depends(get_screening_service),
) -> list[SnapshotSummarySchema]:
    summaries = screening.list_recent_screening_snapshots(limit=limit)
    return [SnapshotSummarySchema.model_validate(s) for s in summaries]


@router.post("/snapshots", response_model=SnapshotSummarySchema)
def save_snapshot(
    body: SaveSnapshotRequest,
    screening: ScreeningService = Depends(get_screening_service),
) -> SnapshotSummarySchema:
    saved = screening.save_screening_snapshot(
        _to_service_filters(body.filters),
        name=body.name,
    )
    return SnapshotSummarySchema(
        snapshot_id=saved.snapshot_id,
        name=saved.name,
        created_at=saved.created_at,
        company_count=saved.company_count,
        filters_summary=str(saved.filters),
    )


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotViewSchema)
def get_snapshot(
    snapshot_id: int,
    screening: ScreeningService = Depends(get_screening_service),
) -> SnapshotViewSchema:
    view = screening.get_screening_snapshot_view(snapshot_id)
    if view is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return SnapshotViewSchema.model_validate(view)


@router.get(
    "/snapshots/{snapshot_id}/compare",
    response_model=list[SnapshotComparisonRowSchema],
)
def compare_snapshot(
    snapshot_id: int,
    screening: ScreeningService = Depends(get_screening_service),
) -> list[SnapshotComparisonRowSchema]:
    rows = screening.compare_snapshot_to_current(
        snapshot_id,
        UniverseScreeningFilters(),
    )
    return [SnapshotComparisonRowSchema.model_validate(r) for r in rows]
