import { useQuery } from "@tanstack/react-query";

import { loadSandboxCapacity } from "./api";

export const sandboxCapacityQueryKey = ["sandbox", "capacity"] as const;

export function useSandboxCapacity({ enabled = true }: { enabled?: boolean } = {}) {
  const { data, isLoading, error } = useQuery({
    queryKey: sandboxCapacityQueryKey,
    queryFn: () => loadSandboxCapacity(),
    enabled,
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
    retry: false,
  });

  return { capacity: data, isLoading, error };
}
