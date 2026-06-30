import type { components } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL;
const TOKEN = import.meta.env.VITE_ADMIN_TOKEN;

export class AdminApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "AdminApiError";
  }
}

type PaginatedResponse<T> = { data: T; meta?: components["schemas"]["ResponseMeta"] };

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
      Authorization: `Bearer ${TOKEN}`,
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const json = await res.json();
  if (!res.ok) {
    throw new AdminApiError(
      res.status,
      json?.error?.code ?? "http_error",
      json?.error?.message ?? res.statusText,
    );
  }
  return (json as PaginatedResponse<T>).data as T;
}

export async function adminGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  return request<T>("GET", path, undefined, params);
}

export async function adminPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, body);
}

export async function adminPut<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("PUT", path, body);
}

export async function adminDelete(path: string): Promise<void> {
  return request<void>("DELETE", path);
}
