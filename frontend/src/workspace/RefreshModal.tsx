import { useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { LoaderCircle, Play, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { openRefreshStream, type RefreshProgressEvent } from "@/hooks";

interface RefreshModalProps {
  open: boolean;
  onClose: () => void;
}

interface RefreshResultRow {
  id: string;
  ticker: string;
  success: boolean;
  error: string | null;
  pricesAdded: number;
  statementsAdded: number;
}

export function RefreshModal({ open, onClose }: RefreshModalProps) {
  const queryClient = useQueryClient();
  const sourceRef = useRef<EventSource | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [total, setTotal] = useState(0);
  const [completed, setCompleted] = useState(0);
  const [rows, setRows] = useState<RefreshResultRow[]>([]);

  useEffect(() => {
    if (!open && sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
      setIsRunning(false);
    }
  }, [open]);

  useEffect(() => {
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
    };
  }, []);

  const successCount = useMemo(() => rows.filter((row) => row.success).length, [rows]);
  const failureCount = useMemo(() => rows.filter((row) => !row.success).length, [rows]);

  const startRefresh = () => {
    if (isRunning) {
      return;
    }

    setRows([]);
    setCompleted(0);
    setTotal(0);
    setIsRunning(true);

    sourceRef.current = openRefreshStream({
      onStart: (payload) => {
        setTotal(payload.total);
      },
      onProgress: (payload: RefreshProgressEvent) => {
        setCompleted(payload.index);
        setRows((current) => [
          ...current,
          {
            id: `${payload.company_id}-${payload.index}`,
            ticker: payload.ticker,
            success: payload.success,
            error: payload.error,
            pricesAdded: payload.prices_added,
            statementsAdded: payload.statements_added,
          },
        ]);
      },
      onDone: async () => {
        setIsRunning(false);
        sourceRef.current = null;
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["screening", "universe"] }),
          queryClient.invalidateQueries({ queryKey: ["signals"] }),
          queryClient.invalidateQueries({ queryKey: ["watchlist"] }),
          queryClient.invalidateQueries({ queryKey: ["companies"] }),
        ]);
        toast.success("Data refresh complete");
      },
      onError: (message) => {
        setIsRunning(false);
        sourceRef.current = null;
        toast.error(message);
      },
    });
  };

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section className="flex h-[80vh] w-full max-w-3xl min-h-0 flex-col rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-panel)]">
        <header className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
          <div>
            <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Data refresh</p>
            <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
              {total > 0 ? `${completed}/${total} processed` : "Ready to refresh investable universe"}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            aria-label="Close refresh modal"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="border-b border-[var(--color-border)] px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              size="sm"
              variant="default"
              disabled={isRunning}
              className="font-mono text-xs"
              onClick={startRefresh}
            >
              {isRunning ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              {isRunning ? "Refreshing…" : "Start refresh"}
            </Button>
            <span className="font-mono text-[11px] text-[var(--color-positive)]">Success: {successCount}</span>
            <span className="font-mono text-[11px] text-[var(--color-negative)]">Failed: {failureCount}</span>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto p-4">
          {rows.length === 0 ? (
            <p className="font-mono text-xs text-[var(--color-text-muted)]">No refresh events yet.</p>
          ) : (
            <ul className="space-y-2">
              {rows.map((row) => (
                <li
                  key={row.id}
                  className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-xs text-[var(--color-text-primary)]">{row.ticker}</p>
                    <p
                      className={`font-mono text-[11px] uppercase ${
                        row.success ? "text-[var(--color-positive)]" : "text-[var(--color-negative)]"
                      }`}
                    >
                      {row.success ? "ok" : "error"}
                    </p>
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-[var(--color-text-muted)]">
                    prices +{row.pricesAdded} · statements +{row.statementsAdded}
                  </p>
                  {row.error ? (
                    <p className="mt-1 font-mono text-[11px] text-[var(--color-negative)]">{row.error}</p>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}
