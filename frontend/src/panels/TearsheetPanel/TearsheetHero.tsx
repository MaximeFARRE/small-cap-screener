import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SCORE_THRESHOLDS } from "@/lib/constants";
import type { CompanyDetail, CompanyScore, ScoreMetricDriver } from "@/hooks";
import {
  formatMarketCap,
  formatNumber,
  formatPercent,
  formatRatio,
} from "@/lib/formatters";

interface TearsheetHeroProps {
  detail: CompanyDetail;
  score: CompanyScore;
  isInWatchlist: boolean;
  watchlistActionPending: boolean;
  onAddToWatchlist: () => void;
  onRemoveFromWatchlist: () => void;
}

interface KpiCard {
  category: string;
  title: string;
  subScore: number | null;
  metric: string | null;
  rawValue: number | null;
}

function scoreColorClass(score: number | null): string {
  if (score === null) return "text-[var(--color-text-muted)]";
  if (score >= SCORE_THRESHOLDS.HIGH) return "text-[var(--color-positive)]";
  if (score >= SCORE_THRESHOLDS.MID) return "text-[var(--color-warning)]";
  return "text-[var(--color-negative)]";
}

function qualityBadgeLabel(score: number | null): string {
  if (score === null) return "—";
  if (score >= SCORE_THRESHOLDS.HIGH) return "HIGH";
  if (score >= SCORE_THRESHOLDS.MID) return "MID";
  return "LOW";
}

function qualityBadgeClass(score: number | null): string {
  if (score === null)
    return "text-[var(--color-text-muted)] border-[var(--color-border)]";
  if (score >= SCORE_THRESHOLDS.HIGH)
    return "text-[var(--color-positive)] border-[var(--color-positive)]/40";
  if (score >= SCORE_THRESHOLDS.MID)
    return "text-[var(--color-warning)] border-[var(--color-warning)]/40";
  return "text-[var(--color-negative)] border-[var(--color-negative)]/40";
}

function formatMetricValue(metric: string, value: number): string {
  const m = metric.toLowerCase();
  if (
    m.includes("margin") ||
    m.includes("yield") ||
    m.includes("growth") ||
    m.includes("roe") ||
    m.includes("roic")
  ) {
    return formatPercent(value);
  }
  if (
    m.includes("ratio") ||
    m.includes("debt") ||
    m.includes("ebitda") ||
    m.includes("pe")
  ) {
    return formatRatio(value);
  }
  return formatNumber(value, 2);
}

function firstDriverForCategory(
  category: string,
  positive: ScoreMetricDriver[],
  negative: ScoreMetricDriver[],
): ScoreMetricDriver | null {
  const norm = category.toLowerCase();
  return (
    positive.find((d) => d.category.toLowerCase() === norm) ??
    negative.find((d) => d.category.toLowerCase() === norm) ??
    null
  );
}

function buildKpiCards(score: CompanyScore): KpiCard[] {
  const categories: Array<{
    key: "quality" | "value" | "growth" | "risk";
    title: string;
  }> = [
    { key: "quality", title: "QUALITY" },
    { key: "value", title: "VALUE" },
    { key: "growth", title: "GROWTH" },
    { key: "risk", title: "RISK" },
  ];

  return categories.map(({ key, title }) => {
    const driver = firstDriverForCategory(
      key,
      score.positive_drivers,
      score.negative_drivers,
    );
    return {
      category: key,
      title,
      subScore: score[key],
      metric: driver?.metric ?? null,
      rawValue: driver?.raw_value ?? null,
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
  const kpiCards = buildKpiCards(score);
  const hasTicker = detail.ticker !== null;
  const totalScore = score.total_score;
  const scoreClass = scoreColorClass(totalScore);
  const badgeLabel = qualityBadgeLabel(totalScore);
  const badgeClass = qualityBadgeClass(totalScore);

  return (
    <section className="border-b border-[var(--color-border)] p-4 space-y-4">
      {/* Identity (left) + Score block (right) */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        {/* LEFT */}
        <div className="min-w-0 flex-1">
          <h2 className="font-mono text-xl font-bold leading-tight text-[var(--color-text-primary)] truncate">
            {detail.name}
          </h2>
          <p className="mt-0.5 font-mono text-xs text-[var(--color-text-muted)]">
            {detail.ticker ?? "—"} · {detail.country ?? "—"} ·{" "}
            {detail.currency}
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {detail.sector && (
              <span className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[var(--color-text-muted)]">
                {detail.sector}
              </span>
            )}
            {detail.industry && (
              <span className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide text-[var(--color-text-muted)]">
                {detail.industry}
              </span>
            )}
          </div>
          {score.summary && (
            <p className="mt-2 font-mono text-[11px] italic text-[var(--color-text-muted)]">
              {score.summary}
            </p>
          )}
        </div>

        {/* RIGHT: dominant score + price + action */}
        <div className="flex shrink-0 flex-col items-end gap-1">
          <div className="flex items-baseline gap-2">
            <span
              className={`font-mono text-5xl font-black leading-none tabular-nums ${scoreClass}`}
            >
              {totalScore === null ? "—" : Math.round(totalScore)}
            </span>
            <span
              className={`rounded-sm border px-1.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-widest ${badgeClass}`}
            >
              {badgeLabel}
            </span>
          </div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-text-muted)]">
            Score
          </p>

          <div className="mt-1 text-right">
            <p className="font-mono text-sm font-semibold text-[var(--color-text-primary)]">
              {detail.current_price === null
                ? "—"
                : `${detail.currency ?? ""} ${formatNumber(detail.current_price, 2)}`}
            </p>
            <p className="font-mono text-[11px] text-[var(--color-text-muted)]">
              MCap {formatMarketCap(detail.market_cap)}
            </p>
          </div>

          {hasTicker &&
            (isInWatchlist ? (
              <Button
                type="button"
                size="sm"
                variant="destructive"
                className="mt-1 font-mono text-xs"
                disabled={watchlistActionPending}
                onClick={onRemoveFromWatchlist}
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remove
              </Button>
            ) : (
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="mt-1 font-mono text-xs"
                disabled={watchlistActionPending}
                onClick={onAddToWatchlist}
              >
                <Plus className="h-3.5 w-3.5" />
                Watchlist
              </Button>
            ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-2 sm:grid-cols-2 md:grid-cols-4">
        {kpiCards.map((card) => {
          const subScoreClass = scoreColorClass(card.subScore);
          const subtext =
            card.metric === null
              ? "—"
              : card.rawValue === null
                ? `${card.metric}: —`
                : `${card.metric}: ${formatMetricValue(card.metric, card.rawValue)}`;

          return (
            <div
              key={card.category}
              className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-3"
            >
              <p className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-text-muted)]">
                {card.title}
              </p>
              <p
                className={`mt-0.5 font-mono text-3xl font-black leading-tight tabular-nums ${subScoreClass}`}
              >
                {card.subScore === null ? "—" : Math.round(card.subScore)}
              </p>
              <p className="mt-0.5 truncate font-mono text-[11px] text-[var(--color-text-muted)]">
                {subtext}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
