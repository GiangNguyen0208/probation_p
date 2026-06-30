import type { components } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL;
const FALLBACK_KEY = import.meta.env.VITE_INTERNAL_API_KEY;

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type PaginatedResponse<T> = { data: T; meta?: components["schemas"]["ResponseMeta"] };

function buildHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "X-API-Key": FALLBACK_KEY };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }
  return headers;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, unknown>,
): Promise<T> {
  const url = BASE ? new URL(path, BASE) : new URL(path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v != null) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url, {
    method,
    headers: {
      ...buildHeaders(),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const json = await res.json();
  if (!res.ok) {
    throw new ApiError(
      res.status,
      json?.error?.code ?? "http_error",
      json?.error?.message ?? res.statusText,
    );
  }
  if (json && typeof json === "object" && "data" in json) {
    return json.data as T;
  }
  return json as T;
}

export async function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>("GET", path, undefined, params);
}

export async function apiGetPaginated<T>(
  path: string,
  params?: Record<string, unknown>,
): Promise<{ data: T; total: number }> {
  const url = BASE ? new URL(path, BASE) : new URL(path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v != null) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url, {
    method: "GET",
    headers: buildHeaders(),
  });
  const json = await res.json();
  if (!res.ok) {
    throw new ApiError(
      res.status,
      json?.error?.code ?? "http_error",
      json?.error?.message ?? res.statusText,
    );
  }
  const paginated = json as PaginatedResponse<T>;
  return {
    data: paginated.data,
    total: paginated.meta?.total ?? 0,
  };
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("PUT", path, body);
}

export async function apiDelete(path: string): Promise<void> {
  return request<void>("DELETE", path);
}
