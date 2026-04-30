from pydantic import BaseModel, ConfigDict


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
