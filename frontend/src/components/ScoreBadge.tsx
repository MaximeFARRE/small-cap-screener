import { SCORE_THRESHOLDS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface ScoreBadgeProps {
  score: number | null;
}

export function ScoreBadge({ score }: ScoreBadgeProps) {
  const scoreLabel = score === null ? "—" : Math.round(score).toString();

  const toneClassName =
    score === null
      ? "bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]"
      : score >= SCORE_THRESHOLDS.HIGH
        ? "bg-[var(--color-positive)]/20 text-[var(--color-positive)]"
        : score >= SCORE_THRESHOLDS.MID
          ? "bg-[var(--color-warning)]/20 text-[var(--color-warning)]"
          : "bg-[var(--color-negative)]/20 text-[var(--color-negative)]";

  return (
    <span
      className={cn(
        "inline-flex min-w-10 items-center justify-center rounded-sm px-2 py-0.5 font-mono text-xs font-bold",
        toneClassName,
      )}
      aria-label={score === null ? "Score unavailable" : `Score ${scoreLabel}`}
    >
      {scoreLabel}
    </span>
  );
}
