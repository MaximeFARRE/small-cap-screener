import dataclasses
import json
from collections.abc import AsyncGenerator
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sse_starlette.sse import EventSourceResponse

from api.dependencies import (
    get_company_detail_service,
    get_company_id,
    get_financial_data_service,
    get_kpi_service,
    get_peer_service,
    get_scoring_service,
    get_watchlist_service,
)
from api.schemas.company import CompanyDetailSchema, CompanyInsightsSchema, HistoricalFundamentalsSchema
from api.schemas.peers import PeerComparisonSchema
from api.schemas.refresh import CompanyRefreshResultSchema
from api.schemas.scoring import ScoreBreakdownSchema
from src.services.company_detail_service import CompanyDetailService
from src.services.financial_data_service import FinancialDataService
from src.services.kpi_snapshot_service import KpiSnapshotService
from src.services.peer_comparison_service import PeerComparisonService
from src.services.scoring_service import ScoringService
from src.services.watchlist_service import WatchlistService

router = APIRouter(prefix="/companies", tags=["companies"])


def _build_historical_schema(detail: object) -> HistoricalFundamentalsSchema:
    hf = detail.historical_fundamentals
    trends = hf.trends
    return HistoricalFundamentalsSchema(
        revenue_history=list(hf.revenue_history),
        ebitda_history=list(hf.ebitda_history),
        ebit_history=list(hf.ebit_history),
        net_income_history=list(hf.net_income_history),
        free_cash_flow_history=list(hf.free_cash_flow_history),
        net_debt_history=list(hf.net_debt_history),
        eps_history=list(hf.eps_history),
        revenue_growth_history=list(hf.revenue_growth_history),
        ebitda_growth_history=list(hf.ebitda_growth_history),
        net_income_growth_history=list(hf.net_income_growth_history),
        free_cash_flow_growth_history=list(hf.free_cash_flow_growth_history),
        ebitda_margin_history=list(hf.ebitda_margin_history),
        financial_anomalies=list(hf.financial_anomalies),
        revenue_cagr=trends.revenue_cagr,
        operating_income_cagr=trends.operating_income_cagr,
        net_income_cagr=trends.net_income_cagr,
        free_cash_flow_cagr=trends.free_cash_flow_cagr,
        revenue_direction=trends.revenue_direction,
        margin_direction=trends.margin_direction,
        net_debt_direction=trends.net_debt_direction,
    )


def _build_tearsheet_export_csv(
    detail: CompanyDetailSchema,
    score: ScoreBreakdownSchema,
    historical: HistoricalFundamentalsSchema,
) -> str:
    lines = StringIO()
    lines.write("section,metric,value\n")
    lines.write(f"profile,ticker,{detail.ticker or ''}\n")
    lines.write(f"profile,name,{detail.name}\n")
    lines.write(f"profile,sector,{detail.sector or ''}\n")
    lines.write(f"profile,country,{detail.country or ''}\n")
    lines.write(f"profile,currency,{detail.currency}\n")
    lines.write(f"profile,current_price,{detail.current_price if detail.current_price is not None else ''}\n")
    lines.write(f"profile,market_cap,{detail.market_cap if detail.market_cap is not None else ''}\n")
    lines.write(f"score,total_score,{score.total_score if score.total_score is not None else ''}\n")
    lines.write(f"score,quality,{score.quality if score.quality is not None else ''}\n")
    lines.write(f"score,value,{score.value if score.value is not None else ''}\n")
    lines.write(f"score,growth,{score.growth if score.growth is not None else ''}\n")
    lines.write(f"score,risk,{score.risk if score.risk is not None else ''}\n")

    for point in historical.revenue_history:
        lines.write(f"history,revenue_{point.fiscal_year},{point.value}\n")
    for point in historical.ebitda_history:
        lines.write(f"history,ebitda_{point.fiscal_year},{point.value}\n")
    for point in historical.net_income_history:
        lines.write(f"history,net_income_{point.fiscal_year},{point.value}\n")
    for point in historical.free_cash_flow_history:
        lines.write(f"history,free_cash_flow_{point.fiscal_year},{point.value}\n")
    for point in historical.net_debt_history:
        lines.write(f"history,net_debt_{point.fiscal_year},{point.value}\n")

    return lines.getvalue()


def _quote_csv_text(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def _build_export_filename() -> str:
    import datetime

    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d-%H%M%S")
    return f"tearsheet-{stamp}.csv"


async def _stream_universe_refresh(
    financial_data: FinancialDataService,
    kpi: KpiSnapshotService,
) -> AsyncGenerator[dict[str, str], None]:
    import asyncio
    import datetime
    from concurrent.futures import ThreadPoolExecutor

    from src.repositories import company_repository
    from src.repositories.database import get_session

    with get_session() as session:
        companies = company_repository.get_investable_universe(
            session,
            max_market_cap=financial_data.default_max_market_cap,
            min_average_daily_volume=financial_data.default_min_average_daily_volume,
            country=financial_data.default_country,
        )
        company_ids = [(c.id, c.ticker or str(c.id)) for c in companies]

    total = len(company_ids)
    yield {"event": "start", "data": json.dumps({"total": total})}

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        for idx, (company_id, ticker) in enumerate(company_ids, start=1):
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
                        "ticker": ticker,
                        **schema.model_dump(),
                    }
                ),
            }

    yield {"event": "done", "data": json.dumps({"total": total})}


@router.get("/refresh")
def refresh_companies_stream(
    financial_data: FinancialDataService = Depends(get_financial_data_service),
    kpi: KpiSnapshotService = Depends(get_kpi_service),
) -> EventSourceResponse:
    return EventSourceResponse(_stream_universe_refresh(financial_data, kpi))


@router.post("/refresh")
def refresh_companies_stream_post(
    financial_data: FinancialDataService = Depends(get_financial_data_service),
    kpi: KpiSnapshotService = Depends(get_kpi_service),
) -> EventSourceResponse:
    return EventSourceResponse(_stream_universe_refresh(financial_data, kpi))


@router.get("/{ticker}", response_model=CompanyDetailSchema)
def get_company_detail(
    company_id: int = Depends(get_company_id),
    service: CompanyDetailService = Depends(get_company_detail_service),
) -> CompanyDetailSchema:
    detail = service.get_financial_detail(company_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No detail found for company {company_id}")

    historical = _build_historical_schema(detail)

    return CompanyDetailSchema(
        company_id=detail.company_id,
        name=detail.name,
        ticker=detail.ticker,
        sector=detail.sector,
        country=detail.country,
        currency=detail.currency,
        industry=detail.industry,
        website=detail.website,
        business_summary=detail.business_summary,
        full_time_employees=detail.full_time_employees,
        city=detail.city,
        current_price=detail.current_price,
        market_cap=detail.market_cap,
        enterprise_value=detail.enterprise_value,
        forward_pe=detail.forward_pe,
        beta=detail.beta,
        average_daily_volume=detail.average_daily_volume,
        analyst_target_price=detail.analyst_target_price,
        analyst_target_upside=detail.analyst_target_upside,
        analyst_recommendation=detail.analyst_recommendation,
        analyst_count=detail.analyst_count,
        pe_ratio=detail.pe_ratio,
        pb_ratio=detail.pb_ratio,
        ev_ebitda=detail.ev_ebitda,
        fcf_yield=detail.fcf_yield,
        gross_margin=detail.gross_margin,
        operating_margin=detail.operating_margin,
        net_margin=detail.net_margin,
        roe=detail.roe,
        roic=detail.roic,
        revenue_growth=detail.revenue_growth,
        ebitda_growth=detail.ebitda_growth,
        net_debt_to_ebitda=detail.net_debt_to_ebitda,
        revenue=detail.revenue,
        ebitda=detail.ebitda,
        net_income=detail.net_income,
        free_cash_flow=detail.free_cash_flow,
        net_debt=detail.net_debt,
        latest_dividend_yield=detail.latest_dividend_yield,
        latest_dividend_rate=detail.latest_dividend_rate,
        data_quality_score=detail.data_quality_score,
        last_refresh_at=detail.last_refresh_at,
        snapshot_date=detail.snapshot_date,
        historical_fundamentals=historical,
        management_team=[dataclasses.asdict(e) for e in detail.management_team],  # type: ignore[arg-type]
        major_holders=[dataclasses.asdict(h) for h in detail.major_holders],  # type: ignore[arg-type]
        institutional_holders=[dataclasses.asdict(h) for h in detail.institutional_holders],  # type: ignore[arg-type]
        insider_activity=[dataclasses.asdict(t) for t in detail.insider_activity],  # type: ignore[arg-type]
    )


@router.get("/{ticker}/score", response_model=ScoreBreakdownSchema)
def get_company_score(
    company_id: int = Depends(get_company_id),
    watchlist: WatchlistService = Depends(get_watchlist_service),
) -> ScoreBreakdownSchema:
    analyst_detail = watchlist.get_company_analyst_detail(company_id)
    explanation = analyst_detail.score_explanation
    return ScoreBreakdownSchema(
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
    )


@router.get("/{ticker}/peers", response_model=PeerComparisonSchema)
def get_company_peers(
    company_id: int = Depends(get_company_id),
    peer_service: PeerComparisonService = Depends(get_peer_service),
) -> PeerComparisonSchema:
    data = peer_service.get_company_peer_comparison(company_id)
    return PeerComparisonSchema.model_validate(data)


@router.get("/{ticker}/insights", response_model=CompanyInsightsSchema)
def get_company_insights(
    company_id: int = Depends(get_company_id),
    detail_service: CompanyDetailService = Depends(get_company_detail_service),
    watchlist: WatchlistService = Depends(get_watchlist_service),
    peer_service: PeerComparisonService = Depends(get_peer_service),
    scoring_service: ScoringService = Depends(get_scoring_service),
) -> CompanyInsightsSchema:
    detail = detail_service.get_financial_detail(company_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No detail found for company {company_id}")
    analyst_detail = watchlist.get_company_analyst_detail(company_id)
    peers = peer_service.get_company_peer_comparison(company_id)
    metric_by_key = {metric.key: metric for metric in peers.metrics}
    ev_peer_median = metric_by_key.get("ev_ebitda").sector_median if metric_by_key.get("ev_ebitda") else None
    pe_peer_median = metric_by_key.get("pe_ratio").sector_median if metric_by_key.get("pe_ratio") else None

    valuation = detail_service.compute_valuation_summary(detail, ev_peer_median, pe_peer_median)
    quality_risk = detail_service.compute_quality_metrics(detail)
    business = detail_service.compute_business_summary(detail)
    capital_allocation = detail_service.compute_allocation_metrics(detail)
    data_quality = detail_service.compute_data_quality_summary(detail)
    analysis = scoring_service.describe_company(
        score_explanation=analyst_detail.score_explanation,
        metrics={
            "revenue_growth": detail.revenue_growth,
            "ebitda_growth": detail.ebitda_growth,
            "net_debt_to_ebitda": detail.net_debt_to_ebitda,
            "ebitda_margin": detail.operating_margin,
            "interest_coverage": None,
        },
    )
    return CompanyInsightsSchema(
        analysis=analysis,  # type: ignore[arg-type]
        valuation=valuation,  # type: ignore[arg-type]
        quality_risk=quality_risk,  # type: ignore[arg-type]
        business=business,  # type: ignore[arg-type]
        capital_allocation=capital_allocation,  # type: ignore[arg-type]
        data_quality={
            "data_quality_score": data_quality.data_quality_score,
            "missing_data": list(data_quality.missing_data),
            "warnings": list(data_quality.warnings),
        },
    )


@router.get("/{ticker}/export")
def export_company_tearsheet_csv(
    company_id: int = Depends(get_company_id),
    detail_service: CompanyDetailService = Depends(get_company_detail_service),
    watchlist: WatchlistService = Depends(get_watchlist_service),
) -> Response:
    detail = detail_service.get_financial_detail(company_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"No detail found for company {company_id}")

    historical = _build_historical_schema(detail)
    analyst_detail = watchlist.get_company_analyst_detail(company_id)
    explanation = analyst_detail.score_explanation
    score = ScoreBreakdownSchema(
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
    )
    detail_schema = CompanyDetailSchema(
        company_id=detail.company_id,
        name=detail.name,
        ticker=detail.ticker,
        sector=detail.sector,
        country=detail.country,
        currency=detail.currency,
        industry=detail.industry,
        website=detail.website,
        business_summary=detail.business_summary,
        full_time_employees=detail.full_time_employees,
        city=detail.city,
        current_price=detail.current_price,
        market_cap=detail.market_cap,
        enterprise_value=detail.enterprise_value,
        forward_pe=detail.forward_pe,
        beta=detail.beta,
        average_daily_volume=detail.average_daily_volume,
        analyst_target_price=detail.analyst_target_price,
        analyst_target_upside=detail.analyst_target_upside,
        analyst_recommendation=detail.analyst_recommendation,
        analyst_count=detail.analyst_count,
        pe_ratio=detail.pe_ratio,
        pb_ratio=detail.pb_ratio,
        ev_ebitda=detail.ev_ebitda,
        fcf_yield=detail.fcf_yield,
        gross_margin=detail.gross_margin,
        operating_margin=detail.operating_margin,
        net_margin=detail.net_margin,
        roe=detail.roe,
        roic=detail.roic,
        revenue_growth=detail.revenue_growth,
        ebitda_growth=detail.ebitda_growth,
        net_debt_to_ebitda=detail.net_debt_to_ebitda,
        revenue=detail.revenue,
        ebitda=detail.ebitda,
        net_income=detail.net_income,
        free_cash_flow=detail.free_cash_flow,
        net_debt=detail.net_debt,
        latest_dividend_yield=detail.latest_dividend_yield,
        latest_dividend_rate=detail.latest_dividend_rate,
        data_quality_score=detail.data_quality_score,
        last_refresh_at=detail.last_refresh_at,
        snapshot_date=detail.snapshot_date,
        historical_fundamentals=historical,
        management_team=[dataclasses.asdict(e) for e in detail.management_team],  # type: ignore[arg-type]
        major_holders=[dataclasses.asdict(h) for h in detail.major_holders],  # type: ignore[arg-type]
        institutional_holders=[dataclasses.asdict(h) for h in detail.institutional_holders],  # type: ignore[arg-type]
        insider_activity=[dataclasses.asdict(t) for t in detail.insider_activity],  # type: ignore[arg-type]
    )
    csv_content = _build_tearsheet_export_csv(detail_schema, score, historical)
    filename = _build_export_filename()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={_quote_csv_text(filename)}",
        },
    )
