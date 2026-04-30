from pydantic import BaseModel, ConfigDict


class ScoreMoverSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int | None
    ticker: str | None
    name: str
    sector: str | None
    snapshot_total_score: float | None
    current_total_score: float | None
    total_score_change: float | None
    snapshot_rank: int | None
    current_rank: int | None


class TopCompanySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    ticker: str | None
    name: str
    sector: str | None
    total_score: float | None
    quality_score: float | None
    value_score: float | None
    rank: int | None


class SignalsSchema(BaseModel):
    movers_up: list[ScoreMoverSchema]
    movers_down: list[ScoreMoverSchema]
    top_quality: list[TopCompanySchema]
    top_value: list[TopCompanySchema]
    watchlist_alerts: list[ScoreMoverSchema]
    snapshot_name: str | None
    has_snapshot: bool
