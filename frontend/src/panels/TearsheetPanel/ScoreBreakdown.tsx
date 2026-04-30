import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import type { CompanyScore, ScoreMetricDriver } from "@/hooks";
import { formatNumber } from "@/lib/formatters";

interface ScoreBreakdownProps {
  score: CompanyScore;
}

function DriverRow({
  driver,
  tone,
}: {
  driver: ScoreMetricDriver;
  tone: "positive" | "negative";
}) {
  const isPositive = tone === "positive";

  return (
    <li className="flex items-center justify-between gap-2 rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-1.5">
      <div className="flex items-center gap-1.5">
        {isPositive ? (
          <ArrowUpRight className="h-3.5 w-3.5 text-[var(--color-positive)]" />
        ) : (
          <ArrowDownRight className="h-3.5 w-3.5 text-[var(--color-negative)]" />
        )}
        <span className="font-mono text-xs text-[var(--color-text-primary)]">
          {driver.metric}
        </span>
      </div>
      <span className="font-mono text-xs text-[var(--color-text-muted)]">
        {formatNumber(driver.raw_value, 2)}
      </span>
    </li>
  );
}

export function ScoreBreakdown({ score }: ScoreBreakdownProps) {
  const bars = [
    { key: "quality", label: "Quality", value: score.quality },
    { key: "value", label: "Value", value: score.value },
    { key: "growth", label: "Growth", value: score.growth },
    { key: "risk", label: "Risk", value: score.risk },
  ] as const;

  return (
    <section className="space-y-4 border-b border-[var(--color-border)] p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">
            Score Breakdown
          </p>
          <p className="font-mono text-sm text-[var(--color-text-muted)]">{score.summary}</p>
        </div>
        <div className="text-right">
          <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Overall</p>
          <p className="font-mono text-2xl font-bold text-[var(--color-text-primary)]">
            {score.total_score === null ? "—" : Math.round(score.total_score)}
          </p>
        </div>
      </div>

      <div className="grid gap-2 md:grid-cols-2">
        {bars.map((bar) => {
          const value = bar.value ?? 0;
          const width = Math.max(0, Math.min(100, value));
          return (
            <div key={bar.key} className="space-y-1 rounded-sm border border-[var(--color-border)] p-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-[var(--color-text-muted)]">{bar.label}</span>
                <span className="font-mono text-xs text-[var(--color-text-primary)]">
                  {bar.value === null ? "—" : formatNumber(bar.value, 1)}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded bg-[var(--color-bg-elevated)]">
                <div
                  className="h-full bg-[var(--color-accent)] transition-all"
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="space-y-2">
          <p className="font-mono text-xs uppercase text-[var(--color-positive)]">Positive drivers</p>
          <ul className="space-y-1">
            {score.positive_drivers.slice(0, 3).map((driver) => (
              <DriverRow key={`${driver.category}:${driver.metric}`} driver={driver} tone="positive" />
            ))}
          </ul>
        </div>
        <div className="space-y-2">
          <p className="font-mono text-xs uppercase text-[var(--color-negative)]">Negative drivers</p>
          <ul className="space-y-1">
            {score.negative_drivers.slice(0, 3).map((driver) => (
              <DriverRow key={`${driver.category}:${driver.metric}`} driver={driver} tone="negative" />
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
