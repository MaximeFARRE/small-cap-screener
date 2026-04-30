import type { PanelType } from "@/panels/registry";

export type LayoutPreset = "single" | "split-h" | "split-v" | "quad";

export interface LayoutPresetDefinition {
  preset: LayoutPreset;
  panels: PanelType[];
}

export const DEFAULT_LAYOUT_PRESET: LayoutPreset = "split-h";

export const LAYOUT_PRESETS: Record<LayoutPreset, LayoutPresetDefinition> = {
  single: {
    preset: "single",
    panels: ["screener"],
  },
  "split-h": {
    preset: "split-h",
    panels: ["screener", "tearsheet"],
  },
  "split-v": {
    preset: "split-v",
    panels: ["screener", "tearsheet"],
  },
  quad: {
    preset: "quad",
    panels: ["screener", "tearsheet", "watchlist", "signals"],
  },
};
