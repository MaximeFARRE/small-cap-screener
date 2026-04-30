import { createElement, type ComponentType } from "react";
import { ScreenerPanel } from "./ScreenerPanel";
import { SignalsPanel } from "./SignalsPanel";
import { TearsheetPanel } from "./TearsheetPanel";
import { WatchlistPanel } from "./WatchlistPanel";

export const PANEL_TYPES = [
  "screener",
  "tearsheet",
  "watchlist",
  "signals",
  "charts",
] as const;

export type PanelType = (typeof PANEL_TYPES)[number];

export interface PanelDefinition {
  label: string;
  component: ComponentType;
}

function createPlaceholderPanel(label: string): ComponentType {
  function PlaceholderPanel() {
    return createElement(
      "div",
      {
        className:
          "flex h-full items-center justify-center px-4 font-mono text-sm text-[var(--color-text-muted)]",
      },
      `Panel: ${label}`,
    );
  }

  PlaceholderPanel.displayName = `${label.replace(/\s+/g, "")}PlaceholderPanel`;
  return PlaceholderPanel;
}

export const PANEL_REGISTRY: Record<PanelType, PanelDefinition> = {
  screener: {
    label: "Screener",
    component: ScreenerPanel,
  },
  tearsheet: {
    label: "Tearsheet",
    component: TearsheetPanel,
  },
  watchlist: {
    label: "Watchlist",
    component: WatchlistPanel,
  },
  signals: {
    label: "Signals",
    component: SignalsPanel,
  },
  charts: {
    label: "Charts",
    component: createPlaceholderPanel("Charts"),
  },
};
