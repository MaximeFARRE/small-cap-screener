import { Trash2 } from "lucide-react";
import { ScoreBadge } from "@/components/ScoreBadge";
import { Button } from "@/components/ui/button";
import { type WatchlistEntry } from "@/hooks";
import { cn } from "@/lib/utils";
import { WatchlistStatusSelect } from "./WatchlistStatusSelect";

interface WatchlistRowProps {
  entry: WatchlistEntry;
  isActive: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

function statusToneClass(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "conviction") {
    return "border-[var(--color-positive)]/40 bg-[var(--color-positive)]/20 text-[var(--color-positive)]";
  }
  if (normalized === "review") {
    return "border-[var(--color-warning)]/40 bg-[var(--color-warning)]/20 text-[var(--color-warning)]";
  }
  if (normalized === "rejected") {
    return "border-[var(--color-negative)]/35 bg-[var(--color-negative)]/20 text-[var(--color-negative)]";
  }
  return "border-[var(--color-accent)]/40 bg-[var(--color-accent)]/20 text-[var(--color-accent)]";
}

function formatNextReview(value: string | null): string {
  if (value === null) {
    return "No review date";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "No review date";
  }
  return parsed.toLocaleDateString();
}

export function WatchlistRow({
  entry,
  isActive,
  onSelect,
  onRemove,
}: WatchlistRowProps) {
  const ticker = entry.ticker;

  return (
    <div
      className={cn(
        "space-y-2 rounded-sm border border-[var(--color-border)] px-2 py-2 transition-colors",
        isActive ? "bg-[var(--color-accent)]/15" : "bg-[var(--color-bg-elevated)] hover:bg-[var(--color-bg-panel)]",
      )}
    >
      <button
        type="button"
        className="block w-full text-left"
        onClick={() => {
          if (ticker) {
            onSelect(ticker);
          }
        }}
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="font-mono text-xs text-[var(--color-text-primary)]">
              {entry.name}
            </p>
            <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
              {ticker ?? "—"}
            </p>
          </div>
          <ScoreBadge score={entry.total_score} />
        </div>
      </button>

      <div className="flex items-center justify-between gap-2">
        <span
          className={cn(
            "rounded-sm border px-2 py-0.5 font-mono text-[11px] uppercase",
            statusToneClass(entry.status),
          )}
        >
          {entry.status}
        </span>
        {ticker ? (
          <WatchlistStatusSelect ticker={ticker} status={entry.status} />
        ) : null}
      </div>

      <div className="flex items-center justify-between gap-2">
        <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
          Next review: {formatNextReview(entry.next_review_at)}
        </p>
        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          className="text-[var(--color-negative)] hover:text-[var(--color-negative)]"
          disabled={!ticker}
          onClick={() => {
            if (ticker) {
              onRemove(ticker);
            }
          }}
          aria-label="Remove from watchlist"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
