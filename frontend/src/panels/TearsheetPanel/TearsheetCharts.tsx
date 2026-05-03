import { useMemo } from "react";
import {
  CartesianGrid,
  Area,
  AreaChart,
  Bar,
  BarChart,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HistoricalFundamentals } from "@/hooks";
import { COLORS } from "@/lib/constants";

interface TearsheetChartsProps {
  historical: HistoricalFundamentals;
}

export function TearsheetCharts({ historical }: TearsheetChartsProps) {
  const revEbitdaData = useMemo(() => {
    const byYear = new Map<number, { year: number; revenue?: number; ebitda?: number }>();

    for (const point of historical.revenue_history) {
      byYear.set(point.fiscal_year, {
        ...(byYear.get(point.fiscal_year) ?? { year: point.fiscal_year }),
        revenue: point.value,
      });
    }
    for (const point of historical.ebitda_history) {
      byYear.set(point.fiscal_year, {
        ...(byYear.get(point.fiscal_year) ?? { year: point.fiscal_year }),
        ebitda: point.value,
      });
    }

    return [...byYear.values()]
      .sort((left, right) => left.year - right.year)
      .map((row) => ({
        year: row.year,
        revenue: row.revenue ?? null,
        ebitda: row.ebitda ?? null,
      }));
  }, [historical.ebitda_history, historical.revenue_history]);
  const marginData = useMemo(
    () =>
      [...historical.ebitda_margin_history]
        .sort((left, right) => left.fiscal_year - right.fiscal_year)
        .map((point) => ({ year: point.fiscal_year, margin: point.value * 100 })),
    [historical.ebitda_margin_history],
  );
  const fcfData = useMemo(
    () =>
      [...historical.free_cash_flow_history]
        .sort((left, right) => left.fiscal_year - right.fiscal_year)
        .map((point) => ({ year: point.fiscal_year, fcf: point.value })),
    [historical.free_cash_flow_history],
  );

  return (
    <section className="grid min-h-0 gap-3 p-4 xl:grid-cols-3">
      <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2">
        <p className="mb-2 font-mono text-xs uppercase text-[var(--color-text-muted)]">
          Revenue + EBITDA
        </p>
        {revEbitdaData.length === 0 ? (
          <div className="flex h-64 items-center justify-center font-mono text-xs text-[var(--color-text-muted)]">
            No chart data available.
          </div>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer>
              <ComposedChart data={revEbitdaData}>
                <CartesianGrid stroke={COLORS.BORDER} strokeDasharray="4 4" />
                <XAxis dataKey="year" stroke={COLORS.TEXT_MUTED} tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }} />
                <YAxis stroke={COLORS.TEXT_MUTED} tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }} />
                <Tooltip contentStyle={{ background: COLORS.BG_PANEL, border: `1px solid ${COLORS.BORDER}` }} />
                <Bar dataKey="revenue" fill={COLORS.ACCENT} radius={[2, 2, 0, 0]} />
                <Line type="monotone" dataKey="ebitda" stroke={COLORS.POSITIVE} dot />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2">
        <p className="mb-2 font-mono text-xs uppercase text-[var(--color-text-muted)]">
          EBITDA Margin
        </p>
        {marginData.length === 0 ? (
          <div className="flex h-64 items-center justify-center font-mono text-xs text-[var(--color-text-muted)]">
            No margin data available.
          </div>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer>
              <AreaChart data={marginData}>
                <CartesianGrid stroke={COLORS.BORDER} strokeDasharray="4 4" />
                <XAxis dataKey="year" stroke={COLORS.TEXT_MUTED} tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }} />
                <YAxis stroke={COLORS.TEXT_MUTED} tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }} />
                <Tooltip contentStyle={{ background: COLORS.BG_PANEL, border: `1px solid ${COLORS.BORDER}` }} />
                <Area type="monotone" dataKey="margin" stroke={COLORS.WARNING} fill="rgba(245,158,11,0.2)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2">
        <p className="mb-2 font-mono text-xs uppercase text-[var(--color-text-muted)]">FCF Trend</p>
        {fcfData.length === 0 ? (
          <div className="flex h-64 items-center justify-center font-mono text-xs text-[var(--color-text-muted)]">
            No FCF data available.
          </div>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer>
              <BarChart data={fcfData}>
                <CartesianGrid stroke={COLORS.BORDER} strokeDasharray="4 4" />
                <XAxis dataKey="year" stroke={COLORS.TEXT_MUTED} tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }} />
                <YAxis stroke={COLORS.TEXT_MUTED} tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }} />
                <Tooltip contentStyle={{ background: COLORS.BG_PANEL, border: `1px solid ${COLORS.BORDER}` }} />
                <Bar dataKey="fcf" fill={COLORS.POSITIVE} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </section>
  );
}
