export interface RefreshStartEvent {
  total: number;
}

export interface RefreshProgressEvent {
  index: number;
  total: number;
  company_id: number;
  ticker: string;
  success: boolean;
  prices_added: number;
  statements_added: number;
  error: string | null;
  error_kind: string | null;
  warnings: string[];
  provider_used: string | null;
}

export interface RefreshDoneEvent {
  total: number;
}

function parsePayload<T>(value: string): T | null {
  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

interface RefreshStreamHandlers {
  onStart: (payload: RefreshStartEvent) => void;
  onProgress: (payload: RefreshProgressEvent) => void;
  onDone: (payload: RefreshDoneEvent) => void;
  onError: (message: string) => void;
}

export function openRefreshStream({
  onStart,
  onProgress,
  onDone,
  onError,
}: RefreshStreamHandlers): EventSource {
  const source = new EventSource("/api/companies/refresh");

  source.addEventListener("start", (event) => {
    const payload = parsePayload<RefreshStartEvent>((event as MessageEvent).data);
    if (payload) {
      onStart(payload);
    }
  });

  source.addEventListener("progress", (event) => {
    const payload = parsePayload<RefreshProgressEvent>((event as MessageEvent).data);
    if (payload) {
      onProgress(payload);
    }
  });

  source.addEventListener("done", (event) => {
    const payload = parsePayload<RefreshDoneEvent>((event as MessageEvent).data);
    if (payload) {
      onDone(payload);
    }
    source.close();
  });

  source.onerror = () => {
    onError("Refresh stream disconnected.");
    source.close();
  };

  return source;
}
