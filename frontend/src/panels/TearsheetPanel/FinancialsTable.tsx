import type { HistoricalFundamentals, HistoricalMetricPoint } from "@/hooks";
import { cn } from "@/lib/utils";

interface FinancialsTableProps {
  historical: HistoricalFundamentals;
}

interface FinancialRowDefinition {
  key: string;
  label: string;
  points: HistoricalMetricPoint[];
  cagr: number | null;
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

function yoy(current: number | null, previous: number | null): number | null {
  if (current === null || previous === null || previous === 0) {
    return null;
  }
  return (current - previous) / Math.abs(previous);
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

export function FinancialsTable({ historical }: FinancialsTableProps) {
  const rows: FinancialRowDefinition[] = [
    {
      key: "revenue",
      label: "Revenue",
      points: historical.revenue_history,
      cagr: historical.revenue_cagr ?? cagrFromPoints(historical.revenue_history),
    },
    {
      key: "ebitda",
      label: "EBITDA",
      points: historical.ebitda_history,
      cagr: cagrFromPoints(historical.ebitda_history),
    },
    {
      key: "net_income",
      label: "Net Income",
      points: historical.net_income_history,
      cagr: historical.net_income_cagr ?? cagrFromPoints(historical.net_income_history),
    },
    {
      key: "free_cash_flow",
      label: "FCF",
      points: historical.free_cash_flow_history,
      cagr: historical.free_cash_flow_cagr ?? cagrFromPoints(historical.free_cash_flow_history),
    },
    {
      key: "total_assets",
      label: "Total Assets",
      points: [],
      cagr: null,
    },
    {
      key: "net_debt",
      label: "Net Debt",
      points: historical.net_debt_history,
      cagr: cagrFromPoints(historical.net_debt_history),
    },
  ];

  const years = Array.from(
    new Set(
      rows.flatMap((row) => row.points.map((point) => point.fiscal_year)),
    ),
  )
    .sort((left, right) => right - left)
    .slice(0, 5);

  return (
    <section className="overflow-auto p-4">
      <table className="w-full min-w-[760px] table-fixed border-collapse">
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
              {years.map((year, index) => {
                const value = valueForYear(row.points, year);
                const previousYear = years[index + 1];
                const previousValue =
                  previousYear === undefined ? null : valueForYear(row.points, previousYear);
                const yoyChange = yoy(value, previousValue);

                return (
                  <td key={`${row.key}-${year}`} className="px-2 py-2 text-right">
                    <div className="font-mono text-xs text-[var(--color-text-primary)]">
                      {formatCurrency(value)}
                    </div>
                    <div
                      className={cn(
                        "font-mono text-[11px]",
                        yoyChange === null
                          ? "text-[var(--color-text-muted)]"
                          : yoyChange >= 0
                            ? "text-[var(--color-positive)]"
                            : "text-[var(--color-negative)]",
                      )}
                    >
                      {formatPercent(yoyChange)}
                    </div>
                  </td>
                );
              })}
              <td className="px-2 py-2 text-right font-mono text-xs text-[var(--color-accent)]">
                {formatPercent(row.cagr)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
