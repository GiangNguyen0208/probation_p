import type { components } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL;
const KEY = import.meta.env.VITE_INTERNAL_API_KEY;

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

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  params?: Record<string, unknown>,
): Promise<T> {
  const url = BASE ? new URL(BASE + path) : new URL(path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v != null) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url, {
    method,
    headers: {
      "X-API-Key": KEY,
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
  return (json as PaginatedResponse<T>).data as T;
}

export async function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>("GET", path, undefined, params);
}

export async function apiGetPaginated<T>(
  path: string,
  params?: Record<string, unknown>,
): Promise<{ data: T; total: number }> {
  const url = BASE ? new URL(BASE + path) : new URL(path, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v != null) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url, {
    method: "GET",
    headers: { "X-API-Key": KEY },
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
