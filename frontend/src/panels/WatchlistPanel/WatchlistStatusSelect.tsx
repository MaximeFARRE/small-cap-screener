import { useMemo } from "react";
import { toast } from "sonner";
import {
  useUpdateWatchlistStatus,
  type WatchlistStatus,
} from "@/hooks";

interface WatchlistStatusSelectProps {
  ticker: string;
  status: string;
}

const STATUS_OPTIONS: Array<{ value: WatchlistStatus; label: string }> = [
  { value: "watching", label: "Watching" },
  { value: "review", label: "Review" },
  { value: "conviction", label: "Conviction" },
  { value: "rejected", label: "Rejected" },
];

function normalizeStatus(status: string): WatchlistStatus {
  const normalized = status.toLowerCase();
  if (
    normalized === "watching" ||
    normalized === "review" ||
    normalized === "conviction" ||
    normalized === "rejected"
  ) {
    return normalized;
  }
  return "watching";
}

export function WatchlistStatusSelect({
  ticker,
  status,
}: WatchlistStatusSelectProps) {
  const updateStatus = useUpdateWatchlistStatus();

  const current = useMemo(() => normalizeStatus(status), [status]);

  return (
    <select
      value={current}
      disabled={updateStatus.isPending}
      onChange={(event) =>
        updateStatus.mutate(
          {
            ticker,
            status: event.target.value as WatchlistStatus,
          },
          {
            onSuccess: () => {
              toast.success(`${ticker} status updated`);
            },
          },
        )
      }
      className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1 font-mono text-[11px] text-[var(--color-text-primary)]"
      aria-label="Watchlist status"
    >
      {STATUS_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
