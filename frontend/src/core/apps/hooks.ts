import { useQuery } from "@tanstack/react-query";

import { listApps } from "./api";

export function useApps() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["apps"],
    queryFn: () => listApps(),
  });
  return { apps: data ?? [], isLoading, error };
}
