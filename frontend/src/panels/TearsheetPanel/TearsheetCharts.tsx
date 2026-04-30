import { useEffect, useMemo, useRef } from "react";
import { AreaSeries, createChart, type IChartApi } from "lightweight-charts";
import {
  Bar,
  BarChart,
  CartesianGrid,
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

function toYearSeries(history: Array<{ fiscal_year: number; value: number }>) {
  return [...history]
    .sort((left, right) => left.fiscal_year - right.fiscal_year)
    .map((point) => ({
      time: `${point.fiscal_year}-12-31`,
      value: point.value,
    }));
}

export function TearsheetCharts({ historical }: TearsheetChartsProps) {
  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const chartApiRef = useRef<IChartApi | null>(null);

  const areaData = useMemo(
    () => toYearSeries(historical.revenue_history),
    [historical.revenue_history],
  );

  const barData = useMemo(() => {
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

  useEffect(() => {
    const container = chartContainerRef.current;
    if (!container) {
      return;
    }
    if (areaData.length === 0) {
      return;
    }

    const chart = createChart(container, {
      layout: {
        background: { color: COLORS.BG_PANEL },
        textColor: COLORS.TEXT_MUTED,
      },
      grid: {
        vertLines: { color: COLORS.BORDER },
        horzLines: { color: COLORS.BORDER },
      },
      rightPriceScale: {
        borderColor: COLORS.BORDER,
      },
      timeScale: {
        borderColor: COLORS.BORDER,
      },
      crosshair: {
        vertLine: { color: COLORS.ACCENT },
        horzLine: { color: COLORS.ACCENT },
      },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: COLORS.ACCENT,
      topColor: "rgba(59,130,246,0.35)",
      bottomColor: "rgba(59,130,246,0.05)",
      lineWidth: 2,
    });

    series.setData(areaData);
    chart.timeScale().fitContent();
    chartApiRef.current = chart;

    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    });
    resizeObserver.observe(container);

    chart.applyOptions({
      width: container.clientWidth,
      height: container.clientHeight,
    });

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartApiRef.current = null;
    };
  }, [areaData]);

  return (
    <section className="grid min-h-0 gap-3 p-4 xl:grid-cols-2">
      <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2">
        <p className="mb-2 font-mono text-xs uppercase text-[var(--color-text-muted)]">
          Price trend proxy (revenue history)
        </p>
        {areaData.length === 0 ? (
          <div className="flex h-64 items-center justify-center font-mono text-xs text-[var(--color-text-muted)]">
            No chart data available.
          </div>
        ) : (
          <div ref={chartContainerRef} className="h-64 w-full" />
        )}
      </div>

      <div className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] p-2">
        <p className="mb-2 font-mono text-xs uppercase text-[var(--color-text-muted)]">
          Revenue vs EBITDA
        </p>
        {barData.length === 0 ? (
          <div className="flex h-64 items-center justify-center font-mono text-xs text-[var(--color-text-muted)]">
            No bar chart data available.
          </div>
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer>
              <BarChart data={barData}>
                <CartesianGrid stroke={COLORS.BORDER} strokeDasharray="4 4" />
                <XAxis
                  dataKey="year"
                  stroke={COLORS.TEXT_MUTED}
                  tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }}
                />
                <YAxis
                  stroke={COLORS.TEXT_MUTED}
                  tick={{ fill: COLORS.TEXT_MUTED, fontSize: 11 }}
                />
                <Tooltip
                  contentStyle={{
                    background: COLORS.BG_PANEL,
                    border: `1px solid ${COLORS.BORDER}`,
                    color: COLORS.TEXT_PRIMARY,
                  }}
                />
                <Bar dataKey="revenue" fill={COLORS.ACCENT} radius={[2, 2, 0, 0]} />
                <Bar dataKey="ebitda" fill={COLORS.POSITIVE} radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </section>
  );
}
