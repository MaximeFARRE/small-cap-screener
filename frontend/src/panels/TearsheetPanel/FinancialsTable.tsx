import { useMemo, useState } from "react";
import type { HistoricalFundamentals, HistoricalMetricPoint } from "@/hooks";
import { cn } from "@/lib/utils";

interface FinancialsTableProps {
  historical: HistoricalFundamentals;
}

interface FinancialRowDefinition {
  key: string;
  label: string;
  absolutePoints: HistoricalMetricPoint[];
  growthPoints: HistoricalMetricPoint[];
  cagr: number | null;
  format: "currency" | "percent" | "ratio";
}

const CURRENCY_COMPACT = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const PERCENT = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
});

function valueForYear(points: HistoricalMetricPoint[], fiscalYear: number): number | null {
  return points.find((point) => point.fiscal_year === fiscalYear)?.value ?? null;
}

function cagrFromPoints(points: HistoricalMetricPoint[]): number | null {
  if (points.length < 2) {
    return null;
  }

  const newest = points[0];
  const oldest = points[points.length - 1];
  if (!newest || !oldest || newest.value <= 0 || oldest.value <= 0) {
    return null;
  }

  const periods = newest.fiscal_year - oldest.fiscal_year;
  if (periods <= 0) {
    return null;
  }
  return Math.pow(newest.value / oldest.value, 1 / periods) - 1;
}

function formatCurrency(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return CURRENCY_COMPACT.format(value);
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return PERCENT.format(value);
}

function formatRatio(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return `${value.toFixed(2)}x`;
}

function formatValue(value: number | null, format: FinancialRowDefinition["format"]): string {
  if (format === "percent") return formatPercent(value);
  if (format === "ratio") return formatRatio(value);
  return formatCurrency(value);
}

export function FinancialsTable({ historical }: FinancialsTableProps) {
  const [mode, setMode] = useState<"absolute" | "growth">("absolute");
  const anomalySet = useMemo(
    () =>
      new Set(
        historical.financial_anomalies.map((item) => `${item.metric_key}:${item.fiscal_year}:${item.kind}`),
      ),
    [historical.financial_anomalies],
  );

  const rows: FinancialRowDefinition[] = [
    {
      key: "revenue",
      label: "Revenue",
      absolutePoints: historical.revenue_history,
      growthPoints: historical.revenue_growth_history,
      cagr: historical.revenue_cagr ?? cagrFromPoints(historical.revenue_history),
      format: "currency",
    },
    {
      key: "ebitda",
      label: "EBITDA",
      absolutePoints: historical.ebitda_history,
      growthPoints: historical.ebitda_growth_history,
      cagr: cagrFromPoints(historical.ebitda_history),
      format: "currency",
    },
    {
      key: "net_income",
      label: "Net Income",
      absolutePoints: historical.net_income_history,
      growthPoints: historical.net_income_growth_history,
      cagr: historical.net_income_cagr ?? cagrFromPoints(historical.net_income_history),
      format: "currency",
    },
    {
      key: "free_cash_flow",
      label: "FCF",
      absolutePoints: historical.free_cash_flow_history,
      growthPoints: historical.free_cash_flow_growth_history,
      cagr: historical.free_cash_flow_cagr ?? cagrFromPoints(historical.free_cash_flow_history),
      format: "currency",
    },
    {
      key: "operating_cash_flow",
      label: "Operating Cash Flow",
      absolutePoints: historical.operating_cash_flow_history,
      growthPoints: [],
      cagr: cagrFromPoints(historical.operating_cash_flow_history),
      format: "currency",
    },
    {
      key: "capex",
      label: "CAPEX",
      absolutePoints: historical.capex_history,
      growthPoints: historical.capex_growth_history,
      cagr: cagrFromPoints(historical.capex_history),
      format: "currency",
    },
    {
      key: "capex_to_revenue",
      label: "CAPEX / Revenue",
      absolutePoints: historical.capex_to_revenue_history,
      growthPoints: [],
      cagr: null,
      format: "percent",
    },
    {
      key: "working_capital",
      label: "Working Capital",
      absolutePoints: historical.working_capital_history,
      growthPoints: historical.working_capital_growth_history,
      cagr: cagrFromPoints(historical.working_capital_history),
      format: "currency",
    },
    {
      key: "net_debt",
      label: "Net Debt",
      absolutePoints: historical.net_debt_history,
      growthPoints: [],
      cagr: cagrFromPoints(historical.net_debt_history),
      format: "currency",
    },
    {
      key: "asset_turnover",
      label: "Asset Turnover",
      absolutePoints: historical.asset_turnover_history,
      growthPoints: [],
      cagr: null,
      format: "ratio",
    },
    {
      key: "equity_multiplier",
      label: "Equity Multiplier",
      absolutePoints: historical.equity_multiplier_history,
      growthPoints: [],
      cagr: null,
      format: "ratio",
    },
  ];

  const years = Array.from(
    new Set(
      rows.flatMap((row) => row.absolutePoints.map((point) => point.fiscal_year)),
    ),
  )
    .sort((left, right) => right - left)
    .slice(0, 5);

  return (
    <section className="overflow-auto p-4">
      <div className="mb-3 flex gap-1">
        {(["absolute", "growth"] as const).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setMode(key)}
            className={cn(
              "rounded-sm border px-2 py-1 font-mono text-xs",
              mode === key
                ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white"
                : "border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)]",
            )}
          >
            {key === "absolute" ? "Absolute values" : "Growth (% YoY)"}
          </button>
        ))}
      </div>
      <table className="w-full min-w-[760px] table-fixed border-separate border-spacing-y-1">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-2 py-2 text-left font-mono text-xs uppercase text-[var(--color-text-muted)]">
              Metric
            </th>
            {years.map((year) => (
              <th
                key={year}
                className="px-2 py-2 text-right font-mono text-xs uppercase text-[var(--color-text-muted)]"
              >
                {year}
              </th>
            ))}
            <th className="px-2 py-2 text-right font-mono text-xs uppercase text-[var(--color-text-muted)]">
              CAGR
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-b border-[var(--color-border)]">
              <td className="px-2 py-2 font-mono text-xs text-[var(--color-text-primary)]">
                {row.label}
              </td>
              {years.map((year) => {
                const value = valueForYear(row.absolutePoints, year);
                const yoyChange = valueForYear(row.growthPoints, year);
                const isNegativeEbitda = anomalySet.has(`${row.key}:${year}:negative`);
                const hasStrongDrop = anomalySet.has(`${row.key}:${year}:strong_drop`);
                const toneClass =
                  isNegativeEbitda || hasStrongDrop
                    ? "text-[var(--color-negative)]"
                    : "text-[var(--color-text-primary)]";

                return (
                  <td key={`${row.key}-${year}`} className={cn("px-2 py-2 text-right", toneClass)}>
                    <div className="font-mono text-xs">
                      {mode === "absolute" ? formatValue(value, row.format) : formatPercent(yoyChange)}
                    </div>
                    <div className="font-mono text-[11px] text-[var(--color-text-muted)]">
                      {mode === "absolute" ? formatPercent(yoyChange) : formatValue(value, row.format)}
                    </div>
                  </td>
                );
              })}
              <td className="px-2 py-2 text-right font-mono text-xs text-[var(--color-accent)]">
                {row.format === "currency" ? formatPercent(row.cagr) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
