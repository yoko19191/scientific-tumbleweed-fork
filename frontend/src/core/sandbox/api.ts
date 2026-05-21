import { fetchWithAuth } from "@/core/auth/fetcher";
import { getBackendBaseURL } from "@/core/config";

export interface SandboxCapacity {
  enabled: boolean;
  backend: string;
  limit: number | null;
  active: number;
  warm: number;
  total: number;
  available: number | null;
  saturated: boolean;
}

export async function loadSandboxCapacity(): Promise<SandboxCapacity> {
  const res = await fetchWithAuth(`${getBackendBaseURL()}/api/sandbox/capacity`);
  if (!res.ok) {
    throw new Error(`Failed to load sandbox capacity: ${res.statusText}`);
  }
  return res.json() as Promise<SandboxCapacity>;
}
