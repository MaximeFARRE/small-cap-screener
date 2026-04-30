// Terminal color palette — mirrors index.css @theme block.
// Use these constants in logic (e.g. chart series colors).
// For Tailwind utility classes prefer the CSS variable tokens directly.
export const COLORS = {
  BG_BASE: "#0a0a0f",
  BG_PANEL: "#0f0f1a",
  BG_ELEVATED: "#161625",
  BORDER: "#1e1e35",
  TEXT_PRIMARY: "#e2e8f0",
  TEXT_MUTED: "#64748b",
  ACCENT: "#3b82f6",
  POSITIVE: "#22c55e",
  NEGATIVE: "#ef4444",
  WARNING: "#f59e0b",
} as const;

// Score thresholds — must stay in sync with Python ScoringService
export const SCORE_THRESHOLDS = {
  HIGH: 70,
  MID: 45,
  LOW: 0,
} as const;

export type MetricDirection = "higher_is_better" | "lower_is_better";

export interface MetricThresholdRule {
  direction: MetricDirection;
  good: number;
  warning: number;
}

export const METRIC_THRESHOLDS = {
  pe_ratio: { direction: "lower_is_better", good: 15, warning: 25 },
  ev_ebitda: { direction: "lower_is_better", good: 10, warning: 14 },
  net_debt_to_ebitda: { direction: "lower_is_better", good: 2.5, warning: 4 },
  roe: { direction: "higher_is_better", good: 12, warning: 7 },
  revenue_growth: { direction: "higher_is_better", good: 8, warning: 0 },
} as const satisfies Record<string, MetricThresholdRule>;
