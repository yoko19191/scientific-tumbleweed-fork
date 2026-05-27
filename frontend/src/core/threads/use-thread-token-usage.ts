import { useQuery } from "@tanstack/react-query";

import { fetchThreadTokenUsage } from "./api";
import { threadTokenUsageQueryKey } from "./token-usage";
import type { ThreadTokenUsageResponse } from "./types";

export function useThreadTokenUsage(
  threadId?: string | null,
  {
    enabled = true,
    includeActive = false,
  }: { enabled?: boolean; includeActive?: boolean } = {},
) {
  return useQuery<ThreadTokenUsageResponse | null>({
    queryKey: threadTokenUsageQueryKey(threadId, includeActive),
    queryFn: async () => {
      if (!threadId) {
        return null;
      }
      return fetchThreadTokenUsage(threadId, { includeActive });
    },
    enabled: enabled && Boolean(threadId),
    retry: false,
    refetchInterval: includeActive ? 2000 : false,
    refetchOnWindowFocus: false,
  });
}
