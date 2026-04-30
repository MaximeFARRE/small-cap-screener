const COMPACT_FORMATTER = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const PERCENT_FORMATTER = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export function formatMarketCap(value: number | null): string {
  if (value === null) return "—";
  return COMPACT_FORMATTER.format(value);
}

export function formatPercent(value: number | null): string {
  if (value === null) return "—";
  return PERCENT_FORMATTER.format(value / 100);
}

export function formatRatio(value: number | null, decimals = 1): string {
  if (value === null) return "—";
  return value.toFixed(decimals) + "x";
}

export function formatNumber(value: number | null, decimals = 2): string {
  if (value === null) return "—";
  return value.toFixed(decimals);
}
