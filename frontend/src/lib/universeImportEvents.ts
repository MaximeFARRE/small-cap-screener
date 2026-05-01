export const UNIVERSE_IMPORT_STATUS_EVENT = "workspace:universe-import-status";

export type UniverseImportStatusPhase =
  | "running"
  | "discovery_done"
  | "completed"
  | "error";

export interface UniverseImportStatusDetail {
  phase: UniverseImportStatusPhase;
  message: string;
  processed?: number;
  total?: number;
  succeeded?: number;
  failed?: number;
  skipped?: number;
}
