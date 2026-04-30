const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function toRequestUrl(path: string): string {
  const normalizedBaseUrl = API_BASE_URL.endsWith("/")
    ? API_BASE_URL.slice(0, -1)
    : API_BASE_URL;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${normalizedBaseUrl}${normalizedPath}`;
}

async function readErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    try {
      const payload: unknown = await response.json();
      if (typeof payload === "object" && payload !== null) {
        const maybeError = payload as Record<string, unknown>;
        const detail = maybeError.detail;
        if (typeof detail === "string" && detail.trim().length > 0) {
          return detail;
        }

        const message = maybeError.message;
        if (typeof message === "string" && message.trim().length > 0) {
          return message;
        }
      }
    } catch {
      // Fallback to plain text below when body is not valid JSON.
    }
  }

  const text = await response.text();
  if (text.trim().length > 0) {
    return text;
  }

  return response.statusText || "Request failed";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(toRequestUrl(path), {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(response.status, await readErrorMessage(response));
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
