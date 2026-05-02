import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { CompanyDetail, CompanyScore, HistoricalFundamentals, ScoreMetricDriver } from "@/hooks";
import { formatMarketCap, formatNumber, formatPercent } from "@/lib/formatters";
import { cn } from "@/lib/utils";

interface ScoreBreakdownProps {
  score: CompanyScore;
  detail?: CompanyDetail;
  historical?: HistoricalFundamentals;
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

function latestGrowth(points: Array<{ fiscal_year: number; value: number }>): number | null {
  if (points.length === 0) return null;
  const sorted = [...points].sort((left, right) => right.fiscal_year - left.fiscal_year);
  return sorted[0]?.value ?? null;
}

function trendClass(value: number | null): string {
  if (value === null) return "text-[var(--color-text-muted)]";
  return value >= 0 ? "text-[var(--color-positive)]" : "text-[var(--color-negative)]";
}

export function ScoreBreakdown({ score, detail, historical }: ScoreBreakdownProps) {
  const bars = useMemo(() => [
    { key: "quality", label: "Quality", value: score.quality },
    { key: "value", label: "Value", value: score.value },
    { key: "growth", label: "Growth", value: score.growth },
    { key: "risk", label: "Risk", value: score.risk },
  ] as const, [score.growth, score.quality, score.risk, score.value]);

  const [animatedWidths, setAnimatedWidths] = useState<Record<string, number>>({
    quality: 0,
    value: 0,
    growth: 0,
    risk: 0,
  });

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      setAnimatedWidths({
        quality: Math.max(0, Math.min(100, score.quality ?? 0)),
        value: Math.max(0, Math.min(100, score.value ?? 0)),
        growth: Math.max(0, Math.min(100, score.growth ?? 0)),
        risk: Math.max(0, Math.min(100, score.risk ?? 0)),
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [score.growth, score.quality, score.risk, score.value, score.total_score]);

  return (
    <section className="space-y-4 border-b border-[var(--color-border)] p-4">
      {detail && historical && (
        <>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-[10px] uppercase text-[var(--color-text-muted)]">Score</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-primary)]">
                {score.total_score === null ? "—" : Math.round(score.total_score)}
              </p>
            </div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-[10px] uppercase text-[var(--color-text-muted)]">Market Cap</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-primary)]">
                {formatMarketCap(detail.market_cap)}
              </p>
            </div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-[10px] uppercase text-[var(--color-text-muted)]">EV</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-primary)]">
                {formatMarketCap(detail.enterprise_value)}
              </p>
            </div>
            <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
              <p className="font-mono text-[10px] uppercase text-[var(--color-text-muted)]">FCF Yield</p>
              <p className="font-mono text-2xl font-bold text-[var(--color-text-primary)]">
                {formatPercent(detail.fcf_yield)}
              </p>
            </div>
          </div>
          <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3">
            <p className="font-mono text-[10px] uppercase text-[var(--color-text-muted)]">Quick verdict</p>
            <p className="mt-1 text-sm text-[var(--color-text-primary)]">{score.summary}</p>
          </div>
          <div className="grid gap-2 md:grid-cols-3">
            {[
              { label: "Revenue growth", value: detail.revenue_growth },
              { label: "EBITDA growth", value: detail.ebitda_growth },
              { label: "FCF growth", value: latestGrowth(historical.free_cash_flow_growth_history) },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3"
              >
                <p className="font-mono text-[10px] uppercase text-[var(--color-text-muted)]">{item.label}</p>
                <p className={cn("font-mono text-xl font-semibold", trendClass(item.value))}>
                  {formatPercent(item.value)}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
      <div className="flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">
            Score Breakdown
          </p>
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
          const width = animatedWidths[bar.key];
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
                  className="h-full bg-[var(--color-accent)] transition-[width] duration-700 ease-out"
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
