import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface SectionHeaderProps {
  title: string;
  count: number;
  collapsed: boolean;
  onToggle: () => void;
}

export function SectionHeader({
  title,
  count,
  collapsed,
  onToggle,
}: SectionHeaderProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="flex w-full items-center justify-between rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5 text-left"
    >
      <span className="inline-flex items-center gap-2">
        {collapsed ? (
          <ChevronRight className="h-3.5 w-3.5 text-[var(--color-text-muted)]" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-[var(--color-text-muted)]" />
        )}
        <span className="font-mono text-xs uppercase text-[var(--color-text-primary)]">
          {title}
        </span>
      </span>

      <span
        className={cn(
          "rounded-sm border px-1.5 py-0.5 font-mono text-[11px]",
          count > 0
            ? "border-[var(--color-accent)]/40 text-[var(--color-accent)]"
            : "border-[var(--color-border)] text-[var(--color-text-muted)]",
        )}
      >
        {count}
      </span>
    </button>
  );
}
