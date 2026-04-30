import type { ComponentType } from "react";

export type PanelType =
  | "screener"
  | "tearsheet"
  | "watchlist"
  | "signals"
  | "charts";

export interface PanelDefinition {
  label: string;
  component: ComponentType;
}

// Populated incrementally as panels are implemented (Phase 3-6).
// To add a new panel: create the component, then add one entry here.
export const PANEL_REGISTRY: Partial<Record<PanelType, PanelDefinition>> = {};
