from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import get_company_id, get_watchlist_service
from api.schemas.watchlist import (
    AddToWatchlistRequest,
    AnalystMemoSchema,
    CompanyAnalystDetailSchema,
    UpdateNextReviewRequest,
    UpdateStatusRequest,
    WatchlistWorkflowEntrySchema,
)
from src.services.watchlist_service import AnalystMemo, WatchlistService

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistWorkflowEntrySchema])
def list_watchlist(
    service: WatchlistService = Depends(get_watchlist_service),
) -> list[WatchlistWorkflowEntrySchema]:
    entries = service.list_watchlist_workflow()
    return [WatchlistWorkflowEntrySchema.model_validate(e) for e in entries]


@router.get("/{ticker}/detail", response_model=CompanyAnalystDetailSchema)
def get_analyst_detail(
    company_id: int = Depends(get_company_id),
    service: WatchlistService = Depends(get_watchlist_service),
) -> CompanyAnalystDetailSchema:
    detail = service.get_company_analyst_detail(company_id)
    explanation = detail.score_explanation
    from api.schemas.scoring import ScoreBreakdownSchema

    return CompanyAnalystDetailSchema(
        watchlist_status=detail.watchlist_status,
        watchlist_notes=detail.watchlist_notes,
        watchlist_is_excluded=detail.watchlist_is_excluded,
        next_review_at=detail.next_review_at,
        analyst_memo=AnalystMemoSchema.model_validate(detail.analyst_memo),
        quality_score=detail.quality_score,
        value_score=detail.value_score,
        growth_score=detail.growth_score,
        risk_score=detail.risk_score,
        total_score=detail.total_score,
        rank=detail.rank,
        sector_rank=detail.sector_rank,
        score_explanation=ScoreBreakdownSchema(
            total_score=explanation.total_score,
            quality=explanation.quality,
            value=explanation.value,
            growth=explanation.growth,
            risk=explanation.risk,
            weights=list(explanation.weights),  # type: ignore[arg-type]
            category_contributions=list(explanation.category_contributions),  # type: ignore[arg-type]
            positive_drivers=list(explanation.positive_drivers),  # type: ignore[arg-type]
            negative_drivers=list(explanation.negative_drivers),  # type: ignore[arg-type]
            strengths=list(explanation.strengths),
            weaknesses=list(explanation.weaknesses),
            summary=explanation.summary,
        ),
    )


@router.post("/{ticker}", response_model=WatchlistWorkflowEntrySchema)
def add_to_watchlist(
    ticker: str,
    body: AddToWatchlistRequest,
    company_id: int = Depends(get_company_id),
    service: WatchlistService = Depends(get_watchlist_service),
) -> WatchlistWorkflowEntrySchema:
    entry = service.add_company(company_id, notes=body.notes)
    if entry is None:
        raise HTTPException(status_code=409, detail=f"{ticker} is already in watchlist")
    entries = service.list_watchlist_workflow()
    match = next((e for e in entries if e.company_id == company_id), None)
    if match is None:
        raise HTTPException(status_code=500, detail="Failed to retrieve watchlist entry")
    return WatchlistWorkflowEntrySchema.model_validate(match)


@router.delete("/{ticker}", status_code=204)
def remove_from_watchlist(
    ticker: str,
    company_id: int = Depends(get_company_id),
    service: WatchlistService = Depends(get_watchlist_service),
) -> None:
    removed = service.remove_company(company_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"{ticker} is not in watchlist")


@router.patch("/{ticker}/memo", response_model=AnalystMemoSchema)
def update_memo(
    ticker: str,
    body: AnalystMemoSchema,
    company_id: int = Depends(get_company_id),
    service: WatchlistService = Depends(get_watchlist_service),
) -> AnalystMemoSchema:
    memo = AnalystMemo(
        investment_thesis=body.investment_thesis,
        key_risks=body.key_risks,
        catalysts=body.catalysts,
        valuation_notes=body.valuation_notes,
        next_action=body.next_action,
    )
    entry = service.update_company_memo(company_id, memo)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"{ticker} is not in watchlist")
    return body


@router.patch("/{ticker}/status", status_code=204)
def update_status(
    ticker: str,
    body: UpdateStatusRequest,
    company_id: int = Depends(get_company_id),
    service: WatchlistService = Depends(get_watchlist_service),
) -> None:
    entry = service.update_company_status(company_id, body.status)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"{ticker} is not in watchlist")


@router.patch("/{ticker}/next-review", status_code=204)
def update_next_review(
    ticker: str,
    body: UpdateNextReviewRequest,
    company_id: int = Depends(get_company_id),
    service: WatchlistService = Depends(get_watchlist_service),
) -> None:
    entry = service.update_company_next_review(company_id, body.next_review_at)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"{ticker} is not in watchlist")
