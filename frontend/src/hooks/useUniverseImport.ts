export interface UniverseImportStartEvent {
  enrich: boolean;
  pacing_seconds: number;
  batch_size: number;
}

export interface UniverseImportDiscoveryEvent {
  discovered_count: number;
  upserted_count: number;
  enrichment_total: number;
}

export interface UniverseImportProgressEvent {
  phase: string;
  processed: number;
  total: number;
  status?: string;
  ticker?: string;
  batch_number?: number;
  total_batches?: number;
  error?: string | null;
}

export interface UniverseImportDoneEvent {
  discovered_count: number;
  upserted_count: number;
  enrichment_total: number;
  enrichment_succeeded: number;
  enrichment_failed: number;
  enrichment_skipped: number;
}

function parsePayload<T>(value: string): T | null {
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

interface UniverseImportStreamHandlers {
  enrich: boolean;
  pacingSeconds: number;
  batchSize: number;
  onStart: (payload: UniverseImportStartEvent) => void;
  onDiscovery: (payload: UniverseImportDiscoveryEvent) => void;
  onProgress: (payload: UniverseImportProgressEvent) => void;
  onDone: (payload: UniverseImportDoneEvent) => void;
  onServerError: (message: string) => void;
  onConnectionError: (message: string) => void;
}

export function openUniverseImportStream({
  enrich,
  pacingSeconds,
  batchSize,
  onStart,
  onDiscovery,
  onProgress,
  onDone,
  onServerError,
  onConnectionError,
}: UniverseImportStreamHandlers): EventSource {
  const query = new URLSearchParams({
    enrich: enrich ? "true" : "false",
    pacing_seconds: String(pacingSeconds),
    batch_size: String(batchSize),
  });
  const source = new EventSource(`/api/refresh/universe/import-france/stream?${query.toString()}`);

  source.addEventListener("start", (event) => {
    const payload = parsePayload<UniverseImportStartEvent>((event as MessageEvent).data);
    if (payload) {
      onStart(payload);
    }
  });

  source.addEventListener("discovery", (event) => {
    const payload = parsePayload<UniverseImportDiscoveryEvent>((event as MessageEvent).data);
    if (payload) {
      onDiscovery(payload);
    }
  });

  source.addEventListener("progress", (event) => {
    const payload = parsePayload<UniverseImportProgressEvent>((event as MessageEvent).data);
    if (payload) {
      onProgress(payload);
    }
  });

  source.addEventListener("done", (event) => {
    const payload = parsePayload<UniverseImportDoneEvent>((event as MessageEvent).data);
    if (payload) {
      onDone(payload);
    }
    source.close();
  });

  source.addEventListener("error", (event) => {
    const payload = parsePayload<{ message?: string }>((event as MessageEvent).data);
    onServerError(payload?.message ?? "Import universe failed.");
    source.close();
  });

  source.onerror = () => {
    onConnectionError("Import stream disconnected.");
    source.close();
  };

  return source;
}
