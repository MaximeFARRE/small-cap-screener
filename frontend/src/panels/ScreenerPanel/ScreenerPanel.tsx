import { useEffect, useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  DEFAULT_SCREENING_FILTERS,
  useSnapshots,
  useUniverse,
  type ScreeningFilters,
} from "@/hooks";
import { ScreenerFilters, type ScreenerFilterState } from "./ScreenerFilters";
import { ScreenerTable } from "./ScreenerTable";

const FILTER_DEBOUNCE_MS = 300;

const DEFAULT_UI_FILTERS: ScreenerFilterState = {
  sector: "",
  minMarketCap: "",
  maxMarketCap: "",
  minScore: "",
  maxScore: "",
  watchlistOnly: false,
  sortBy: "rank",
  descending: false,
};

function parseOptionalNumber(raw: string): number | null {
  if (raw.trim().length === 0) {
    return null;
  }
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    return null;
  }
  return parsed;
}

function toApiFilters(filters: ScreenerFilterState): ScreeningFilters {
  return {
    ...DEFAULT_SCREENING_FILTERS,
    sector: filters.sector.trim() || null,
    min_total_score: parseOptionalNumber(filters.minScore),
    min_market_cap: parseOptionalNumber(filters.minMarketCap),
    max_market_cap: parseOptionalNumber(filters.maxMarketCap),
    watchlist_scope: filters.watchlistOnly ? "watchlist_only" : "all",
    sort_by: filters.sortBy,
    descending: filters.descending,
  };
}

export function ScreenerPanel() {
  const { activeTicker, setActiveTicker } = useWorkspace();

  const [filters, setFilters] = useState<ScreenerFilterState>(DEFAULT_UI_FILTERS);
  const [debouncedFilters, setDebouncedFilters] = useState<ScreenerFilterState>(DEFAULT_UI_FILTERS);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedFilters(filters);
    }, FILTER_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [filters]);

  const apiFilters = useMemo(() => toApiFilters(debouncedFilters), [debouncedFilters]);
  const universeQuery = useUniverse(apiFilters);
  const snapshotsQuery = useSnapshots(5);

  const rows = useMemo(() => {
    const loadedRows = universeQuery.data ?? [];
    const maxScore = parseOptionalNumber(debouncedFilters.maxScore);

    if (maxScore === null) {
      return loadedRows;
    }
    return loadedRows.filter(
      (row) => row.total_score === null || row.total_score <= maxScore,
    );
  }, [debouncedFilters.maxScore, universeQuery.data]);

  const sectors = useMemo(() => {
    const loadedRows = universeQuery.data ?? [];
    const unique = new Set<string>();
    for (const row of loadedRows) {
      if (row.sector) {
        unique.add(row.sector);
      }
    }
    return [...unique].sort((left, right) => left.localeCompare(right));
  }, [universeQuery.data]);

  const errorMessage =
    universeQuery.error instanceof Error
      ? universeQuery.error.message
      : "Failed to load universe.";

  const latestSnapshot = snapshotsQuery.data?.[0] ?? null;

  return (
    <div className="flex h-full min-h-0">
      <ScreenerFilters
        filters={filters}
        sectors={sectors}
        onChange={(next) => setFilters((current) => ({ ...current, ...next }))}
        onReset={() => setFilters(DEFAULT_UI_FILTERS)}
      />

      <section className="flex min-w-0 flex-1 flex-col bg-[var(--color-bg-panel)]">
        <header className="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-2">
          <div>
            <p className="font-mono text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
              Screener Universe
            </p>
            <p className="font-mono text-xs text-[var(--color-text-muted)]">
              {rows.length} companies
            </p>
          </div>
          <div className="text-right font-mono text-[11px] text-[var(--color-text-muted)]">
            <p>{latestSnapshot ? `Latest snapshot: ${latestSnapshot.name}` : "No snapshot yet"}</p>
            <p>{latestSnapshot ? new Date(latestSnapshot.created_at).toLocaleString() : "—"}</p>
          </div>
        </header>

        {universeQuery.isError ? (
          <ErrorState message={errorMessage} onRetry={() => void universeQuery.refetch()} />
        ) : universeQuery.isPending && !universeQuery.data ? (
          <LoadingState label="Loading universe…" />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No companies match current filters."
            description="Adjust filters or reset them to repopulate the universe."
          />
        ) : (
          <div className="min-h-0 flex-1 overflow-auto">
            <ScreenerTable
              rows={rows}
              activeTicker={activeTicker}
              onSelectTicker={setActiveTicker}
            />
          </div>
        )}
      </section>
    </div>
  );
}
