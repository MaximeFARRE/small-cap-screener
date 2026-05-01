import { Columns2, Grid2x2, HelpCircle, RefreshCcw, Rows2, Square } from "lucide-react";
import { useState, type ComponentType } from "react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/context/WorkspaceContext";
import type { LayoutPreset } from "./LayoutPresets";
import { RefreshModal } from "./RefreshModal";

interface LayoutPresetOption {
  preset: LayoutPreset;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

const LAYOUT_PRESET_OPTIONS: readonly LayoutPresetOption[] = [
  { preset: "single", label: "Single", icon: Square },
  { preset: "split-h", label: "Split horizontal", icon: Columns2 },
  { preset: "split-v", label: "Split vertical", icon: Rows2 },
  { preset: "quad", label: "Quad", icon: Grid2x2 },
];

interface PanelHeaderProps {
  onShowShortcuts: () => void;
}

export function PanelHeader({ onShowShortcuts }: PanelHeaderProps) {
  const { layout, setLayout } = useWorkspace();
  const [showRefreshModal, setShowRefreshModal] = useState(false);

  return (
    <>
      <header className="flex items-center justify-between border border-[var(--color-border)] bg-[var(--color-bg-panel)] px-3 py-2">
        <div className="font-mono text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
          Workspace
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="font-mono text-xs"
            onClick={onShowShortcuts}
          >
            <HelpCircle className="h-3.5 w-3.5" />
            Shortcuts
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            className="font-mono text-xs"
            onClick={() => setShowRefreshModal(true)}
          >
            <RefreshCcw className="h-3.5 w-3.5" />
            Refresh data
          </Button>
          {LAYOUT_PRESET_OPTIONS.map((option) => {
            const Icon = option.icon;
            const isActive = layout.preset === option.preset;

            return (
              <button
                key={option.preset}
                type="button"
                onClick={() => setLayout({ preset: option.preset, panels: layout.panels })}
                className={`inline-flex items-center gap-1 rounded-sm border px-2 py-1 font-mono text-xs transition-colors ${
                  isActive
                    ? "border-[var(--color-accent)] bg-[var(--color-accent)] text-white"
                    : "border-[var(--color-border)] bg-[var(--color-bg-elevated)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                }`}
                aria-label={`Use ${option.label} layout`}
              >
                <Icon className="h-3.5 w-3.5" />
              </button>
            );
          })}
        </div>
      </header>
      <RefreshModal
        open={showRefreshModal}
        onClose={() => setShowRefreshModal(false)}
      />
    </>
  );
}
