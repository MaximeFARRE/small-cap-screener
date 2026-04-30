from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class ScreeningFiltersSchema(BaseModel):
    sector: str | None = None
    min_total_score: float | None = None
    min_data_quality_score: float | None = None
    max_pe: float | None = None
    min_growth: float | None = None
    min_margin: float | None = None
    min_market_cap: float | None = None
    max_market_cap: float | None = None
    stale_only: bool = False
    scored_only: bool = False
    watchlist_scope: str = "all"
    watchlist_status: str | None = None
    include_excluded: bool = False
    top_n: int | None = None
    sort_by: str = "rank"
    descending: bool = False


class CompanyRowSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    ticker: str | None
    name: str
    sector: str | None
    market: str | None
    country: str | None
    total_score: float | None
    quality_score: float | None
    value_score: float | None
    growth_score: float | None
    risk_score: float | None
    rank: int | None
    sector_rank: int | None
    pe_ratio: float | None
    ev_ebitda: float | None
    fcf_yield: float | None
    revenue_growth: float | None
    ebitda_margin: float | None
    operating_margin: float | None
    roic: float | None
    roe: float | None
    net_debt_to_ebitda: float | None
    market_cap: float | None
    data_quality_score: float | None
    last_universe_refresh_at: datetime | None
    snapshot_date: date | None


class SnapshotSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int
    name: str
    created_at: datetime
    company_count: int
    filters_summary: str


class SnapshotRowSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int | None
    ticker: str | None
    name: str
    sector: str | None
    total_score: float | None
    quality_score: float | None
    value_score: float | None
    growth_score: float | None
    risk_score: float | None
    rank: int | None
    sector_rank: int | None


class SnapshotViewSchema(BaseModel):
    summary: SnapshotSummarySchema
    rows: list[SnapshotRowSchema]


class SnapshotComparisonRowSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int | None
    ticker: str | None
    name: str
    sector: str | None
    snapshot_rank: int | None
    current_rank: int | None
    rank_change: int | None
    snapshot_total_score: float | None
    current_total_score: float | None
    total_score_change: float | None


class SaveSnapshotRequest(BaseModel):
    name: str = "screening snapshot"
    filters: ScreeningFiltersSchema = ScreeningFiltersSchema()
