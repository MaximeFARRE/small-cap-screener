import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScoreBadge } from "@/components/ScoreBadge";
import type { CompanyDetail, CompanyScore, ScoreMetricDriver } from "@/hooks";
import { formatMarketCap, formatNumber, formatPercent, formatRatio } from "@/lib/formatters";

interface TearsheetHeroProps {
  detail: CompanyDetail;
  score: CompanyScore;
  isInWatchlist: boolean;
  watchlistActionPending: boolean;
  onAddToWatchlist: () => void;
  onRemoveFromWatchlist: () => void;
}

interface DriverCard {
  category: string;
  label: string;
  metric: string;
  value: number;
}

function formatMetricValue(metric: string, value: number): string {
  const metricName = metric.toLowerCase();
  if (
    metricName.includes("margin") ||
    metricName.includes("yield") ||
    metricName.includes("growth") ||
    metricName.includes("roe") ||
    metricName.includes("roic")
  ) {
    return formatPercent(value);
  }
  if (
    metricName.includes("ratio") ||
    metricName.includes("debt") ||
    metricName.includes("ebitda") ||
    metricName.includes("pe")
  ) {
    return formatRatio(value);
  }
  return formatNumber(value, 2);
}

function firstDriverForCategory(
  category: string,
  drivers: ScoreMetricDriver[],
): ScoreMetricDriver | null {
  const normalized = category.toLowerCase();
  return (
    drivers.find((driver) => driver.category.toLowerCase() === normalized) ?? null
  );
}

function buildDriverCards(score: CompanyScore): DriverCard[] {
  const categories: Array<{ key: string; label: string }> = [
    { key: "quality", label: "Quality" },
    { key: "value", label: "Value" },
    { key: "growth", label: "Growth" },
    { key: "risk", label: "Risk" },
  ];

  return categories.map((category) => {
    const driver = firstDriverForCategory(category.key, score.positive_drivers);
    return {
      category: category.key,
      label: category.label,
      metric: driver?.metric ?? "N/A",
      value: driver?.raw_value ?? 0,
    };
  });
}

export function TearsheetHero({
  detail,
  score,
  isInWatchlist,
  watchlistActionPending,
  onAddToWatchlist,
  onRemoveFromWatchlist,
}: TearsheetHeroProps) {
  const driverCards = buildDriverCards(score);
  const hasTicker = detail.ticker !== null;

  return (
    <section className="space-y-4 border-b border-[var(--color-border)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-mono text-lg font-semibold text-[var(--color-text-primary)]">
            {detail.name}
          </h2>
          <p className="font-mono text-xs text-[var(--color-text-muted)]">
            {detail.ticker ?? "—"} · {detail.country ?? "—"} · {detail.currency}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-0.5 font-mono text-[11px] text-[var(--color-text-muted)]">
              {detail.sector ?? "Unknown sector"}
            </span>
            <span className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-0.5 font-mono text-[11px] text-[var(--color-text-muted)]">
              {detail.industry ?? "Unknown industry"}
            </span>
          </div>
        </div>

        <div className="text-right space-y-2">
          <div className="mb-2">
            <p className="font-mono text-xs uppercase text-[var(--color-text-muted)]">Score</p>
            <ScoreBadge score={score.total_score} />
          </div>
          <p className="font-mono text-sm text-[var(--color-text-primary)]">
            Price: {detail.current_price === null ? "—" : formatNumber(detail.current_price, 2)}
          </p>
          <p className="font-mono text-xs text-[var(--color-text-muted)]">
            Market cap: {formatMarketCap(detail.market_cap)}
          </p>

          {hasTicker ? (
            isInWatchlist ? (
              <Button
                type="button"
                size="sm"
                variant="destructive"
                className="w-full justify-center font-mono text-xs"
                disabled={watchlistActionPending}
                onClick={onRemoveFromWatchlist}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remove from watchlist
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="w-full justify-center font-mono text-xs"
                disabled={watchlistActionPending}
                onClick={onAddToWatchlist}
              >
                <Plus className="h-3.5 w-3.5" />
                Add to watchlist
              </Button>
            )
          ) : null}
        </div>
      </div>

      <div className="grid gap-2 md:grid-cols-4">
        {driverCards.map((card) => (
          <div
            key={card.category}
            className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2"
          >
            <p className="font-mono text-[11px] uppercase text-[var(--color-text-muted)]">
              {card.label}
            </p>
            <p className="truncate font-mono text-xs text-[var(--color-text-primary)]">
              {card.metric}
            </p>
            <p className="font-mono text-xs text-[var(--color-accent)]">
              {card.metric === "N/A" ? "—" : formatMetricValue(card.metric, card.value)}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
