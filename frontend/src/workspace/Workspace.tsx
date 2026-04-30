import {
  Group as PanelGroup,
  Panel,
  Separator as PanelResizeHandle,
} from "react-resizable-panels";
import type { ReactNode } from "react";
import {
  useWorkspace,
  type WorkspacePanel as WorkspacePanelState,
} from "@/context/WorkspaceContext";
import { PANEL_REGISTRY } from "@/panels/registry";

interface PanelSlotProps {
  panel: WorkspacePanelState;
}

function PanelSlot({ panel }: PanelSlotProps) {
  const definition = PANEL_REGISTRY[panel.type];
  const PanelComponent = definition?.component;
  const label = definition?.label ?? panel.type;

  return (
    <div className="h-full w-full border border-[var(--color-border)] bg-[var(--color-bg-panel)]">
      {PanelComponent ? (
        <PanelComponent />
      ) : (
        <div className="flex h-full items-center justify-center font-mono text-sm text-[var(--color-text-muted)]">
          Panel: {label}
        </div>
      )}
    </div>
  );
}

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
      <Panel defaultSize={50} minSize={20}>
        <PanelSlot panel={firstPanel} />
      </Panel>
      <ResizeHandle />
      <Panel defaultSize={50} minSize={20}>
        <PanelSlot panel={secondPanel} />
      </Panel>
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
      <Panel defaultSize={50} minSize={20}>
        <PanelGroup orientation="horizontal">
          <Panel defaultSize={50} minSize={20}>
            <PanelSlot panel={topLeft} />
          </Panel>
          <ResizeHandle />
          <Panel defaultSize={50} minSize={20}>
            <PanelSlot panel={topRight} />
          </Panel>
        </PanelGroup>
      </Panel>
      <ResizeHandle />
      <Panel defaultSize={50} minSize={20}>
        <PanelGroup orientation="horizontal">
          <Panel defaultSize={50} minSize={20}>
            <PanelSlot panel={bottomLeft} />
          </Panel>
          <ResizeHandle />
          <Panel defaultSize={50} minSize={20}>
            <PanelSlot panel={bottomRight} />
          </Panel>
        </PanelGroup>
      </Panel>
    </PanelGroup>
  );
}

export function Workspace() {
  const { layout } = useWorkspace();
  const { panels, preset } = layout;

  let content: ReactNode = null;
  if (preset === "single") {
    const firstPanel = panels[0];
    if (firstPanel) {
      content = (
        <PanelGroup orientation="horizontal">
          <Panel defaultSize={100} minSize={20}>
            <PanelSlot panel={firstPanel} />
          </Panel>
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
    <main className="h-full w-full bg-[var(--color-bg-base)] p-2">
      {content}
    </main>
  );
}
