import dataclasses

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import (
    get_company_detail_service,
    get_company_id,
    get_peer_service,
    get_watchlist_service,
)
from api.schemas.company import CompanyDetailSchema, HistoricalFundamentalsSchema
from api.schemas.peers import PeerComparisonSchema
from api.schemas.scoring import ScoreBreakdownSchema
from src.services.company_detail_service import CompanyDetailService
from src.services.peer_comparison_service import PeerComparisonService
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
        revenue_cagr=trends.revenue_cagr,
        operating_income_cagr=trends.operating_income_cagr,
        net_income_cagr=trends.net_income_cagr,
        free_cash_flow_cagr=trends.free_cash_flow_cagr,
        revenue_direction=trends.revenue_direction,
        margin_direction=trends.margin_direction,
        net_debt_direction=trends.net_debt_direction,
    )


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
