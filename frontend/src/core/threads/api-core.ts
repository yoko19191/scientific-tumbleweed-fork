import type { AgentThread } from "./types";

export type CreateThreadResponse = AgentThread;

export type CreateThreadDeps = {
  fetchWithAuth: (url: string, init?: RequestInit) => Promise<Response>;
  getBackendBaseURL: () => string;
};

async function readErrorDetail(
  response: Response,
  fallback: string,
): Promise<string> {
  const error = await response.json().catch(() => ({ detail: fallback }));
  return error.detail ?? fallback;
}

export async function createThreadWithDeps(
  threadId: string,
  metadata: Record<string, unknown>,
  deps: CreateThreadDeps,
): Promise<CreateThreadResponse> {
  const response = await deps.fetchWithAuth(
    `${deps.getBackendBaseURL()}/api/threads`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: threadId,
        metadata,
      }),
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response, "Failed to create thread"));
  }

  return response.json();
}
