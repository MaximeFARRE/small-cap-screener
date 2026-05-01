import { X } from "lucide-react";

interface ShortcutsModalProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS: Array<{ key: string; action: string }> = [
  { key: "S", action: "Focus screener filters" },
  { key: "W", action: "Focus watchlist panel" },
  { key: "J / K", action: "Navigate rows in focused table" },
  { key: "Enter", action: "Open tearsheet for selected row" },
  { key: "Esc", action: "Clear active ticker" },
  { key: "?", action: "Open shortcuts help" },
];

export function ShortcutsModal({ open, onClose }: ShortcutsModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <section className="w-full max-w-lg rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-panel)]">
        <header className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3">
          <div>
            <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Keyboard shortcuts</p>
            <p className="font-mono text-[11px] text-[var(--color-text-muted)]">Global commands</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-1 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
            aria-label="Close shortcuts modal"
          >
            <X className="h-4 w-4" />
          </button>
        </header>
        <ul className="space-y-2 p-4">
          {SHORTCUTS.map((shortcut) => (
            <li
              key={shortcut.key}
              className="flex items-center justify-between rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-3 py-2"
            >
              <kbd className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-2 py-0.5 font-mono text-xs text-[var(--color-text-primary)]">
                {shortcut.key}
              </kbd>
              <span className="font-mono text-xs text-[var(--color-text-muted)]">{shortcut.action}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
