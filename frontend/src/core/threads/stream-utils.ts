function normalizeStoredRunId(runId: string | null): string | null {
  if (!runId) {
    return null;
  }

  const trimmed = runId.trim();
  if (!trimmed) {
    return null;
  }

  // Extract from query parameters
  const queryIndex = trimmed.indexOf("?");
  if (queryIndex >= 0) {
    const params = new URLSearchParams(trimmed.slice(queryIndex + 1));
    const queryRunId = params.get("run_id")?.trim();
    if (queryRunId && isValidRunId(queryRunId)) {
      return queryRunId;
    }
  }

  const pathWithoutQueryOrHash = trimmed.split(/[?#]/, 1)[0]?.trim() ?? "";
  if (!pathWithoutQueryOrHash) {
    return null;
  }

  // Extract from /runs/{id} path pattern
  const runsMarker = "/runs/";
  const runsIndex = pathWithoutQueryOrHash.lastIndexOf(runsMarker);
  if (runsIndex >= 0) {
    const runIdAfterMarker = pathWithoutQueryOrHash
      .slice(runsIndex + runsMarker.length)
      .split("/", 1)[0]
      ?.trim();
    if (runIdAfterMarker && isValidRunId(runIdAfterMarker)) {
      return runIdAfterMarker;
    }
    return null;
  }

  // Last path segment as fallback
  const segments = pathWithoutQueryOrHash
    .split("/")
    .map((segment) => segment.trim())
    .filter(Boolean);
  const lastSegment = segments.at(-1) ?? null;
  if (lastSegment && isValidRunId(lastSegment)) {
    return lastSegment;
  }
  return null;
}

/** Validate that a string looks like a UUID run ID. */
function isValidRunId(id: string): boolean {
  return /^[a-f0-9-]{8,}$/i.test(id);
}

// Prefix for sessionStorage keys scoped to a specific user.
// Prevents run IDs from leaking across user sessions in the same browser tab.
function userScopedKey(userId: string | null | undefined, key: string): string {
  return userId ? `u:${userId}:${key}` : key;
}

// Clear all lg:stream:* sessionStorage keys for a given user (or unscoped keys).
export function clearStreamSessionStorage(userId?: string | null): void {
  if (typeof window === "undefined") return;
  const prefix = userId ? `u:${userId}:lg:stream:` : "lg:stream:";
  const keysToRemove: string[] = [];
  for (let i = 0; i < window.sessionStorage.length; i++) {
    const k = window.sessionStorage.key(i);
    if (k?.startsWith(prefix)) {
      keysToRemove.push(k);
    }
  }
  keysToRemove.forEach((k) => window.sessionStorage.removeItem(k));
}

export function getRunMetadataStorage(userId?: string | null): {
  getItem(key: `lg:stream:${string}`): string | null;
  setItem(key: `lg:stream:${string}`, value: string): void;
  removeItem(key: `lg:stream:${string}`): void;
} {
  return {
    getItem(key) {
      const scopedKey = userScopedKey(userId, key);
      const normalized = normalizeStoredRunId(
        window.sessionStorage.getItem(scopedKey),
      );
      if (normalized) {
        window.sessionStorage.setItem(scopedKey, normalized);
        return normalized;
      }
      window.sessionStorage.removeItem(scopedKey);
      return null;
    },
    setItem(key, value) {
      const scopedKey = userScopedKey(userId, key);
      const normalized = normalizeStoredRunId(value);
      if (normalized) {
        window.sessionStorage.setItem(scopedKey, normalized);
        return;
      }
      window.sessionStorage.removeItem(scopedKey);
    },
    removeItem(key) {
      window.sessionStorage.removeItem(userScopedKey(userId, key));
    },
  };
}

export function getStreamErrorMessage(error: unknown): string {
  if (isSandboxCapacityError(error)) {
    return SANDBOX_CAPACITY_ERROR_MESSAGE;
  }
  if (typeof error === "string" && error.trim()) {
    return error;
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  if (typeof error === "object" && error !== null) {
    const message = Reflect.get(error, "message");
    if (typeof message === "string" && message.trim()) {
      return message;
    }
    const nestedError = Reflect.get(error, "error");
    if (nestedError instanceof Error && nestedError.message.trim()) {
      return nestedError.message;
    }
    if (typeof nestedError === "string" && nestedError.trim()) {
      return nestedError;
    }
  }
  return "Request failed.";
}

export const SANDBOX_CAPACITY_ERROR_CODE = "SANDBOX_CAPACITY_EXCEEDED";
export const SANDBOX_CAPACITY_ERROR_MESSAGE =
  "服务器沙盒容量已满，暂时无法创建新的沙盒，请稍后再试。";

export function isSandboxCapacityError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) {
    return false;
  }

  const code = Reflect.get(error, "code");
  if (code === SANDBOX_CAPACITY_ERROR_CODE) {
    return true;
  }

  const detail = Reflect.get(error, "detail");
  if (isSandboxCapacityError(detail)) {
    return true;
  }

  const nestedError = Reflect.get(error, "error");
  if (nestedError !== error && isSandboxCapacityError(nestedError)) {
    return true;
  }

  return false;
}
