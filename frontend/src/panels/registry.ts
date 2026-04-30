import { createElement, type ComponentType } from "react";

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
    component: createPlaceholderPanel("Screener"),
  },
  tearsheet: {
    label: "Tearsheet",
    component: createPlaceholderPanel("Tearsheet"),
  },
  watchlist: {
    label: "Watchlist",
    component: createPlaceholderPanel("Watchlist"),
  },
  signals: {
    label: "Signals",
    component: createPlaceholderPanel("Signals"),
  },
  charts: {
    label: "Charts",
    component: createPlaceholderPanel("Charts"),
  },
};
