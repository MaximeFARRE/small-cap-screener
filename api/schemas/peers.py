from pydantic import BaseModel, ConfigDict


class PeerMetricSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    company_value: float | None
    sector_median: float | None
    percentile_rank: float | None
    premium_discount_vs_peers: float | None
    is_lower_better: bool


class PeerCompanyRowSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    ticker: str | None
    name: str
    sector_rank: int | None
    total_score: float | None
    market_cap: float | None
    ev_ebitda: float | None
    pe_ratio: float | None
    fcf_yield: float | None
    revenue_growth: float | None
    ebitda_margin: float | None
    roic: float | None
    roe: float | None
    net_debt_to_ebitda: float | None
    peer_rank: int | None
    score_percentile: float | None


class PeerAnalystAssessmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cheaper_than_peers: bool | None
    higher_quality_than_peers: bool | None
    growth_premium_justified: bool | None
    balance_sheet_weaker: bool | None


class PeerComparisonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sector: str | None
    market: str | None
    market_cap_bucket: str | None
    company_sector_rank: int | None
    sector_company_count: int
    sector_scored_count: int
    peer_count: int
    metrics: list[PeerMetricSchema]
    peer_rows: list[PeerCompanyRowSchema]
    analyst_assessment: PeerAnalystAssessmentSchema
