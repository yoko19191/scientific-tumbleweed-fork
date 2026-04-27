import { fetchWithAuth } from "../auth/fetcher";
import { getBackendBaseURL } from "../config";

import { createThreadWithDeps } from "./api-core";
import type { CreateThreadResponse } from "./api-core";

export async function createThread(
  threadId: string,
  metadata: Record<string, unknown> = {},
): Promise<CreateThreadResponse> {
  return createThreadWithDeps(threadId, metadata, {
    fetchWithAuth,
    getBackendBaseURL,
  });
}
