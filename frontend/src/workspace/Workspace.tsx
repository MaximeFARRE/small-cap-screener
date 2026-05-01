import {
  Group as PanelGroup,
  Panel as ResizablePanel,
  Separator as PanelResizeHandle,
} from "react-resizable-panels";
import { useEffect, useState, type ReactNode } from "react";
import {
  useWorkspace,
  type WorkspacePanel as WorkspacePanelState,
} from "@/context/WorkspaceContext";
import { PanelHeader } from "./PanelHeader";
import { UniverseImportBanner } from "./UniverseImportBanner";
import { WorkspacePanel } from "./Panel";
import { ShortcutsModal } from "./ShortcutsModal";

function ResizeHandle() {
  return (
    <PanelResizeHandle className="bg-[var(--color-border)] transition-colors hover:bg-[var(--color-accent)] data-[separator-active]:bg-[var(--color-accent)]" />
  );
}

function renderSplitLayout(
  panels: WorkspacePanelState[],
  direction: "horizontal" | "vertical",
) {
  const firstPanel = panels[0];
  const secondPanel = panels[1];

  if (!firstPanel || !secondPanel) {
    return null;
  }

  return (
    <PanelGroup orientation={direction}>
      <ResizablePanel defaultSize={50} minSize={20}>
        <WorkspacePanel panel={firstPanel} />
      </ResizablePanel>
      <ResizeHandle />
      <ResizablePanel defaultSize={50} minSize={20}>
        <WorkspacePanel panel={secondPanel} />
      </ResizablePanel>
    </PanelGroup>
  );
}

function renderQuadLayout(panels: WorkspacePanelState[]) {
  const [topLeft, topRight, bottomLeft, bottomRight] = panels;

  if (!topLeft || !topRight || !bottomLeft || !bottomRight) {
    return null;
  }

  return (
    <PanelGroup orientation="vertical">
      <ResizablePanel defaultSize={50} minSize={20}>
        <PanelGroup orientation="horizontal">
          <ResizablePanel defaultSize={50} minSize={20}>
            <WorkspacePanel panel={topLeft} />
          </ResizablePanel>
          <ResizeHandle />
          <ResizablePanel defaultSize={50} minSize={20}>
            <WorkspacePanel panel={topRight} />
          </ResizablePanel>
        </PanelGroup>
      </ResizablePanel>
      <ResizeHandle />
      <ResizablePanel defaultSize={50} minSize={20}>
        <PanelGroup orientation="horizontal">
          <ResizablePanel defaultSize={50} minSize={20}>
            <WorkspacePanel panel={bottomLeft} />
          </ResizablePanel>
          <ResizeHandle />
          <ResizablePanel defaultSize={50} minSize={20}>
            <WorkspacePanel panel={bottomRight} />
          </ResizablePanel>
        </PanelGroup>
      </ResizablePanel>
    </PanelGroup>
  );
}

export function Workspace() {
  const { activeTicker, layout, setActiveTicker, focusedPanelType, setFocusedPanelType } = useWorkspace();
  const [showShortcuts, setShowShortcuts] = useState(false);
  const { panels, preset } = layout;

  useEffect(() => {
    const focusPanelElement = (type: string) => {
      const panel = document.querySelector<HTMLElement>(`[data-panel-type="${type}"]`);
      if (!panel) {
        return;
      }
      panel.focus();
    };

    const isEditableTarget = (target: EventTarget | null): boolean => {
      if (!(target instanceof HTMLElement)) {
        return false;
      }
      const tagName = target.tagName;
      return (
        target.isContentEditable ||
        tagName === "INPUT" ||
        tagName === "TEXTAREA" ||
        tagName === "SELECT"
      );
    };

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setActiveTicker(null);
        return;
      }

      if (event.key === "?") {
        event.preventDefault();
        setShowShortcuts(true);
        return;
      }

      if (isEditableTarget(event.target)) {
        return;
      }

      const key = event.key.toLowerCase();
      if (key === "s") {
        event.preventDefault();
        setFocusedPanelType("screener");
        focusPanelElement("screener");
        window.dispatchEvent(new CustomEvent("workspace:focus-screener-filter"));
        return;
      }
      if (key === "w") {
        event.preventDefault();
        setFocusedPanelType("watchlist");
        focusPanelElement("watchlist");
        return;
      }
      if (key === "j" || key === "k") {
        event.preventDefault();
        const direction = key === "j" ? 1 : -1;
        window.dispatchEvent(
          new CustomEvent("workspace:navigate-rows", {
            detail: { panel: focusedPanelType, direction },
          }),
        );
        return;
      }
      if (event.key === "Enter") {
        event.preventDefault();
        window.dispatchEvent(
          new CustomEvent("workspace:open-selected", {
            detail: { panel: focusedPanelType },
          }),
        );
        if (activeTicker) {
          setFocusedPanelType("tearsheet");
          focusPanelElement("tearsheet");
        }
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [activeTicker, focusedPanelType, setActiveTicker, setFocusedPanelType]);

  let content: ReactNode = null;
  if (preset === "single") {
    const firstPanel = panels[0];
    if (firstPanel) {
      content = (
        <PanelGroup orientation="horizontal">
          <ResizablePanel defaultSize={100} minSize={20}>
            <WorkspacePanel panel={firstPanel} />
          </ResizablePanel>
        </PanelGroup>
      );
    }
  } else if (preset === "split-h") {
    content = renderSplitLayout(panels, "horizontal");
  } else if (preset === "split-v") {
    content = renderSplitLayout(panels, "vertical");
  } else if (preset === "quad") {
    content = renderQuadLayout(panels);
  }

  return (
    <main className="flex h-full w-full flex-col gap-2 bg-[var(--color-bg-base)] p-2">
      <PanelHeader onShowShortcuts={() => setShowShortcuts(true)} />
      <UniverseImportBanner />
      <div className="min-h-0 flex-1">
        {content ?? (
          <div className="flex h-full items-center justify-center font-mono text-sm text-[var(--color-text-muted)]">
            No panel layout available.
          </div>
        )}
      </div>
      <ShortcutsModal open={showShortcuts} onClose={() => setShowShortcuts(false)} />
    </main>
  );
}
