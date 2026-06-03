import { fetchWithAuth } from "@/core/auth/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type { WorkspaceApp } from "./types";

export async function listApps(): Promise<WorkspaceApp[]> {
  const response = await fetchWithAuth(`${getBackendBaseURL()}/api/apps`);
  if (!response.ok) {
    throw new Error(`Failed to load apps: ${response.statusText}`);
  }
  const data = (await response.json()) as { apps?: WorkspaceApp[] };
  return data.apps ?? [];
}
