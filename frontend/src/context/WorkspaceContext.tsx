import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { PanelType } from "@/panels/registry";

export type LayoutPreset = "single" | "split-h" | "split-v" | "quad";

interface WorkspaceState {
  activeTicker: string | null;
  setActiveTicker: (ticker: string | null) => void;
  layout: LayoutPreset;
  setLayout: (preset: LayoutPreset) => void;
}

const WorkspaceContext = createContext<WorkspaceState | null>(null);

const STORAGE_KEY = "workspace:layout";

function readStoredLayout(): LayoutPreset {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (
      stored === "single" ||
      stored === "split-h" ||
      stored === "split-v" ||
      stored === "quad"
    ) {
      return stored;
    }
  } catch {
    // localStorage unavailable
  }
  return "split-h";
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [activeTicker, setActiveTickerState] = useState<string | null>(null);
  const [layout, setLayoutState] = useState<LayoutPreset>(readStoredLayout);

  const setActiveTicker = useCallback((ticker: string | null) => {
    setActiveTickerState(ticker);
  }, []);

  const setLayout = useCallback((preset: LayoutPreset) => {
    setLayoutState(preset);
    try {
      localStorage.setItem(STORAGE_KEY, preset);
    } catch {
      // localStorage unavailable
    }
  }, []);

  return (
    <WorkspaceContext.Provider
      value={{ activeTicker, setActiveTicker, layout, setLayout }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace(): WorkspaceState {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used inside WorkspaceProvider");
  return ctx;
}

// Silence unused import warning until panels import PanelType
export type { PanelType };
