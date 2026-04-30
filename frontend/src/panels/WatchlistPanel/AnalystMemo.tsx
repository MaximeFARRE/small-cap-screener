import { useEffect, useMemo, useRef, useState } from "react";
import type { AnalystMemo as AnalystMemoValue } from "@/hooks";

interface AnalystMemoProps {
  ticker: string;
  memo: AnalystMemoValue;
  onSave: (ticker: string, memo: AnalystMemoValue) => Promise<void>;
}

type SaveState = "idle" | "saving" | "saved" | "error";

const DEBOUNCE_MS = 300;
const SAVED_BADGE_MS = 1500;

function memoSnapshot(memo: AnalystMemoValue): string {
  return JSON.stringify(memo);
}

export function AnalystMemo({ ticker, memo, onSave }: AnalystMemoProps) {
  const [draft, setDraft] = useState<AnalystMemoValue>(memo);
  const [savedSnapshot, setSavedSnapshot] = useState<string>(memoSnapshot(memo));
  const [saveState, setSaveState] = useState<SaveState>("idle");

  const debounceTimeoutRef = useRef<number | null>(null);
  const savedTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current !== null) {
        window.clearTimeout(debounceTimeoutRef.current);
      }
      if (savedTimeoutRef.current !== null) {
        window.clearTimeout(savedTimeoutRef.current);
      }
    };
  }, []);

  const hasChanges = useMemo(
    () => memoSnapshot(draft) !== savedSnapshot,
    [draft, savedSnapshot],
  );

  const triggerSave = () => {
    if (!hasChanges) {
      return;
    }
    if (debounceTimeoutRef.current !== null) {
      window.clearTimeout(debounceTimeoutRef.current);
    }
    debounceTimeoutRef.current = window.setTimeout(async () => {
      setSaveState("saving");
      try {
        await onSave(ticker, draft);
        const snapshot = memoSnapshot(draft);
        setSavedSnapshot(snapshot);
        setSaveState("saved");

        if (savedTimeoutRef.current !== null) {
          window.clearTimeout(savedTimeoutRef.current);
        }
        savedTimeoutRef.current = window.setTimeout(() => {
          setSaveState("idle");
        }, SAVED_BADGE_MS);
      } catch {
        setSaveState("error");
      }
    }, DEBOUNCE_MS);
  };

  return (
    <section className="flex h-full min-h-0 flex-col border-l border-[var(--color-border)] bg-[var(--color-bg-panel)]">
      <header className="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-2">
        <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">
          Analyst memo · {ticker}
        </p>
        <p
          className={`font-mono text-[11px] transition-opacity ${
            saveState === "saved"
              ? "text-[var(--color-positive)] opacity-100"
              : saveState === "saving"
                ? "text-[var(--color-warning)] opacity-100"
                : saveState === "error"
                  ? "text-[var(--color-negative)] opacity-100"
                  : "opacity-0"
          }`}
        >
          {saveState === "saved"
            ? "Saved ✓"
            : saveState === "saving"
              ? "Saving…"
              : saveState === "error"
                ? "Save failed"
                : ""}
        </p>
      </header>

      <div className="grid min-h-0 flex-1 gap-2 overflow-auto p-3">
        <label className="space-y-1">
          <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Thesis</span>
          <textarea
            value={draft.investment_thesis ?? ""}
            onChange={(event) =>
              setDraft((current) => ({ ...current, investment_thesis: event.target.value }))
            }
            onBlur={triggerSave}
            rows={4}
            className="w-full resize-y rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2 font-mono text-xs text-[var(--color-text-primary)]"
          />
        </label>

        <label className="space-y-1">
          <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Risks</span>
          <textarea
            value={draft.key_risks ?? ""}
            onChange={(event) =>
              setDraft((current) => ({ ...current, key_risks: event.target.value }))
            }
            onBlur={triggerSave}
            rows={3}
            className="w-full resize-y rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2 font-mono text-xs text-[var(--color-text-primary)]"
          />
        </label>

        <label className="space-y-1">
          <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Catalysts</span>
          <textarea
            value={draft.catalysts ?? ""}
            onChange={(event) =>
              setDraft((current) => ({ ...current, catalysts: event.target.value }))
            }
            onBlur={triggerSave}
            rows={3}
            className="w-full resize-y rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2 font-mono text-xs text-[var(--color-text-primary)]"
          />
        </label>

        <label className="space-y-1">
          <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Valuation notes</span>
          <textarea
            value={draft.valuation_notes ?? ""}
            onChange={(event) =>
              setDraft((current) => ({ ...current, valuation_notes: event.target.value }))
            }
            onBlur={triggerSave}
            rows={3}
            className="w-full resize-y rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2 font-mono text-xs text-[var(--color-text-primary)]"
          />
        </label>

        <label className="space-y-1">
          <span className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">Next action</span>
          <textarea
            value={draft.next_action ?? ""}
            onChange={(event) =>
              setDraft((current) => ({ ...current, next_action: event.target.value }))
            }
            onBlur={triggerSave}
            rows={2}
            className="w-full resize-y rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2 font-mono text-xs text-[var(--color-text-primary)]"
          />
        </label>
      </div>
    </section>
  );
}
