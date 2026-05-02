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
  useCompanyInsights,
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
type ExtendedTearsheetTab =
  | TearsheetTab
  | "analysis"
  | "valuation"
  | "quality_risk"
  | "business"
  | "capital_allocation"
  | "data_quality";

const TABS: Array<{ key: ExtendedTearsheetTab; label: string }> = [
  { key: "analysis", label: "Analysis" },
  { key: "valuation", label: "Valuation" },
  { key: "quality_risk", label: "Quality & Risk" },
  { key: "business", label: "Business" },
  { key: "capital_allocation", label: "Capital Allocation" },
  { key: "data_quality", label: "Data Quality" },
  { key: "summary", label: "Overview" },
  { key: "financials", label: "Financials" },
  { key: "charts", label: "Charts" },
  { key: "peers", label: "Peers" },
];

export function TearsheetPanel() {
  const { activeTicker } = useWorkspace();
  const [activeTab, setActiveTab] = useState<ExtendedTearsheetTab>("analysis");
  const [heroCollapsed, setHeroCollapsed] = useState(false);

  function selectTab(tab: ExtendedTearsheetTab) {
    setActiveTab(tab);
    if (tab !== "summary") setHeroCollapsed(true);
  }

  const detailQuery = useCompanyDetail(activeTicker);
  const scoreQuery = useCompanyScore(activeTicker);
  const historyQuery = useFinancialHistory(activeTicker);
  const peersQuery = useCompanyPeers(activeTicker);
  const insightsQuery = useCompanyInsights(activeTicker);
  const watchlistQuery = useWatchlist();
  const addToWatchlist = useAddToWatchlist();
  const removeFromWatchlist = useRemoveFromWatchlist();

  const isPendingAny =
    detailQuery.isPending ||
    scoreQuery.isPending ||
    historyQuery.isPending ||
    peersQuery.isPending ||
    insightsQuery.isPending;

  const firstError = useMemo(
    () =>
      detailQuery.error ??
      scoreQuery.error ??
      historyQuery.error ??
      peersQuery.error ??
      insightsQuery.error ??
      null,
    [detailQuery.error, historyQuery.error, insightsQuery.error, peersQuery.error, scoreQuery.error],
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
          void insightsQuery.refetch();
        }}
      />
    );
  }

  const detail = detailQuery.data;
  const score = scoreQuery.data;
  const historical = historyQuery.data;
  const peers = peersQuery.data;
  const insights = insightsQuery.data;

  if (!detail || !score || !historical || !peers || !insights) {
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
        {activeTab === "analysis" ? (
          <section className="space-y-3 p-4">
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Score breakdown</p>
              <p className="mt-1 font-mono text-sm text-[var(--color-text-primary)]">
                Quality {Math.round(insights.analysis.quality ?? 0)} | Value {Math.round(insights.analysis.value ?? 0)} | Growth {Math.round(insights.analysis.growth ?? 0)} | Risk {Math.round(insights.analysis.risk ?? 0)}
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
                <p className="font-mono text-xs uppercase text-[var(--color-positive)]">Strengths</p>
                <div className="mt-1 space-y-1 text-sm text-[var(--color-text-primary)]">
                  {insights.analysis.strengths.slice(0, 3).map((item) => <p key={item}>{item}</p>)}
                </div>
              </div>
              <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
                <p className="font-mono text-xs uppercase text-[var(--color-negative)]">Weaknesses</p>
                <div className="mt-1 space-y-1 text-sm text-[var(--color-text-primary)]">
                  {insights.analysis.weaknesses.slice(0, 3).map((item) => <p key={item}>{item}</p>)}
                </div>
              </div>
            </div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-xs uppercase text-[var(--color-warning)]">Red flags</p>
              <div className="mt-1 space-y-1 text-sm text-[var(--color-text-primary)]">
                {insights.analysis.red_flags.length === 0 ? <p>None</p> : insights.analysis.red_flags.map((item) => <p key={item}>{item}</p>)}
              </div>
            </div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Trend</p>
              <p className="mt-1 text-sm text-[var(--color-text-primary)]">{insights.analysis.trend}</p>
              <p className="mt-1 text-sm text-[var(--color-text-primary)]">{insights.analysis.verdict}</p>
            </div>
          </section>
        ) : activeTab === "valuation" ? (
          <section className="space-y-3 p-4">
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">EV/EBITDA: {insights.valuation.ev_ebitda ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">P/E: {insights.valuation.pe_ratio ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">FCF yield: {insights.valuation.fcf_yield ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Vs peers: {insights.valuation.valuation_view}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Verdict: {insights.valuation.valuation_verdict}</div>
          </section>
        ) : activeTab === "quality_risk" ? (
          <section className="space-y-3 p-4">
            {[
              ["Profitability", insights.quality_risk.profitability_score],
              ["Balance sheet", insights.quality_risk.balance_sheet_score],
              ["Cash flow quality", insights.quality_risk.cash_flow_quality_score],
              ["Volatility", insights.quality_risk.volatility_score],
            ].map(([label, scoreValue]) => (
              <div key={label} className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
                <div className="mb-1 flex justify-between font-mono text-xs text-[var(--color-text-muted)]">
                  <span>{label}</span>
                  <span>{Math.round(Number(scoreValue))}/100</span>
                </div>
                <div className="h-2 rounded bg-[var(--color-bg-panel)]">
                  <div className="h-2 rounded bg-[var(--color-accent)]" style={{ width: `${Math.max(0, Math.min(100, Number(scoreValue)))}%` }} />
                </div>
              </div>
            ))}
          </section>
        ) : activeTab === "business" ? (
          <section className="grid gap-3 p-4 md:grid-cols-2">
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Sector: {insights.business.sector ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Industry: {insights.business.industry ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Market cap: {insights.business.market_cap ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">EV: {insights.business.enterprise_value ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Target price: {insights.business.analyst_target_price ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Recommendation: {insights.business.analyst_recommendation ?? "—"} ({insights.business.analyst_count ?? 0})</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)] md:col-span-2">Business model: {insights.business.business_model ?? "—"}</div>
          </section>
        ) : activeTab === "capital_allocation" ? (
          <section className="space-y-3 p-4">
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">FCF evolution: {insights.capital_allocation.fcf_trend}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Debt evolution: {insights.capital_allocation.debt_trend}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Reinvestment vs returns: {insights.capital_allocation.reinvestment_vs_returns}</div>
          </section>
        ) : activeTab === "data_quality" ? (
          <section className="space-y-3 p-4">
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3 text-sm text-[var(--color-text-primary)]">Data quality score: {insights.data_quality.data_quality_score ?? "—"}</div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Missing data</p>
              <div className="mt-1 space-y-1 text-sm text-[var(--color-text-primary)]">
                {insights.data_quality.missing_data.length === 0 ? <p>None</p> : insights.data_quality.missing_data.map((item) => <p key={item}>{item}</p>)}
              </div>
            </div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-xs uppercase text-[var(--color-warning)]">Warnings</p>
              <div className="mt-1 space-y-1 text-sm text-[var(--color-text-primary)]">
                {insights.data_quality.warnings.length === 0 ? <p>None</p> : insights.data_quality.warnings.map((item) => <p key={item}>{item}</p>)}
              </div>
            </div>
          </section>
        ) : activeTab === "summary" ? (
          <ScoreBreakdown score={score} detail={detail} historical={historical} />
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
