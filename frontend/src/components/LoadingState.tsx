interface LoadingStateProps {
  label?: string;
}

export function LoadingState({ label = "Loading data…" }: LoadingStateProps) {
  return (
    <div className="flex h-full w-full items-center justify-center p-4">
      <div className="flex items-center gap-2 rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-3 py-2">
        <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--color-accent)]" />
        <p className="font-mono text-sm text-[var(--color-text-muted)]">{label}</p>
      </div>
    </div>
  );
}
