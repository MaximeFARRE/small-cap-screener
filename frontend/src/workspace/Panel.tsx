import type { ChangeEvent } from "react";
import { useWorkspace, type WorkspacePanel as WorkspacePanelState } from "@/context/WorkspaceContext";
import { PANEL_REGISTRY, PANEL_TYPES, type PanelType } from "@/panels/registry";

interface WorkspacePanelProps {
  panel: WorkspacePanelState;
}

function toLabel(type: PanelType): string {
  return type.charAt(0).toUpperCase() + type.slice(1);
}

export function WorkspacePanel({ panel }: WorkspacePanelProps) {
  const { layout, setLayout, closePanel } = useWorkspace();
  const definition = PANEL_REGISTRY[panel.type];
  const PanelComponent = definition?.component;
  const panelLabel = definition?.label ?? toLabel(panel.type);

  const options = PANEL_TYPES.map((type) => ({
    type,
    label: PANEL_REGISTRY[type].label ?? toLabel(type),
  }));

  const handleTypeChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const nextType = event.target.value as PanelType;
    if (nextType === panel.type) {
      return;
    }

    const nextPanels = layout.panels.map((layoutPanel) =>
      layoutPanel.id === panel.id ? { ...layoutPanel, type: nextType } : layoutPanel,
    );
    setLayout({
      ...layout,
      panels: nextPanels,
    });
  };

  return (
    <section className="flex h-full w-full flex-col border border-[var(--color-border)] bg-[var(--color-bg-panel)]">
      <header className="flex items-center justify-between gap-2 border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-3 py-2">
        <span className="font-mono text-xs tracking-wide text-[var(--color-text-primary)] uppercase">
          {panelLabel}
        </span>
        <div className="flex items-center gap-2">
          <select
            aria-label="Panel type"
            value={panel.type}
            onChange={handleTypeChange}
            className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-2 py-1 font-mono text-xs text-[var(--color-text-primary)]"
          >
            {options.map((option) => (
              <option key={option.type} value={option.type}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => closePanel(panel.id)}
            className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-2 py-1 font-mono text-xs text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-primary)]"
            aria-label="Close panel"
          >
            Close
          </button>
        </div>
      </header>
      <div className="min-h-0 flex-1">
        {PanelComponent ? (
          <PanelComponent />
        ) : (
          <div className="flex h-full items-center justify-center px-4 font-mono text-sm text-[var(--color-text-muted)]">
            Panel: {panelLabel}
          </div>
        )}
      </div>
    </section>
  );
}
