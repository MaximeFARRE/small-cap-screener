interface EmptyStateProps {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="flex h-full w-full items-center justify-center p-4">
      <div className="space-y-1 rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-4 py-3 text-center">
        <p className="font-mono text-sm text-[var(--color-text-primary)]">{title}</p>
        {description ? (
          <p className="font-mono text-xs text-[var(--color-text-muted)]">{description}</p>
        ) : null}
      </div>
    </div>
  );
}
