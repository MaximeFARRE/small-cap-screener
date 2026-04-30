import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { CompanyScore } from "./useCompany";

export type WatchlistStatus = "watching" | "review" | "conviction" | "rejected";

export interface AnalystMemo {
  investment_thesis: string | null;
  key_risks: string | null;
  catalysts: string | null;
  valuation_notes: string | null;
  next_action: string | null;
}

export interface WatchlistEntry {
  company_id: number;
  ticker: string | null;
  name: string;
  status: WatchlistStatus | string;
  notes: string | null;
  memo_summary: string | null;
  is_excluded: boolean;
  total_score: number | null;
  rank: number | null;
  sector_rank: number | null;
  data_quality_score: number | null;
  last_universe_refresh_at: string | null;
  next_review_at: string | null;
}

export interface WatchlistDetail {
  watchlist_status: WatchlistStatus | string | null;
  watchlist_notes: string | null;
  watchlist_is_excluded: boolean;
  next_review_at: string | null;
  analyst_memo: AnalystMemo;
  quality_score: number | null;
  value_score: number | null;
  growth_score: number | null;
  risk_score: number | null;
  total_score: number | null;
  rank: number | null;
  sector_rank: number | null;
  score_explanation: CompanyScore;
}

function watchlistKey() {
  return ["watchlist"] as const;
}

function watchlistDetailKey(ticker: string) {
  return ["watchlist", "detail", ticker] as const;
}

async function invalidateWatchlistQueries(queryClient: QueryClient): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({ queryKey: watchlistKey() }),
    queryClient.invalidateQueries({ queryKey: ["companies"] }),
    queryClient.invalidateQueries({ queryKey: ["screening", "universe"] }),
  ]);
}

export function useWatchlist() {
  return useQuery({
    queryKey: watchlistKey(),
    queryFn: () => api.get<WatchlistEntry[]>("/watchlist"),
  });
}

export function useWatchlistDetail(ticker: string | null) {
  return useQuery({
    queryKey: ["watchlist", "detail", ticker],
    enabled: ticker !== null,
    queryFn: () =>
      api.get<WatchlistDetail>(`/watchlist/${encodeURIComponent(ticker ?? "")}/detail`),
  });
}

export function useAddToWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticker, notes }: { ticker: string; notes?: string | null }) =>
      api.post<WatchlistEntry>(`/watchlist/${encodeURIComponent(ticker)}`, {
        notes: notes ?? null,
      }),
    onSuccess: async () => {
      await invalidateWatchlistQueries(queryClient);
    },
  });
}

export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticker }: { ticker: string }) =>
      api.delete<void>(`/watchlist/${encodeURIComponent(ticker)}`),
    onSuccess: async () => {
      await invalidateWatchlistQueries(queryClient);
    },
  });
}

export function useUpdateMemo() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticker, memo }: { ticker: string; memo: AnalystMemo }) =>
      api.patch<AnalystMemo>(`/watchlist/${encodeURIComponent(ticker)}/memo`, memo),
    onSuccess: async (_data, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: watchlistDetailKey(variables.ticker),
        }),
        invalidateWatchlistQueries(queryClient),
      ]);
    },
  });
}

export function useUpdateWatchlistStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticker, status }: { ticker: string; status: WatchlistStatus }) =>
      api.patch<void>(`/watchlist/${encodeURIComponent(ticker)}/status`, { status }),
    onMutate: async ({ ticker, status }) => {
      await queryClient.cancelQueries({ queryKey: watchlistKey() });
      const previous = queryClient.getQueryData<WatchlistEntry[]>(watchlistKey());

      queryClient.setQueryData<WatchlistEntry[]>(watchlistKey(), (current) =>
        (current ?? []).map((entry) =>
          entry.ticker === ticker ? { ...entry, status } : entry,
        ),
      );

      return { previous };
    },
    onError: (_error, _variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(watchlistKey(), context.previous);
      }
    },
    onSettled: async () => {
      await invalidateWatchlistQueries(queryClient);
    },
  });
}
