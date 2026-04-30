import * as React from "react";
import { ChevronLeft, ChevronRight, RotateCcw } from "lucide-react";
import type { UniverseSortBy } from "@/hooks";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ScreenerFilterState {
  sector: string;
  minMarketCap: string;
  maxMarketCap: string;
  minScore: string;
  maxScore: string;
  watchlistOnly: boolean;
  sortBy: UniverseSortBy;
  descending: boolean;
}

interface ScreenerFiltersProps {
  filters: ScreenerFilterState;
  sectors: string[];
  onChange: (next: Partial<ScreenerFilterState>) => void;
  onReset: () => void;
}

const SORT_OPTIONS: Array<{ value: UniverseSortBy; label: string }> = [
  { value: "rank", label: "Rank" },
  { value: "total_score", label: "Total score" },
  { value: "quality_score", label: "Quality score" },
  { value: "value_score", label: "Value score" },
  { value: "growth_score", label: "Growth score" },
  { value: "risk_score", label: "Risk score" },
  { value: "ticker", label: "Ticker" },
];

export function ScreenerFilters({
  filters,
  sectors,
  onChange,
  onReset,
}: ScreenerFiltersProps) {
  const [collapsed, setCollapsed] = React.useState(false);

  return (
    <aside
      className={cn(
        "border-r border-[var(--color-border)] bg-[var(--color-bg-panel)] transition-all",
        collapsed ? "w-12" : "w-64",
      )}
    >
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-2 py-2">
        {!collapsed ? (
          <p className="font-mono text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
            Filters
          </p>
        ) : null}
        <button
          type="button"
          className="inline-flex h-7 w-7 items-center justify-center rounded-sm border border-[var(--color-border)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
          onClick={() => setCollapsed((value) => !value)}
          aria-label={collapsed ? "Expand filters" : "Collapse filters"}
        >
          {collapsed ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronLeft className="h-3.5 w-3.5" />}
        </button>
      </div>

      {collapsed ? null : (
        <div className="space-y-3 p-3">
          <label className="block space-y-1">
            <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Sector</span>
            <select
              className="w-full rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5 text-xs text-[var(--color-text-primary)]"
              value={filters.sector}
              onChange={(event) => onChange({ sector: event.target.value })}
            >
              <option value="">All sectors</option>
              {sectors.map((sector) => (
                <option key={sector} value={sector}>
                  {sector}
                </option>
              ))}
            </select>
          </label>

          <div className="grid grid-cols-2 gap-2">
            <label className="block space-y-1">
              <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Min cap</span>
              <input
                type="number"
                inputMode="decimal"
                className="w-full rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5 text-xs text-[var(--color-text-primary)]"
                value={filters.minMarketCap}
                onChange={(event) => onChange({ minMarketCap: event.target.value })}
                placeholder="0"
              />
            </label>
            <label className="block space-y-1">
              <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Max cap</span>
              <input
                type="number"
                inputMode="decimal"
                className="w-full rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5 text-xs text-[var(--color-text-primary)]"
                value={filters.maxMarketCap}
                onChange={(event) => onChange({ maxMarketCap: event.target.value })}
                placeholder="2000000000"
              />
            </label>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <label className="block space-y-1">
              <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Min score</span>
              <input
                type="number"
                inputMode="decimal"
                className="w-full rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5 text-xs text-[var(--color-text-primary)]"
                value={filters.minScore}
                onChange={(event) => onChange({ minScore: event.target.value })}
                placeholder="0"
              />
            </label>
            <label className="block space-y-1">
              <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Max score</span>
              <input
                type="number"
                inputMode="decimal"
                className="w-full rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5 text-xs text-[var(--color-text-primary)]"
                value={filters.maxScore}
                onChange={(event) => onChange({ maxScore: event.target.value })}
                placeholder="100"
              />
            </label>
          </div>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={filters.watchlistOnly}
              onChange={(event) => onChange({ watchlistOnly: event.target.checked })}
              className="h-4 w-4 rounded border border-[var(--color-border)] bg-[var(--color-bg-elevated)]"
            />
            <span className="font-mono text-xs text-[var(--color-text-primary)]">Watchlist only</span>
          </label>

          <label className="block space-y-1">
            <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Sort by</span>
            <select
              className="w-full rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5 text-xs text-[var(--color-text-primary)]"
              value={filters.sortBy}
              onChange={(event) => onChange({ sortBy: event.target.value as UniverseSortBy })}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={filters.descending}
              onChange={(event) => onChange({ descending: event.target.checked })}
              className="h-4 w-4 rounded border border-[var(--color-border)] bg-[var(--color-bg-elevated)]"
            />
            <span className="font-mono text-xs text-[var(--color-text-primary)]">Descending</span>
          </label>

          <Button
            type="button"
            variant="outline"
            size="sm"
            className="w-full justify-center font-mono text-xs"
            onClick={onReset}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset filters
          </Button>
        </div>
      )}
    </aside>
  );
}
