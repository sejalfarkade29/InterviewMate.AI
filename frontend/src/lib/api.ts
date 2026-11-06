import type { Attempt } from "@/types";

/**
 * By default the browser calls the SAME origin (/api/...) and Next.js forwards the request to the FastAPI backend
 * (see `rewrites` in next.config.mjs). That avoids CORS and cookie problems. Set NEXT_PUBLIC_API_URL only if you
 * want the browser to call the backend directly.
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const OFFLINE = "Cannot reach the server. Start the backend (uvicorn app.main:app --reload --port 8000) and try again.";

function describe(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{ loc: [...], msg: "..." }]
    return detail
      .map((d) => {
        const field = Array.isArray(d?.loc) ? String(d.loc[d.loc.length - 1]).replace(/_/g, " ") : "";
        const msg = String(d?.msg ?? "Invalid value").replace(/^Value error, /, "");
        return field ? `${field}: ${msg}` : msg;
      })
      .join(". ");
  }
  return "Something went wrong. Please try again.";
}

async function request<T>(path: string, init: RequestInit, json = true): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, {
      ...init,
      credentials: "include", // sends the httpOnly session cookie
      headers: { ...(json ? { "Content-Type": "application/json" } : {}), ...(init.headers ?? {}) },
    });
  } catch {
    throw new ApiError(OFFLINE, 0);
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    // The Next.js proxy answers 500/502/503/504 with plain text when the backend is down or crashed.
    if (body === null && res.status >= 500) throw new ApiError(OFFLINE, res.status);
    throw new ApiError(describe(body?.detail), res.status);
  }
  return body as T;
}

export const api = <T,>(path: string, init: RequestInit = {}) => request<T>(path, init);
export const post = <T,>(path: string, data?: unknown) => request<T>(path, { method: "POST", body: data === undefined ? undefined : JSON.stringify(data) });
export const put = <T,>(path: string, data?: unknown) => request<T>(path, { method: "PUT", body: data === undefined ? undefined : JSON.stringify(data) });
export const del = <T = void,>(path: string) => request<T>(path, { method: "DELETE" });
/** multipart upload (resume files). The browser sets the Content-Type boundary itself. */
export const upload = <T,>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }, false);

/** WebSocket URL for live voice. WebSockets connect straight to the backend (Next.js cannot proxy them in dev). */
export function wsUrl(path: string, token: string): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  let origin: string;
  if (explicit) origin = explicit.replace(/\/$/, "");
  else if (process.env.NEXT_PUBLIC_API_URL) origin = process.env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws").replace(/\/$/, "");
  else origin = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8000`;
  return `${origin}${path}?token=${encodeURIComponent(token)}`;
}

// Legacy helpers for the older attempts table (still served by the backend).
export function syncAttempt(attempt: Attempt) { return post<Attempt>("/attempts", attempt); }
export function loadRemoteAttempts() { return api<Attempt[]>("/attempts"); }
export function clearRemoteAttempts() { return del("/attempts"); }
