import { useQuery } from "@tanstack/react-query";

import { getAcademicDataSearchStatus } from "./api";

export function useAcademicDataSearchStatus() {
  return useQuery({
    queryKey: ["apps", "research-data-search", "status"],
    queryFn: () => getAcademicDataSearchStatus(),
    staleTime: 30_000,
  });
}
