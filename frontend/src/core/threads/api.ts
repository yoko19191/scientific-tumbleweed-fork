import { fetchWithAuth } from "../auth/fetcher";
import { getBackendBaseURL } from "../config";

import { createThreadWithDeps } from "./api-core";
import type { CreateThreadResponse } from "./api-core";
import type { ThreadTokenUsageResponse } from "./types";

export async function createThread(
  threadId: string,
  metadata: Record<string, unknown> = {},
): Promise<CreateThreadResponse> {
  return createThreadWithDeps(threadId, metadata, {
    fetchWithAuth,
    getBackendBaseURL,
  });
}

export async function fetchThreadTokenUsage(
  threadId: string,
  { includeActive = false }: { includeActive?: boolean } = {},
): Promise<ThreadTokenUsageResponse | null> {
  const search = new URLSearchParams();
  if (includeActive) {
    search.set("include_active", "true");
  }

  const suffix = search.toString() ? `?${search.toString()}` : "";
  const response = await fetchWithAuth(
    `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}/token-usage${suffix}`,
  );

  if (!response.ok) {
    if (response.status === 403 || response.status === 404) {
      return null;
    }
    throw new Error("Failed to load thread token usage.");
  }

  return (await response.json()) as ThreadTokenUsageResponse;
}
