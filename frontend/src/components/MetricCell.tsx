import { METRIC_THRESHOLDS, type MetricDirection } from "@/lib/constants";
import { formatMarketCap, formatPercent, formatRatio } from "@/lib/formatters";
import { cn } from "@/lib/utils";

export type MetricType = keyof typeof METRIC_THRESHOLDS | "market_cap";
export type MetricFormat = "ratio" | "percent" | "currency";

interface MetricCellProps {
  value: number | null;
  type: MetricType;
  format: MetricFormat;
}

function resolveDirectionalTone(
  value: number,
  direction: MetricDirection,
  good: number,
  warning: number,
): string {
  if (direction === "higher_is_better") {
    if (value >= good) {
      return "text-[var(--color-positive)]";
    }
    if (value < warning) {
      return "text-[var(--color-negative)]";
    }
    return "text-[var(--color-warning)]";
  }

  if (value <= good) {
    return "text-[var(--color-positive)]";
  }
  if (value > warning) {
    return "text-[var(--color-negative)]";
  }
  return "text-[var(--color-warning)]";
}

function formatMetric(value: number | null, format: MetricFormat): string {
  if (value === null) {
    return "—";
  }
  if (format === "percent") {
    return formatPercent(value);
  }
  if (format === "currency") {
    return formatMarketCap(value);
  }
  return formatRatio(value);
}

export function MetricCell({ value, type, format }: MetricCellProps) {
  if (value === null) {
    return <span className="font-mono text-xs text-[var(--color-text-muted)]">—</span>;
  }

  const rule = type === "market_cap" ? null : METRIC_THRESHOLDS[type];
  const toneClassName = rule
    ? resolveDirectionalTone(value, rule.direction, rule.good, rule.warning)
    : "text-[var(--color-text-primary)]";

  return (
    <span className={cn("font-mono text-xs", toneClassName)}>
      {formatMetric(value, format)}
    </span>
  );
}
