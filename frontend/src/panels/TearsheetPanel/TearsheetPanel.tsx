import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/context/WorkspaceContext";
import {
  useAddToWatchlist,
  downloadCompanyTearsheetCsv,
  useCompanyDetail,
  useCompanyPeers,
  useCompanyScore,
  useFinancialHistory,
  useRemoveFromWatchlist,
  useWatchlist,
} from "@/hooks";
import { cn } from "@/lib/utils";
import { FinancialsTable } from "./FinancialsTable";
import { PeersTable } from "./PeersTable";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { TearsheetCharts } from "./TearsheetCharts";
import { TearsheetHero } from "./TearsheetHero";

type TearsheetTab = "summary" | "financials" | "charts" | "peers";

const TABS: Array<{ key: TearsheetTab; label: string }> = [
  { key: "summary", label: "Summary" },
  { key: "financials", label: "Financials" },
  { key: "charts", label: "Charts" },
  { key: "peers", label: "Peers" },
];

export function TearsheetPanel() {
  const { activeTicker } = useWorkspace();
  const [activeTab, setActiveTab] = useState<TearsheetTab>("summary");
  const [heroCollapsed, setHeroCollapsed] = useState(false);

  function selectTab(tab: TearsheetTab) {
    setActiveTab(tab);
    if (tab !== "summary") setHeroCollapsed(true);
  }

  const detailQuery = useCompanyDetail(activeTicker);
  const scoreQuery = useCompanyScore(activeTicker);
  const historyQuery = useFinancialHistory(activeTicker);
  const peersQuery = useCompanyPeers(activeTicker);
  const watchlistQuery = useWatchlist();
  const addToWatchlist = useAddToWatchlist();
  const removeFromWatchlist = useRemoveFromWatchlist();

  const isPendingAny =
    detailQuery.isPending || scoreQuery.isPending || historyQuery.isPending || peersQuery.isPending;

  const firstError = useMemo(
    () =>
      detailQuery.error ??
      scoreQuery.error ??
      historyQuery.error ??
      peersQuery.error ??
      null,
    [detailQuery.error, historyQuery.error, peersQuery.error, scoreQuery.error],
  );

  if (activeTicker === null) {
    return (
      <EmptyState
        title="Select a company from the screener or watchlist."
      />
    );
  }

  if (firstError) {
    return (
      <ErrorState
        message={firstError instanceof Error ? firstError.message : "Failed to load company data."}
        onRetry={() => {
          void detailQuery.refetch();
          void scoreQuery.refetch();
          void historyQuery.refetch();
          void peersQuery.refetch();
        }}
      />
    );
  }

  const detail = detailQuery.data;
  const score = scoreQuery.data;
  const historical = historyQuery.data;
  const peers = peersQuery.data;

  if (!detail || !score || !historical || !peers) {
    return (
      isPendingAny ? (
        <LoadingState label="Loading tearsheet…" />
      ) : (
        <EmptyState title="No data available for selected company." />
      )
    );
  }

  const ticker = detail.ticker;
  const isInWatchlist =
    ticker !== null &&
    (watchlistQuery.data ?? []).some((entry) => entry.ticker === ticker);

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--color-bg-panel)]">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-2">
        <div>
          <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Tearsheet</p>
          <p className="font-mono text-[11px] text-[var(--color-text-muted)]">{detail.ticker ?? "—"}</p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="font-mono text-xs"
          disabled={!ticker}
          onClick={async () => {
            if (!ticker) {
              return;
            }
            try {
              await downloadCompanyTearsheetCsv(ticker);
              toast.success(`Exported tearsheet for ${ticker}`);
            } catch (error) {
              toast.error(error instanceof Error ? error.message : "Failed to export tearsheet");
            }
          }}
        >
          <Download className="h-3.5 w-3.5" />
          Export tearsheet
        </Button>
      </header>

      <TearsheetHero
        detail={detail}
        score={score}
        isInWatchlist={isInWatchlist}
        isCollapsed={heroCollapsed}
        onToggleCollapse={() => setHeroCollapsed((c) => !c)}
        watchlistActionPending={addToWatchlist.isPending || removeFromWatchlist.isPending}
        onAddToWatchlist={() => {
          if (ticker) {
            addToWatchlist.mutate(
              { ticker },
              {
                onSuccess: () => {
                  toast.success(`${ticker} added to watchlist`);
                },
              },
            );
          }
        }}
        onRemoveFromWatchlist={() => {
          if (ticker) {
            removeFromWatchlist.mutate(
              { ticker },
              {
                onSuccess: () => {
                  toast.success(`${ticker} removed from watchlist`);
                },
              },
            );
          }
        }}
      />

      <nav className="flex items-center gap-1 border-b border-[var(--color-border)] px-3 py-2">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => selectTab(tab.key)}
            className={cn(
              "rounded-sm border px-2 py-1 font-mono text-xs transition-colors",
              activeTab === tab.key
                ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white"
                : "border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]",
            )}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="min-h-0 flex-1 overflow-auto">
        {activeTab === "summary" ? (
          <ScoreBreakdown score={score} />
        ) : activeTab === "financials" ? (
          <FinancialsTable historical={historical} />
        ) : activeTab === "charts" ? (
          <TearsheetCharts historical={historical} />
        ) : (
          <PeersTable peers={peers} activeTicker={activeTicker} />
        )}
      </div>
    </div>
  );
}
