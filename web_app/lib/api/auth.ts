/**
 * Typed client for the P0.5 session-cookie auth API
 * (`backend/app/api/routes/auth.py`).
 *
 * The backend sets an httponly session cookie and a readable CSRF
 * cookie; this module never stores a token itself — `credentials:
 * "include"` is what carries the session, and the CSRF cookie is only
 * ever read back into a header, never persisted here. There is no
 * localStorage fallback: if the backend is unreachable, every call
 * throws and the UI must say so.
 */

const CSRF_COOKIE_NAME = "blinkora_csrf";

export type AuthUser = {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
};

export type AuthErrorCode =
  | "INVALID_CREDENTIALS"
  | "EMAIL_TAKEN"
  | "UNAUTHORIZED"
  | "CSRF_FAILED"
  | "RATE_LIMITED"
  | "UNAVAILABLE"
  | "UNEXPECTED";

export class AuthApiError extends Error {
  readonly code: AuthErrorCode;
  readonly status: number;

  constructor(code: AuthErrorCode, status: number, detail: string) {
    super(detail);
    this.name = "AuthApiError";
    this.code = code;
    this.status = status;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const prefix = `${name}=`;
  for (const part of document.cookie.split(";")) {
    const trimmed = part.trim();
    if (trimmed.startsWith(prefix)) return decodeURIComponent(trimmed.slice(prefix.length));
  }
  return null;
}

function codeForStatus(status: number, serverCode?: string | null): AuthErrorCode {
  if (serverCode === "INVALID_CREDENTIALS") return "INVALID_CREDENTIALS";
  if (serverCode === "EMAIL_TAKEN") return "EMAIL_TAKEN";
  if (serverCode === "CSRF_FAILED") return "CSRF_FAILED";
  if (serverCode === "RATE_LIMITED" || status === 429) return "RATE_LIMITED";
  if (status === 401) return "UNAUTHORIZED";
  if (status >= 500) return "UNAVAILABLE";
  return "UNEXPECTED";
}

export function createAuthApi(baseUrl: string) {
  const base = baseUrl.replace(/\/+$/, "");

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const method = (init.method ?? "GET").toUpperCase();
    const headers: Record<string, string> = { ...(init.headers as Record<string, string> | undefined) };
    if (method !== "GET" && method !== "HEAD") {
      const csrf = readCookie(CSRF_COOKIE_NAME);
      if (csrf) headers["X-CSRF-Token"] = csrf;
      if (init.body !== undefined) headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
    }

    let response: Response;
    try {
      response = await fetch(`${base}${path}`, { ...init, method, headers, credentials: "include" });
    } catch (error) {
      throw new AuthApiError("UNAVAILABLE", 0, error instanceof Error ? error.message : "network error");
    }

    if (!response.ok) {
      let body: { error_code?: string; detail?: string } = {};
      try {
        body = await response.json();
      } catch {
        // No JSON body to read.
      }
      throw new AuthApiError(codeForStatus(response.status, body.error_code), response.status, body.detail ?? "Request failed.");
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  return {
    register: (email: string, password: string, displayName: string) =>
      request<AuthUser>("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, password, display_name: displayName }),
      }),

    login: (email: string, password: string) =>
      request<AuthUser>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

    logout: () => request<void>("/api/auth/logout", { method: "POST" }),

    me: () => request<AuthUser>("/api/auth/me"),
  };
}

export type AuthApi = ReturnType<typeof createAuthApi>;
