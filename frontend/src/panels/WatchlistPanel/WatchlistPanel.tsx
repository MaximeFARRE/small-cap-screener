import { useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  useAddToWatchlist,
  useRemoveFromWatchlist,
  useUpdateMemo,
  useWatchlist,
  useWatchlistDetail,
  type AnalystMemo as AnalystMemoValue,
} from "@/hooks";
import { AnalystMemo } from "./AnalystMemo";
import { WatchlistRow } from "./WatchlistRow";

export function WatchlistPanel() {
  const { activeTicker, setActiveTicker } = useWorkspace();
  const watchlistQuery = useWatchlist();
  const addToWatchlist = useAddToWatchlist();
  const removeFromWatchlist = useRemoveFromWatchlist();
  const updateMemo = useUpdateMemo();

  const [selectedTickerOverride, setSelectedTickerOverride] = useState<string | null>(null);

  const rows = watchlistQuery.data;

  const selectedTicker = useMemo(() => {
    const tickers = (rows ?? [])
      .map((entry) => entry.ticker)
      .filter((ticker): ticker is string => ticker !== null);
    if (tickers.length === 0) {
      return null;
    }

    if (selectedTickerOverride && tickers.includes(selectedTickerOverride)) {
      return selectedTickerOverride;
    }
    if (activeTicker && tickers.includes(activeTicker)) {
      return activeTicker;
    }
    return tickers[0] ?? null;
  }, [activeTicker, rows, selectedTickerOverride]);

  const selectedDetailQuery = useWatchlistDetail(selectedTicker);

  const activeTickerIsInWatchlist =
    activeTicker !== null && (rows ?? []).some((entry) => entry.ticker === activeTicker);

  const handleSelectTicker = (ticker: string) => {
    setActiveTicker(ticker);
    setSelectedTickerOverride(ticker);
  };

  const handleRemoveTicker = (ticker: string) => {
    removeFromWatchlist.mutate({ ticker });
  };

  const handleSaveMemo = async (ticker: string, memo: AnalystMemoValue): Promise<void> => {
    await updateMemo.mutateAsync({ ticker, memo });
  };

  const errorMessage =
    watchlistQuery.error instanceof Error
      ? watchlistQuery.error.message
      : "Failed to load watchlist.";

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--color-bg-panel)]">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-2">
        <div>
          <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Watchlist</p>
          <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
            {(rows ?? []).length} tracked companies
          </p>
        </div>

        {activeTicker ? (
          activeTickerIsInWatchlist ? (
            <Button
              type="button"
              size="sm"
              variant="destructive"
              onClick={() => handleRemoveTicker(activeTicker)}
              disabled={removeFromWatchlist.isPending}
              className="font-mono text-xs"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Remove
            </Button>
          ) : (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => addToWatchlist.mutate({ ticker: activeTicker })}
              disabled={addToWatchlist.isPending}
              className="font-mono text-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              Add {activeTicker}
            </Button>
          )
        ) : null}
      </header>

      {watchlistQuery.isError ? (
        <ErrorState message={errorMessage} onRetry={() => void watchlistQuery.refetch()} />
      ) : watchlistQuery.isPending && !watchlistQuery.data ? (
        <LoadingState label="Loading watchlist…" />
      ) : (rows ?? []).length === 0 ? (
        <EmptyState
          title="Watchlist is empty."
          description="Add a ticker from Screener or Tearsheet."
        />
      ) : (
        <div className="flex min-h-0 flex-1">
          <div className="w-[45%] min-w-80 space-y-2 overflow-auto p-3">
            {(rows ?? []).map((entry) => (
              <WatchlistRow
                key={entry.company_id}
                entry={entry}
                isActive={entry.ticker !== null && entry.ticker === selectedTicker}
                onSelect={handleSelectTicker}
                onRemove={handleRemoveTicker}
              />
            ))}
          </div>

          {selectedTicker === null ? (
            <div className="flex flex-1 items-center justify-center border-l border-[var(--color-border)]">
              <EmptyState title="Select a company to edit memo." />
            </div>
          ) : selectedDetailQuery.isError ? (
            <div className="flex flex-1 items-center justify-center border-l border-[var(--color-border)]">
              <ErrorState
                message={
                  selectedDetailQuery.error instanceof Error
                    ? selectedDetailQuery.error.message
                    : "Failed to load watchlist detail."
                }
                onRetry={() => void selectedDetailQuery.refetch()}
              />
            </div>
          ) : selectedDetailQuery.isPending || !selectedDetailQuery.data ? (
            <div className="flex flex-1 items-center justify-center border-l border-[var(--color-border)]">
              <LoadingState label="Loading memo…" />
            </div>
          ) : (
            <div className="min-h-0 flex-1">
              <AnalystMemo
                key={selectedTicker}
                ticker={selectedTicker}
                memo={selectedDetailQuery.data.analyst_memo}
                onSave={handleSaveMemo}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
