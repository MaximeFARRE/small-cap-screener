import json
from asyncio import Queue, get_running_loop
from collections.abc import AsyncGenerator
from functools import partial

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

from api.dependencies import (
    get_company_id,
    get_financial_data_service,
    get_kpi_service,
    get_screening_service,
    get_ticker_ingestion_service,
    get_universe_discovery_service,
    get_universe_service,
)
from api.schemas.refresh import (
    CompanyRefreshResultSchema,
    ImportUniverseRequestSchema,
    ImportUniverseResultSchema,
    TickerIngestionRequestSchema,
    TickerIngestionResultSchema,
)
from src.repositories import company_repository
from src.repositories.database import get_session
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.screening_service import ScreeningService
from src.services.ticker_ingestion_service import TickerIngestionService
from src.services.universe_discovery_service import UniverseDiscoveryService
from src.services.universe_service import UniverseService

router = APIRouter(prefix="/refresh", tags=["data_refresh"])


def _queue_event(
    *,
    loop,
    queue: Queue[dict[str, str] | None],
    event_name: str,
    payload: dict,
) -> None:
    loop.call_soon_threadsafe(
        queue.put_nowait,
        {"event": event_name, "data": json.dumps(payload)},
    )


def _stream_import_france_universe(
    *,
    loop,
    queue: Queue[dict[str, str] | None],
    universe_service: UniverseService,
    discovery_service: UniverseDiscoveryService,
    enrich: bool,
    pacing_seconds: float,
    batch_size: int,
) -> None:
    try:
        _queue_event(
            loop=loop,
            queue=queue,
            event_name="start",
            payload={
                "enrich": enrich,
                "pacing_seconds": pacing_seconds,
                "batch_size": batch_size,
            },
        )

        import_result = universe_service.import_euronext_france_universe()
        enrichment_total = len(import_result.upserted_company_ids) if enrich else 0
        _queue_event(
            loop=loop,
            queue=queue,
            event_name="discovery",
            payload={
                "discovered_count": import_result.discovered_count,
                "upserted_count": import_result.upserted_count,
                "enrichment_total": enrichment_total,
            },
        )

        enrichment_succeeded = 0
        enrichment_failed = 0
        enrichment_skipped = 0

        if enrich and enrichment_total > 0:

            def progress_callback(payload: dict) -> None:
                _queue_event(
                    loop=loop,
                    queue=queue,
                    event_name="progress",
                    payload=payload,
                )

            enrichment_result = discovery_service.refresh_companies_by_ids(
                company_id_list=import_result.upserted_company_ids,
                pacing_seconds=pacing_seconds,
                batch_size=batch_size,
                skip_recently_refreshed=False,
                progress_callback=progress_callback,
            )
            enrichment_succeeded = enrichment_result.succeeded
            enrichment_failed = enrichment_result.failed
            enrichment_skipped = enrichment_result.skipped

        _queue_event(
            loop=loop,
            queue=queue,
            event_name="done",
            payload={
                "discovered_count": import_result.discovered_count,
                "upserted_count": import_result.upserted_count,
                "enrichment_total": enrichment_total,
                "enrichment_succeeded": enrichment_succeeded,
                "enrichment_failed": enrichment_failed,
                "enrichment_skipped": enrichment_skipped,
            },
        )
    except Exception as exc:  # noqa: BLE001
        _queue_event(
            loop=loop,
            queue=queue,
            event_name="error",
            payload={"message": str(exc)},
        )
    finally:
        loop.call_soon_threadsafe(queue.put_nowait, None)


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


@router.post("/ingest", response_model=TickerIngestionResultSchema)
def ingest_ticker(
    body: TickerIngestionRequestSchema,
    ingestion_service: TickerIngestionService = Depends(get_ticker_ingestion_service),
) -> TickerIngestionResultSchema:
    result = ingestion_service.ingest_identifier(body.identifier)
    return TickerIngestionResultSchema.model_validate(result)


@router.post("/universe/import-france", response_model=ImportUniverseResultSchema)
def import_france_universe(
    body: ImportUniverseRequestSchema,
    universe_service: UniverseService = Depends(get_universe_service),
    discovery_service: UniverseDiscoveryService = Depends(get_universe_discovery_service),
) -> ImportUniverseResultSchema:
    import_result = universe_service.import_euronext_france_universe()
    if not body.enrich:
        return ImportUniverseResultSchema(
            discovered_count=import_result.discovered_count,
            upserted_count=import_result.upserted_count,
            enrichment_total=0,
            enrichment_succeeded=0,
            enrichment_failed=0,
            enrichment_skipped=0,
        )

    enrichment_result = discovery_service.refresh_companies_by_ids(
        company_id_list=import_result.upserted_company_ids,
        pacing_seconds=body.pacing_seconds,
        batch_size=body.batch_size,
        skip_recently_refreshed=False,
    )
    return ImportUniverseResultSchema(
        discovered_count=import_result.discovered_count,
        upserted_count=import_result.upserted_count,
        enrichment_total=enrichment_result.total,
        enrichment_succeeded=enrichment_result.succeeded,
        enrichment_failed=enrichment_result.failed,
        enrichment_skipped=enrichment_result.skipped,
    )


@router.get("/universe/import-france/stream")
async def import_france_universe_stream(
    enrich: bool = Query(default=True),
    pacing_seconds: float = Query(default=0.0, ge=0.0),
    batch_size: int = Query(default=25, ge=1),
    universe_service: UniverseService = Depends(get_universe_service),
    discovery_service: UniverseDiscoveryService = Depends(get_universe_discovery_service),
) -> EventSourceResponse:
    async def _event_generator() -> AsyncGenerator[dict[str, str], None]:
        loop = get_running_loop()
        event_queue: Queue[dict[str, str] | None] = Queue()
        worker = loop.run_in_executor(
            None,
            partial(
                _stream_import_france_universe,
                loop=loop,
                queue=event_queue,
                universe_service=universe_service,
                discovery_service=discovery_service,
                enrich=enrich,
                pacing_seconds=pacing_seconds,
                batch_size=batch_size,
            ),
        )

        while True:
            event = await event_queue.get()
            if event is None:
                break
            yield event

        await worker

    return EventSourceResponse(_event_generator())


@router.post("/{ticker}", response_model=CompanyRefreshResultSchema)
def refresh_company(
    company_id: int = Depends(get_company_id),
    financial_data: FinancialDataService = Depends(get_financial_data_service),
    kpi: KpiSnapshotService = Depends(get_kpi_service),
) -> CompanyRefreshResultSchema:
    result = financial_data.refresh_company_data(company_id)
    if result.success:
        import datetime

        kpi.compute_and_upsert_for_company(company_id, datetime.date.today())
    return CompanyRefreshResultSchema.model_validate(result)
