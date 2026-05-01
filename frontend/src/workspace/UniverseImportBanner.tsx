import { useEffect, useMemo, useState } from "react";
import {
  UNIVERSE_IMPORT_STATUS_EVENT,
  type UniverseImportStatusDetail,
} from "@/lib/universeImportEvents";

const AUTO_HIDE_DELAY_MS = 8000;

function clampProgress(processed: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  const ratio = (processed / total) * 100;
  return Math.max(0, Math.min(100, ratio));
}

export function UniverseImportBanner() {
  const [status, setStatus] = useState<UniverseImportStatusDetail | null>(null);

  useEffect(() => {
    const onStatus = (event: Event) => {
      const detail = (event as CustomEvent<UniverseImportStatusDetail>).detail;
      setStatus(detail);
    };

    window.addEventListener(UNIVERSE_IMPORT_STATUS_EVENT, onStatus);
    return () => window.removeEventListener(UNIVERSE_IMPORT_STATUS_EVENT, onStatus);
  }, []);

  useEffect(() => {
    if (!status || status.phase === "running" || status.phase === "discovery_done") {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setStatus(null);
    }, AUTO_HIDE_DELAY_MS);
    return () => window.clearTimeout(timeoutId);
  }, [status]);

  const progress = useMemo(() => {
    if (!status) {
      return 0;
    }
    return clampProgress(status.processed ?? 0, status.total ?? 0);
  }, [status]);

  if (!status) {
    return null;
  }

  const toneClassName =
    status.phase === "error"
      ? "border-[var(--color-negative)] bg-[var(--color-negative)]/10"
      : status.phase === "completed"
        ? "border-[var(--color-positive)] bg-[var(--color-positive)]/10"
        : "border-[var(--color-accent)] bg-[var(--color-accent)]/10";

  return (
    <section className={`rounded-sm border px-3 py-2 ${toneClassName}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="font-mono text-xs text-[var(--color-text-primary)]">{status.message}</p>
        <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
          {status.total && status.total > 0 ? `${status.processed ?? 0}/${status.total}` : "—"}
        </p>
      </div>
      {status.total && status.total > 0 ? (
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-sm bg-[var(--color-bg-elevated)]">
          <div
            className="h-full rounded-sm bg-[var(--color-accent)] transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      ) : null}
      {status.phase === "completed" ? (
        <p className="mt-1 font-mono text-[11px] text-[var(--color-text-muted)]">
          succès: {status.succeeded ?? 0} · échecs: {status.failed ?? 0} · ignorées: {status.skipped ?? 0}
        </p>
      ) : null}
    </section>
  );
}
