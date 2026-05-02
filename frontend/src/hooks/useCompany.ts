import { useQuery } from "@tanstack/react-query";
import { ApiError, api } from "@/lib/api";

export interface HistoricalMetricPoint {
  fiscal_year: number;
  period_type: string;
  value: number;
}

export interface FinancialAnomaly {
  metric_key: string;
  fiscal_year: number;
  kind: string;
}

export interface HistoricalFundamentals {
  revenue_history: HistoricalMetricPoint[];
  ebitda_history: HistoricalMetricPoint[];
  ebit_history: HistoricalMetricPoint[];
  net_income_history: HistoricalMetricPoint[];
  free_cash_flow_history: HistoricalMetricPoint[];
  net_debt_history: HistoricalMetricPoint[];
  eps_history: HistoricalMetricPoint[];
  revenue_growth_history: HistoricalMetricPoint[];
  ebitda_growth_history: HistoricalMetricPoint[];
  net_income_growth_history: HistoricalMetricPoint[];
  free_cash_flow_growth_history: HistoricalMetricPoint[];
  ebitda_margin_history: HistoricalMetricPoint[];
  financial_anomalies: FinancialAnomaly[];
  revenue_cagr: number | null;
  operating_income_cagr: number | null;
  net_income_cagr: number | null;
  free_cash_flow_cagr: number | null;
  revenue_direction: string | null;
  margin_direction: string | null;
  net_debt_direction: string | null;
}

export interface CompanyDetail {
  company_id: number;
  name: string;
  ticker: string | null;
  sector: string | null;
  country: string | null;
  currency: string;
  industry: string | null;
  website: string | null;
  business_summary: string | null;
  full_time_employees: number | null;
  city: string | null;
  current_price: number | null;
  market_cap: number | null;
  enterprise_value: number | null;
  forward_pe: number | null;
  beta: number | null;
  average_daily_volume: number | null;
  analyst_target_price: number | null;
  analyst_target_upside: number | null;
  analyst_recommendation: string | null;
  analyst_count: number | null;
  pe_ratio: number | null;
  pb_ratio: number | null;
  ev_ebitda: number | null;
  fcf_yield: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  roe: number | null;
  roic: number | null;
  revenue_growth: number | null;
  ebitda_growth: number | null;
  net_debt_to_ebitda: number | null;
  revenue: number | null;
  ebitda: number | null;
  net_income: number | null;
  free_cash_flow: number | null;
  net_debt: number | null;
  latest_dividend_yield: number | null;
  latest_dividend_rate: number | null;
  data_quality_score: number | null;
  last_refresh_at: string | null;
  snapshot_date: string | null;
  historical_fundamentals: HistoricalFundamentals;
}

export interface ScoreWeightEntry {
  category: string;
  weight: number;
}

export interface ScoreCategoryContribution {
  category: string;
  sub_score: number;
  weight: number;
  weighted_points: number;
}

export interface ScoreMetricDriver {
  category: string;
  metric: string;
  raw_value: number;
  metric_score: number;
  weighted_points: number;
  impact_points: number;
}

export interface CompanyScore {
  total_score: number | null;
  quality: number | null;
  value: number | null;
  growth: number | null;
  risk: number | null;
  weights: ScoreWeightEntry[];
  category_contributions: ScoreCategoryContribution[];
  positive_drivers: ScoreMetricDriver[];
  negative_drivers: ScoreMetricDriver[];
  strengths: string[];
  weaknesses: string[];
  summary: string;
}

export interface PeerMetric {
  key: string;
  label: string;
  company_value: number | null;
  sector_median: number | null;
  percentile_rank: number | null;
  premium_discount_vs_peers: number | null;
  is_lower_better: boolean;
}

export interface PeerCompanyRow {
  company_id: number;
  ticker: string | null;
  name: string;
  sector_rank: number | null;
  total_score: number | null;
  market_cap: number | null;
  ev_ebitda: number | null;
  pe_ratio: number | null;
  fcf_yield: number | null;
  revenue_growth: number | null;
  ebitda_margin: number | null;
  roic: number | null;
  roe: number | null;
  net_debt_to_ebitda: number | null;
  peer_rank: number | null;
  score_percentile: number | null;
}

export interface PeerComparison {
  sector: string | null;
  market: string | null;
  market_cap_bucket: string | null;
  company_sector_rank: number | null;
  sector_company_count: number;
  sector_scored_count: number;
  peer_count: number;
  metrics: PeerMetric[];
  peer_rows: PeerCompanyRow[];
}

export interface AnalysisSummary {
  quality: number | null;
  value: number | null;
  growth: number | null;
  risk: number | null;
  strengths: string[];
  weaknesses: string[];
  red_flags: string[];
  trend: string;
  verdict: string;
  revenue_trend: string;
  margin_trend: string;
  debt_trend: string;
  cash_conversion_ratio: number | null;
  revenue_cagr_3y: number | null;
  ebitda_cagr_3y: number | null;
  net_income_growth: number | null;
  fcf_growth: number | null;
}

export interface ValuationSummary {
  ev_ebitda: number | null;
  pe_ratio: number | null;
  fcf_yield: number | null;
  valuation_view: string;
  valuation_verdict: string;
}

export interface QualityRiskSummary {
  profitability_score: number;
  balance_sheet_score: number;
  cash_flow_quality_score: number;
  volatility_score: number;
}

export interface BusinessSummary {
  sector: string | null;
  industry: string | null;
  business_model: string | null;
  market_cap: number | null;
  enterprise_value: number | null;
  analyst_target_price: number | null;
  analyst_target_upside: number | null;
  analyst_recommendation: string | null;
  analyst_count: number | null;
}

export interface CapitalAllocationSummary {
  fcf_trend: string;
  debt_trend: string;
  reinvestment_vs_returns: string;
}

export interface DataQualitySummary {
  data_quality_score: number | null;
  years_available: number;
  missing_data: string[];
  warnings: string[];
}

export interface MomentumSummary {
  performance_1m: number | null;
  performance_6m: number | null;
  performance_12m: number | null;
  pct_vs_52w_high: number | null;
  pct_vs_52w_low: number | null;
}

export interface OwnershipTopHolder {
  holder_name: string;
  weight: number | null;
}

export interface OwnershipSummary {
  institutional_pct: number | null;
  insiders_pct: number | null;
  top_holders: OwnershipTopHolder[];
}

export interface CompanyInsights {
  analysis: AnalysisSummary;
  valuation: ValuationSummary;
  quality_risk: QualityRiskSummary;
  business: BusinessSummary;
  momentum: MomentumSummary;
  ownership: OwnershipSummary;
  capital_allocation: CapitalAllocationSummary;
  data_quality: DataQualitySummary;
}

function getCompanyPath(ticker: string, suffix = ""): string {
  return `/companies/${encodeURIComponent(ticker)}${suffix}`;
}

export async function downloadCompanyTearsheetCsv(ticker: string): Promise<void> {
  const blob = await api.getBlob(getCompanyPath(ticker, "/export"));
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const safeTicker = ticker.replace(/[^a-zA-Z0-9._-]/g, "_");
  link.href = url;
  link.download = `${safeTicker}-tearsheet.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function useCompanyDetail(ticker: string | null) {
  return useQuery({
    queryKey: ["companies", "detail", ticker],
    enabled: ticker !== null,
    queryFn: () => api.get<CompanyDetail>(getCompanyPath(ticker ?? "")),
  });
}

export function useCompanyScore(ticker: string | null) {
  return useQuery({
    queryKey: ["companies", "score", ticker],
    enabled: ticker !== null,
    queryFn: () => api.get<CompanyScore>(getCompanyPath(ticker ?? "", "/score")),
  });
}

export function useFinancialHistory(ticker: string | null) {
  return useQuery({
    queryKey: ["companies", "history", ticker],
    enabled: ticker !== null,
    queryFn: async () => {
      const safeTicker = ticker ?? "";
      try {
        return await api.get<HistoricalFundamentals>(getCompanyPath(safeTicker, "/history"));
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          const detail = await api.get<CompanyDetail>(getCompanyPath(safeTicker));
          return detail.historical_fundamentals;
        }
        throw error;
      }
    },
  });
}

export function useCompanyPeers(ticker: string | null) {
  return useQuery({
    queryKey: ["companies", "peers", ticker],
    enabled: ticker !== null,
    queryFn: () => api.get<PeerComparison>(getCompanyPath(ticker ?? "", "/peers")),
  });
}

export function useCompanyInsights(ticker: string | null) {
  return useQuery({
    queryKey: ["companies", "insights", ticker],
    enabled: ticker !== null,
    queryFn: () => api.get<CompanyInsights>(getCompanyPath(ticker ?? "", "/insights")),
  });
}
