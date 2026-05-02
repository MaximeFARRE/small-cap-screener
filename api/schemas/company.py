from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class HistoricalMetricPointSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fiscal_year: int
    period_type: str
    value: float


class FinancialAnomalySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    metric_key: str
    fiscal_year: int
    kind: str


class HistoricalFundamentalsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revenue_history: list[HistoricalMetricPointSchema]
    ebitda_history: list[HistoricalMetricPointSchema]
    ebit_history: list[HistoricalMetricPointSchema]
    net_income_history: list[HistoricalMetricPointSchema]
    free_cash_flow_history: list[HistoricalMetricPointSchema]
    net_debt_history: list[HistoricalMetricPointSchema]
    eps_history: list[HistoricalMetricPointSchema]
    capex_history: list[HistoricalMetricPointSchema]
    capex_to_revenue_history: list[HistoricalMetricPointSchema]
    working_capital_history: list[HistoricalMetricPointSchema]
    operating_cash_flow_history: list[HistoricalMetricPointSchema]
    asset_turnover_history: list[HistoricalMetricPointSchema]
    equity_multiplier_history: list[HistoricalMetricPointSchema]
    capex_growth_history: list[HistoricalMetricPointSchema]
    working_capital_growth_history: list[HistoricalMetricPointSchema]
    revenue_growth_history: list[HistoricalMetricPointSchema]
    ebitda_growth_history: list[HistoricalMetricPointSchema]
    net_income_growth_history: list[HistoricalMetricPointSchema]
    free_cash_flow_growth_history: list[HistoricalMetricPointSchema]
    ebitda_margin_history: list[HistoricalMetricPointSchema]
    financial_anomalies: list[FinancialAnomalySchema]
    revenue_cagr: float | None = None
    operating_income_cagr: float | None = None
    net_income_cagr: float | None = None
    free_cash_flow_cagr: float | None = None
    revenue_direction: str | None = None
    margin_direction: str | None = None
    net_debt_direction: str | None = None


class ExecutiveSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    title: str | None
    age: int | None
    total_pay: float | None


class HolderSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    holder_name: str
    holder_type: str
    weight: float | None
    shares: float | None
    market_value: float | None
    date_reported: date | None


class InsiderTransactionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    insider_name: str | None
    relation: str | None
    transaction_text: str | None
    ownership: str | None
    shares: float | None
    market_value: float | None
    start_date: date | None


class CompanyDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: int
    name: str
    ticker: str | None
    sector: str | None
    country: str | None
    currency: str
    industry: str | None
    website: str | None
    business_summary: str | None
    full_time_employees: int | None
    city: str | None
    # Valuation
    current_price: float | None
    market_cap: float | None
    enterprise_value: float | None
    forward_pe: float | None
    beta: float | None
    average_daily_volume: float | None
    # Analyst
    analyst_target_price: float | None
    analyst_target_upside: float | None
    analyst_recommendation: str | None
    analyst_count: int | None
    # Latest ratios
    pe_ratio: float | None
    pb_ratio: float | None
    ev_ebitda: float | None
    fcf_yield: float | None
    gross_margin: float | None
    operating_margin: float | None
    net_margin: float | None
    roe: float | None
    roic: float | None
    revenue_growth: float | None
    ebitda_growth: float | None
    net_debt_to_ebitda: float | None
    # Income statement snapshot
    revenue: float | None
    ebitda: float | None
    net_income: float | None
    free_cash_flow: float | None
    net_debt: float | None
    # Dividends
    latest_dividend_yield: float | None
    latest_dividend_rate: float | None
    # Meta
    data_quality_score: float | None
    last_refresh_at: datetime | None
    snapshot_date: date | None
    # Nested
    historical_fundamentals: HistoricalFundamentalsSchema
    management_team: list[ExecutiveSchema]
    major_holders: list[HolderSchema]
    institutional_holders: list[HolderSchema]
    insider_activity: list[InsiderTransactionSchema]


class CompanyAnalysisSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quality: float | None
    value: float | None
    growth: float | None
    risk: float | None
    strengths: list[str]
    weaknesses: list[str]
    red_flags: list[str]
    trend: str
    verdict: str
    revenue_trend: str
    margin_trend: str
    debt_trend: str
    cash_conversion_ratio: float | None
    revenue_cagr_3y: float | None
    ebitda_cagr_3y: float | None
    net_income_growth: float | None
    fcf_growth: float | None


class ValuationSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ev_ebitda: float | None
    pe_ratio: float | None
    fcf_yield: float | None
    valuation_view: str
    valuation_verdict: str


class QualityRiskSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profitability_score: float
    balance_sheet_score: float
    cash_flow_quality_score: float
    volatility_score: float


class BusinessSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sector: str | None
    industry: str | None
    business_model: str | None
    market_cap: float | None
    enterprise_value: float | None
    analyst_target_price: float | None
    analyst_target_upside: float | None
    analyst_recommendation: str | None
    analyst_count: int | None


class CapitalAllocationSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fcf_trend: str
    capex_trend: str
    debt_trend: str
    reinvestment_vs_returns: str


class DataQualitySummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    data_quality_score: float | None
    years_available: int
    missing_data: list[str]
    warnings: list[str]


class MomentumSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    performance_1m: float | None
    performance_6m: float | None
    performance_12m: float | None
    pct_vs_52w_high: float | None
    pct_vs_52w_low: float | None


class OwnershipHolderSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    holder_name: str
    weight: float | None


class OwnershipSummarySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    institutional_pct: float | None
    insiders_pct: float | None
    top_holders: list[OwnershipHolderSummarySchema]


class CompanyInsightsSchema(BaseModel):
    analysis: CompanyAnalysisSchema
    valuation: ValuationSummarySchema
    quality_risk: QualityRiskSummarySchema
    business: BusinessSummarySchema
    momentum: MomentumSummarySchema
    ownership: OwnershipSummarySchema
    capital_allocation: CapitalAllocationSummarySchema
    data_quality: DataQualitySummarySchema
