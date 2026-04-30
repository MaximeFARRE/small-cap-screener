import { useMemo, useState } from "react";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useSignals, type ScoreMover, type TopCompanySignal } from "@/hooks";
import { SectionHeader } from "./SectionHeader";
import { SignalRow } from "./SignalRow";

type SectionKey =
  | "moversUp"
  | "moversDown"
  | "topQuality"
  | "topValue"
  | "watchlistAlerts";

interface SectionBlockProps {
  title: string;
  items: Array<ScoreMover | TopCompanySignal>;
  collapsed: boolean;
  onToggle: () => void;
  onSelectTicker: (ticker: string) => void;
}

function SectionBlock({
  title,
  items,
  collapsed,
  onToggle,
  onSelectTicker,
}: SectionBlockProps) {
  return (
    <section className="space-y-2">
      <SectionHeader
        title={title}
        count={items.length}
        collapsed={collapsed}
        onToggle={onToggle}
      />
      {collapsed ? null : items.length === 0 ? (
        <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-2 py-2 font-mono text-xs text-[var(--color-text-muted)]">
          No signals in this section.
        </div>
      ) : (
        <div className="space-y-1">
          {items.map((item) => (
            <SignalRow
              key={`${item.company_id ?? "na"}:${item.ticker ?? "na"}:${item.name}`}
              signal={item}
              onSelectTicker={onSelectTicker}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export function SignalsPanel() {
  const { setActiveTicker } = useWorkspace();
  const signalsQuery = useSignals();

  const [collapsedSections, setCollapsedSections] = useState<Record<SectionKey, boolean>>({
    moversUp: false,
    moversDown: false,
    topQuality: false,
    topValue: false,
    watchlistAlerts: false,
  });

  const payload = signalsQuery.data;

  const sections = useMemo(
    () => [
      {
        key: "moversUp" as const,
        title: "Score Movers ↑",
        items: payload?.movers_up ?? [],
      },
      {
        key: "moversDown" as const,
        title: "Score Movers ↓",
        items: payload?.movers_down ?? [],
      },
      {
        key: "topQuality" as const,
        title: "Top Quality",
        items: payload?.top_quality ?? [],
      },
      {
        key: "topValue" as const,
        title: "Top Value",
        items: payload?.top_value ?? [],
      },
      {
        key: "watchlistAlerts" as const,
        title: "Watchlist Alerts",
        items: payload?.watchlist_alerts ?? [],
      },
    ],
    [payload],
  );

  const errorMessage =
    signalsQuery.error instanceof Error
      ? signalsQuery.error.message
      : "Failed to load signals.";

  return (
    <div className="flex h-full min-h-0 flex-col bg-[var(--color-bg-panel)]">
      <header className="border-b border-[var(--color-border)] px-3 py-2">
        <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Signals</p>
        <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
          {payload?.snapshot_name
            ? `Reference snapshot: ${payload.snapshot_name}`
            : "No snapshot reference yet"}
        </p>
      </header>

      {signalsQuery.isError ? (
        <div className="flex flex-1 items-center justify-center p-4">
          <p className="font-mono text-sm text-[var(--color-negative)]">{errorMessage}</p>
        </div>
      ) : signalsQuery.isPending && !payload ? (
        <div className="flex flex-1 items-center justify-center p-4">
          <p className="font-mono text-sm text-[var(--color-text-muted)]">Loading signals…</p>
        </div>
      ) : (
        <div className="min-h-0 flex-1 space-y-3 overflow-auto p-3">
          {sections.map((section) => (
            <SectionBlock
              key={section.key}
              title={section.title}
              items={section.items}
              collapsed={collapsedSections[section.key]}
              onToggle={() =>
                setCollapsedSections((current) => ({
                  ...current,
                  [section.key]: !current[section.key],
                }))
              }
              onSelectTicker={(ticker) => setActiveTicker(ticker)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
