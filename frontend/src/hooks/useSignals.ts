import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface ScoreMover {
  company_id: number | null;
  ticker: string | null;
  name: string;
  sector: string | null;
  snapshot_total_score: number | null;
  current_total_score: number | null;
  total_score_change: number | null;
  snapshot_rank: number | null;
  current_rank: number | null;
}

export interface TopCompanySignal {
  company_id: number;
  ticker: string | null;
  name: string;
  sector: string | null;
  total_score: number | null;
  quality_score: number | null;
  value_score: number | null;
  rank: number | null;
}

export interface SignalsPayload {
  movers_up: ScoreMover[];
  movers_down: ScoreMover[];
  top_quality: TopCompanySignal[];
  top_value: TopCompanySignal[];
  watchlist_alerts: ScoreMover[];
  snapshot_name: string | null;
  has_snapshot: boolean;
}

const SIGNALS_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

export function useSignals() {
  return useQuery({
    queryKey: ["signals"],
    queryFn: () => api.get<SignalsPayload>("/signals"),
    refetchInterval: SIGNALS_REFRESH_INTERVAL_MS,
  });
}
