from pydantic import BaseModel, ConfigDict, Field


class CompanyRefreshResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    ticker: str
    success: bool
    prices_added: int
    statements_added: int
    error: str | None
    error_kind: str | None
    warnings: list[str]
    provider_used: str | None


class TickerIngestionRequestSchema(BaseModel):
    identifier: str


class TickerIngestionResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    success: bool
    resolved_ticker: str | None = None
    company_id: int | None = None
    created: bool = False
    kpi_snapshot_id: int | None = None
    error: str | None = None
    error_kind: str | None = None
    stage: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ImportUniverseRequestSchema(BaseModel):
    enrich: bool = True
    pacing_seconds: float = 0.0
    batch_size: int = 25


class ImportUniverseResultSchema(BaseModel):
    discovered_count: int
    upserted_count: int
    enrichment_total: int
    enrichment_succeeded: int
    enrichment_failed: int
    enrichment_skipped: int
