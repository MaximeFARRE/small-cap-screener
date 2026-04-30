import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { ScoreBadge } from "@/components/ScoreBadge";
import type { ScoreMover, TopCompanySignal } from "@/hooks";
import { cn } from "@/lib/utils";

type SignalRowData = ScoreMover | TopCompanySignal;

interface SignalRowProps {
  signal: SignalRowData;
  onSelectTicker: (ticker: string) => void;
}

function hasDelta(signal: SignalRowData): signal is ScoreMover {
  return "total_score_change" in signal;
}

function isTickerValue(value: string | null): value is string {
  return value !== null && value.trim().length > 0;
}

export function SignalRow({ signal, onSelectTicker }: SignalRowProps) {
  const ticker = signal.ticker;
  const delta = hasDelta(signal) ? signal.total_score_change : null;
  const score = hasDelta(signal) ? signal.current_total_score : signal.total_score;

  return (
    <button
      type="button"
      className="flex w-full items-center justify-between gap-2 rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-2 py-1.5 text-left hover:bg-[var(--color-bg-elevated)]"
      onClick={() => {
        if (isTickerValue(ticker)) {
          onSelectTicker(ticker);
        }
      }}
      disabled={!isTickerValue(ticker)}
    >
      <div className="min-w-0">
        <p className="font-mono text-xs text-[var(--color-text-primary)]">
          {ticker ?? "—"} · {signal.name}
        </p>
        <p className="truncate font-mono text-[11px] text-[var(--color-text-muted)]">
          {signal.sector ?? "Unknown sector"}
        </p>
      </div>

      <div className="flex items-center gap-2">
        <ScoreBadge score={score} />
        {delta !== null ? (
          <span
            className={cn(
              "inline-flex items-center gap-1 font-mono text-[11px]",
              delta >= 0
                ? "text-[var(--color-positive)]"
                : "text-[var(--color-negative)]",
            )}
          >
            {delta >= 0 ? (
              <ArrowUpRight className="h-3.5 w-3.5" />
            ) : (
              <ArrowDownRight className="h-3.5 w-3.5" />
            )}
            {delta >= 0 ? "+" : ""}
            {Math.round(delta)} pts
          </span>
        ) : null}
      </div>
    </button>
  );
}
