import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { PANEL_TYPES, type PanelType } from "../panels/registry";
import {
  DEFAULT_LAYOUT_PRESET,
  LAYOUT_PRESETS,
  type LayoutPreset,
} from "../workspace/LayoutPresets";

const STORAGE_KEY = "workspace:layout";

export interface WorkspacePanel {
  id: string;
  type: PanelType;
}

export interface PanelLayout {
  preset: LayoutPreset;
  panels: WorkspacePanel[];
}

interface WorkspaceState {
  activeTicker: string | null;
  setActiveTicker: (ticker: string | null) => void;
  focusedPanelType: PanelType | null;
  setFocusedPanelType: (type: PanelType | null) => void;
  layout: PanelLayout;
  setLayout: (layout: PanelLayout) => void;
  openPanel: (type: PanelType) => void;
  closePanel: (panelId: string) => void;
}

const WorkspaceContext = createContext<WorkspaceState | null>(null);

function createPanelId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `panel-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function isLayoutPreset(value: unknown): value is LayoutPreset {
  return value === "single" || value === "split-h" || value === "split-v" || value === "quad";
}

function isPanelType(value: unknown): value is PanelType {
  return PANEL_TYPES.some((panelType) => panelType === value);
}

function isWorkspacePanel(value: unknown): value is WorkspacePanel {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const panel = value as Partial<WorkspacePanel>;
  return typeof panel.id === "string" && isPanelType(panel.type);
}

function buildDefaultLayout(preset: LayoutPreset): PanelLayout {
  const panelTypes = LAYOUT_PRESETS[preset].panels;
  return {
    preset,
    panels: panelTypes.map((type) => ({ id: createPanelId(), type })),
  };
}

function normalizeLayout(layout: PanelLayout): PanelLayout {
  const defaultTypes = LAYOUT_PRESETS[layout.preset].panels;
  const maxPanels = defaultTypes.length;
  const primaryPanelType = defaultTypes[0];
  if (!primaryPanelType) {
    throw new Error(`No default panel type configured for preset: ${layout.preset}`);
  }
  const nextPanels = [...layout.panels].slice(0, maxPanels);

  while (nextPanels.length < maxPanels) {
    const index = nextPanels.length;
    const fallbackType = defaultTypes[index] ?? primaryPanelType;
    nextPanels.push({ id: createPanelId(), type: fallbackType });
  }

  return {
    preset: layout.preset,
    panels: nextPanels,
  };
}

function isPanelLayout(value: unknown): value is PanelLayout {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const maybeLayout = value as Partial<PanelLayout>;
  if (!isLayoutPreset(maybeLayout.preset)) {
    return false;
  }
  if (!Array.isArray(maybeLayout.panels)) {
    return false;
  }

  return maybeLayout.panels.every((panel) => isWorkspacePanel(panel));
}

function readStoredLayout(): PanelLayout {
  if (typeof window === "undefined") {
    return buildDefaultLayout(DEFAULT_LAYOUT_PRESET);
  }

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (!stored) {
    return buildDefaultLayout(DEFAULT_LAYOUT_PRESET);
  }

  try {
    const parsed: unknown = JSON.parse(stored);
    if (isPanelLayout(parsed)) {
      return normalizeLayout(parsed);
    }
  } catch {
    window.localStorage.removeItem(STORAGE_KEY);
  }

  return buildDefaultLayout(DEFAULT_LAYOUT_PRESET);
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [activeTicker, setActiveTickerState] = useState<string | null>(null);
  const [focusedPanelType, setFocusedPanelTypeState] = useState<PanelType | null>(null);
  const [layout, setLayoutState] = useState<PanelLayout>(readStoredLayout);

  const setActiveTicker = useCallback((ticker: string | null) => {
    setActiveTickerState(ticker);
  }, []);

  const setFocusedPanelType = useCallback((type: PanelType | null) => {
    setFocusedPanelTypeState(type);
  }, []);

  const persistLayout = useCallback((nextLayout: PanelLayout) => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextLayout));
  }, []);

  const setLayout = useCallback((nextLayout: PanelLayout) => {
    const normalizedLayout = normalizeLayout(nextLayout);
    setLayoutState(normalizedLayout);
    persistLayout(normalizedLayout);
  }, [persistLayout]);

  const openPanel = useCallback((type: PanelType) => {
    setLayoutState((previousLayout) => {
      const maxPanels = LAYOUT_PRESETS[previousLayout.preset].panels.length;
      if (previousLayout.panels.length >= maxPanels) {
        return previousLayout;
      }

      const nextLayout: PanelLayout = {
        ...previousLayout,
        panels: [...previousLayout.panels, { id: createPanelId(), type }],
      };
      const normalizedLayout = normalizeLayout(nextLayout);
      persistLayout(normalizedLayout);
      return normalizedLayout;
    });
  }, [persistLayout]);

  const closePanel = useCallback((panelId: string) => {
    setLayoutState((previousLayout) => {
      const remainingPanels = previousLayout.panels.filter(
        (panel) => panel.id !== panelId,
      );
      if (remainingPanels.length === previousLayout.panels.length) {
        return previousLayout;
      }

      if (remainingPanels.length === 0) {
        const fallbackLayout = buildDefaultLayout("single");
        persistLayout(fallbackLayout);
        return fallbackLayout;
      }

      const nextLayout: PanelLayout = {
        ...previousLayout,
        panels: remainingPanels,
      };
      const normalizedLayout = normalizeLayout(nextLayout);
      persistLayout(normalizedLayout);
      return normalizedLayout;
    });
  }, [persistLayout]);

  return (
    <WorkspaceContext.Provider
      value={{
        activeTicker,
        setActiveTicker,
        focusedPanelType,
        setFocusedPanelType,
        layout,
        setLayout,
        openPanel,
        closePanel,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useWorkspace(): WorkspaceState {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return ctx;
}
