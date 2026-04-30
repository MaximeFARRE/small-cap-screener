import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from api.dependencies import (
    get_company_id,
    get_financial_data_service,
    get_kpi_service,
    get_screening_service,
)
from api.schemas.refresh import CompanyRefreshResultSchema
from src.repositories import company_repository
from src.repositories.database import get_session
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.screening_service import ScreeningService

router = APIRouter(prefix="/refresh", tags=["data_refresh"])


@router.post("/{ticker}", response_model=CompanyRefreshResultSchema)
def refresh_company(
    ticker: str,
    financial_data: FinancialDataService = Depends(get_financial_data_service),
    kpi: KpiSnapshotService = Depends(get_kpi_service),
) -> CompanyRefreshResultSchema:
    company_id = get_company_id(ticker)
    result = financial_data.refresh_company_data(company_id)
    if result.success:
        import datetime

        kpi.compute_and_upsert_for_company(company_id, datetime.date.today())
    return CompanyRefreshResultSchema.model_validate(result)


@router.post("/universe/stream")
def refresh_universe_stream(
    financial_data: FinancialDataService = Depends(get_financial_data_service),
    kpi: KpiSnapshotService = Depends(get_kpi_service),
    screening: ScreeningService = Depends(get_screening_service),
) -> EventSourceResponse:
    """Stream per-company refresh progress via Server-Sent Events."""

    async def _event_generator() -> AsyncGenerator[dict[str, str], None]:
        import asyncio
        import datetime
        from concurrent.futures import ThreadPoolExecutor

        with get_session() as session:
            companies = company_repository.get_investable_universe(
                session,
                max_market_cap=financial_data.default_max_market_cap,
                min_average_daily_volume=financial_data.default_min_average_daily_volume,
                country=financial_data.default_country,
            )
            company_ids = [(c.id, c.ticker or c.id) for c in companies]

        total = len(company_ids)
        yield {
            "event": "start",
            "data": json.dumps({"total": total}),
        }

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            for idx, (company_id, _ticker) in enumerate(company_ids, start=1):
                result = await loop.run_in_executor(
                    executor,
                    financial_data.refresh_company_data,
                    company_id,
                )
                if result.success:
                    await loop.run_in_executor(
                        executor,
                        kpi.compute_and_upsert_for_company,
                        company_id,
                        datetime.date.today(),
                    )

                schema = CompanyRefreshResultSchema.model_validate(result)
                yield {
                    "event": "progress",
                    "data": json.dumps(
                        {
                            "index": idx,
                            "total": total,
                            **schema.model_dump(),
                        }
                    ),
                }

        yield {"event": "done", "data": json.dumps({"total": total})}

    return EventSourceResponse(_event_generator())
