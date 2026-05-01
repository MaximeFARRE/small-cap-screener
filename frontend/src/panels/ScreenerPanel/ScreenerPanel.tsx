import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  DEFAULT_SCREENING_FILTERS,
  useIngestTicker,
  openUniverseImportStream,
  useSnapshots,
  useUniverse,
  type ScreeningFilters,
} from "@/hooks";
import {
  UNIVERSE_IMPORT_STATUS_EVENT,
  type UniverseImportStatusDetail,
} from "@/lib/universeImportEvents";
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
  const queryClient = useQueryClient();
  const { activeTicker, focusedPanelType, setActiveTicker } = useWorkspace();

  const [filters, setFilters] = useState<ScreenerFilterState>(DEFAULT_UI_FILTERS);
  const [debouncedFilters, setDebouncedFilters] = useState<ScreenerFilterState>(DEFAULT_UI_FILTERS);
  const [isUniverseImportRunning, setIsUniverseImportRunning] = useState(false);
  const sectorFilterRef = useRef<HTMLSelectElement | null>(null);
  const importStreamRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const onFocusScreenerFilter = () => {
      sectorFilterRef.current?.focus();
    };
    window.addEventListener("workspace:focus-screener-filter", onFocusScreenerFilter);
    return () => {
      window.removeEventListener("workspace:focus-screener-filter", onFocusScreenerFilter);
    };
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setDebouncedFilters(filters);
    }, FILTER_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [filters]);

  const apiFilters = useMemo(() => toApiFilters(debouncedFilters), [debouncedFilters]);
  const universeQuery = useUniverse(apiFilters);
  const snapshotsQuery = useSnapshots(5);
  const ingestTickerMutation = useIngestTicker();

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

  const isActionPending = ingestTickerMutation.isPending || isUniverseImportRunning;

  const emitUniverseImportStatus = (detail: UniverseImportStatusDetail) => {
    window.dispatchEvent(
      new CustomEvent<UniverseImportStatusDetail>(UNIVERSE_IMPORT_STATUS_EVENT, {
        detail,
      }),
    );
  };

  useEffect(() => {
    return () => {
      if (importStreamRef.current) {
        importStreamRef.current.close();
        importStreamRef.current = null;
      }
    };
  }, []);

  const handleAddTicker = async () => {
    const rawInput = window.prompt("Ticker ou ISIN (ex: MC.PA ou FR0000120271)");
    if (rawInput === null) {
      return;
    }
    const identifier = rawInput.trim();
    if (identifier.length === 0) {
      window.alert("Ticker/ISIN vide.");
      return;
    }

    try {
      const result = await ingestTickerMutation.mutateAsync(identifier);
      if (!result.success) {
        window.alert(result.error ?? "Échec de l'import du ticker.");
        return;
      }
      const warnings = result.warnings.length > 0 ? `\nAvertissements: ${result.warnings.join(" | ")}` : "";
      window.alert(`Ticker importé: ${result.resolved_ticker ?? result.ticker}${warnings}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Échec de l'import du ticker.";
      window.alert(message);
    }
  };

  const handleImportSmallCaps = async () => {
    const confirmed = window.confirm(
      "Importer toutes les small caps France et lancer l'enrichissement complet ?",
    );
    if (!confirmed) {
      return;
    }
    if (importStreamRef.current) {
      importStreamRef.current.close();
      importStreamRef.current = null;
    }

    setIsUniverseImportRunning(true);
    emitUniverseImportStatus({
      phase: "running",
      message: "Import universe en cours…",
      processed: 0,
      total: 0,
    });

    importStreamRef.current = openUniverseImportStream({
      enrich: true,
      pacingSeconds: 0.0,
      batchSize: 25,
      onStart: () => {
        emitUniverseImportStatus({
          phase: "running",
          message: "Découverte Euronext France en cours…",
          processed: 0,
          total: 0,
        });
      },
      onDiscovery: (payload) => {
        emitUniverseImportStatus({
          phase: "discovery_done",
          message: `Découverte terminée: ${payload.discovered_count} trouvées, ${payload.upserted_count} importées.`,
          processed: 0,
          total: payload.enrichment_total,
        });
      },
      onProgress: (payload) => {
        const phaseMessage =
          payload.phase === "batch_start"
            ? `Enrichissement lot ${payload.batch_number ?? 0}/${payload.total_batches ?? 0}…`
            : payload.phase === "company_result" && payload.ticker
              ? `Enrichissement ${payload.ticker} (${payload.processed}/${payload.total})…`
              : "Enrichissement en cours…";

        emitUniverseImportStatus({
          phase: "running",
          message: phaseMessage,
          processed: payload.processed,
          total: payload.total,
        });
      },
      onDone: async (result) => {
        setIsUniverseImportRunning(false);
        importStreamRef.current = null;
        emitUniverseImportStatus({
          phase: "completed",
          message: `Import terminé: ${result.enrichment_succeeded}/${result.enrichment_total} enrichies.`,
          processed: result.enrichment_total,
          total: result.enrichment_total,
          succeeded: result.enrichment_succeeded,
          failed: result.enrichment_failed,
          skipped: result.enrichment_skipped,
        });
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["screening", "universe"] }),
          queryClient.invalidateQueries({ queryKey: ["companies"] }),
          queryClient.invalidateQueries({ queryKey: ["signals"] }),
          queryClient.invalidateQueries({ queryKey: ["screening", "snapshots"] }),
        ]);
        window.alert(
          `Import terminé.\nDécouvertes: ${result.discovered_count}\nImportées/mises à jour: ${result.upserted_count}\nEnrichies: ${result.enrichment_succeeded}/${result.enrichment_total}\nÉchecs: ${result.enrichment_failed}\nIgnorées: ${result.enrichment_skipped}`,
        );
      },
      onServerError: (message) => {
        setIsUniverseImportRunning(false);
        importStreamRef.current = null;
        emitUniverseImportStatus({
          phase: "error",
          message,
        });
        window.alert(message);
      },
      onConnectionError: (message) => {
        setIsUniverseImportRunning(false);
        importStreamRef.current = null;
        emitUniverseImportStatus({
          phase: "error",
          message,
        });
        window.alert(message);
      },
    });
  };

  return (
    <div className="flex h-full min-h-0">
      <ScreenerFilters
        filters={filters}
        sectors={sectors}
        onChange={(next) => setFilters((current) => ({ ...current, ...next }))}
        onReset={() => setFilters(DEFAULT_UI_FILTERS)}
        focusTargetRef={sectorFilterRef}
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
          <div className="ml-3 flex items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => void handleAddTicker()}
              disabled={isActionPending}
            >
              Ajouter un ticker
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => void handleImportSmallCaps()}
              disabled={isActionPending}
            >
              Importer small caps
            </Button>
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
              panelFocused={focusedPanelType === "screener"}
              onSelectTicker={setActiveTicker}
            />
          </div>
        )}
      </section>
    </div>
  );
}
