import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export type UniverseSortBy =
  | "rank"
  | "total_score"
  | "quality_score"
  | "value_score"
  | "growth_score"
  | "risk_score"
  | "ticker";

export type WatchlistScope = "all" | "watchlist_only" | "non_watchlist_only";

export interface ScreeningFilters {
  sector: string | null;
  min_total_score: number | null;
  min_data_quality_score: number | null;
  max_pe: number | null;
  min_growth: number | null;
  min_margin: number | null;
  min_market_cap: number | null;
  max_market_cap: number | null;
  stale_only: boolean;
  scored_only: boolean;
  watchlist_scope: WatchlistScope;
  watchlist_status: string | null;
  include_excluded: boolean;
  top_n: number | null;
  sort_by: UniverseSortBy;
  descending: boolean;
}

export interface CompanyRow {
  company_id: number;
  ticker: string | null;
  name: string;
  sector: string | null;
  market: string | null;
  country: string | null;
  total_score: number | null;
  quality_score: number | null;
  value_score: number | null;
  growth_score: number | null;
  risk_score: number | null;
  rank: number | null;
  sector_rank: number | null;
  pe_ratio: number | null;
  ev_ebitda: number | null;
  fcf_yield: number | null;
  revenue_growth: number | null;
  ebitda_margin: number | null;
  operating_margin: number | null;
  roic: number | null;
  roe: number | null;
  net_debt_to_ebitda: number | null;
  market_cap: number | null;
  data_quality_score: number | null;
  last_universe_refresh_at: string | null;
  snapshot_date: string | null;
}

export interface SnapshotSummary {
  snapshot_id: number;
  name: string;
  created_at: string;
  company_count: number;
  filters_summary: string;
}

export const DEFAULT_SCREENING_FILTERS: ScreeningFilters = {
  sector: null,
  min_total_score: null,
  min_data_quality_score: null,
  max_pe: null,
  min_growth: null,
  min_margin: null,
  min_market_cap: null,
  max_market_cap: null,
  stale_only: false,
  scored_only: false,
  watchlist_scope: "all",
  watchlist_status: null,
  include_excluded: false,
  top_n: null,
  sort_by: "rank",
  descending: false,
};

function toApiFilters(filters: ScreeningFilters): ScreeningFilters {
  return {
    ...filters,
    sector: filters.sector?.trim() || null,
  };
}

export function useUniverse(filters: ScreeningFilters) {
  return useQuery({
    queryKey: ["screening", "universe", filters],
    queryFn: () =>
      api.post<CompanyRow[]>("/screening/universe/filter", toApiFilters(filters)),
  });
}

export function useSnapshots(limit = 20) {
  return useQuery({
    queryKey: ["screening", "snapshots", limit],
    queryFn: () => api.get<SnapshotSummary[]>(`/screening/snapshots?limit=${limit}`),
  });
}
