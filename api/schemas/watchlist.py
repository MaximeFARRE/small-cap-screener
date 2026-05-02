from datetime import datetime

from pydantic import BaseModel, ConfigDict

from api.schemas.scoring import ScoreBreakdownSchema


class AnalystMemoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investment_thesis: str | None = None
    key_risks: str | None = None
    catalysts: str | None = None
    valuation_notes: str | None = None
    next_action: str | None = None


class WatchlistWorkflowEntrySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    ticker: str | None
    name: str
    status: str
    notes: str | None
    memo_summary: str | None
    is_excluded: bool
    total_score: float | None
    rank: int | None
    sector_rank: int | None
    data_quality_score: float | None
    last_universe_refresh_at: datetime | None
    next_review_at: datetime | None


class CompanyAnalystDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    watchlist_status: str | None
    watchlist_notes: str | None
    watchlist_is_excluded: bool
    next_review_at: datetime | None
    analyst_memo: AnalystMemoSchema
    quality_score: float | None
    value_score: float | None
    growth_score: float | None
    risk_score: float | None
    total_score: float | None
    rank: int | None
    sector_rank: int | None
    score_explanation: ScoreBreakdownSchema


class AddToWatchlistRequest(BaseModel):
    notes: str | None = None


class UpdateStatusRequest(BaseModel):
    status: str


class UpdateNextReviewRequest(BaseModel):
    next_review_at: datetime | None
