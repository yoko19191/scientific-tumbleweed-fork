import { fetchWithAuth } from "@/core/auth/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type { MCPConfig } from "./types";

export async function loadMCPConfig() {
  const response = await fetchWithAuth(`${getBackendBaseURL()}/api/mcp/config`);
  return response.json() as Promise<MCPConfig>;
}

export async function updateMCPConfig(config: MCPConfig) {
  const response = await fetchWithAuth(`${getBackendBaseURL()}/api/mcp/config`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });
  return response.json();
}

export async function setMCPServerEnabled(serverName: string, enabled: boolean) {
  const response = await fetchWithAuth(
    `${getBackendBaseURL()}/api/mcp/servers/${encodeURIComponent(serverName)}/enabled`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ enabled }),
    },
  );
  return response.json() as Promise<{ success: boolean; name: string; enabled: boolean }>;
}
