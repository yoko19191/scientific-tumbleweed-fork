/**
 * Auth API fetcher utilities.
 *
 * All auth-related requests go through the backend gateway.
 * Credentials are carried via HttpOnly cookies (set by the backend).
 */

import { getBackendBaseURL } from "@/core/config";

import type {
  LoginCredentials,
  LoginResponse,
  RegisterCredentials,
  SetupStatus,
  User,
} from "./types";

const AUTH_BASE = () => `${getBackendBaseURL()}/api/v1/auth`;

/**
 * Wrapper around fetch that always includes credentials (cookies)
 * and the CSRF token header for state-changing requests.
 */
export async function fetchWithAuth(
  url: string,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers);

  // Attach CSRF token for state-changing methods
  const method = (init?.method ?? "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = getCsrfToken();
    if (csrfToken) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  return fetch(url, {
    ...init,
    headers,
    credentials: "include",
  });
}

/**
 * Read the CSRF token from the `csrf_token` cookie.
 * The backend sets this as a non-HttpOnly cookie so JS can read it.
 */
export function getCsrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

/** POST /api/v1/auth/login/local (OAuth2 form) */
export async function login(
  credentials: LoginCredentials,
): Promise<LoginResponse> {
  const body = new URLSearchParams({
    username: credentials.username,
    password: credentials.password,
  });

  const res = await fetchWithAuth(`${AUTH_BASE()}/login/local`, {
    method: "POST",
    body,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new AuthError(res.status, err?.detail);
  }
  return res.json();
}

/** POST /api/v1/auth/register */
export async function register(
  credentials: RegisterCredentials,
): Promise<User> {
  const res = await fetchWithAuth(`${AUTH_BASE()}/register`, {
    method: "POST",
    body: JSON.stringify(credentials),
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => null);
    throw new AuthError(res.status, err?.detail);
  }
  return res.json();
}

/** POST /api/v1/auth/logout */
export async function logout(): Promise<void> {
  await fetchWithAuth(`${AUTH_BASE()}/logout`, { method: "POST" });
}

/** GET /api/v1/auth/me */
export async function fetchCurrentUser(): Promise<User | null> {
  try {
    const res = await fetchWithAuth(`${AUTH_BASE()}/me`);
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/** GET /api/v1/auth/setup-status */
export async function fetchSetupStatus(): Promise<SetupStatus> {
  const res = await fetchWithAuth(`${AUTH_BASE()}/setup-status`);
  return res.json();
}

/** Structured auth error */
export class AuthError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail?: unknown) {
    const msg =
      typeof detail === "object" && detail !== null && "message" in detail
        ? (detail as { message: string }).message
        : `Auth request failed (${status})`;
    super(msg);
    this.name = "AuthError";
    this.status = status;
    this.detail = detail;
  }
}
