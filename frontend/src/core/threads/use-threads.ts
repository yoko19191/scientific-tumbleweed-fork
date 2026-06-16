import {
  type InfiniteData,
  type QueryClient,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { getAPIClient } from "../api";
import { useAuth } from "../auth/AuthProvider";
import { fetchWithAuth } from "../auth/fetcher";
import { getBackendBaseURL } from "../config";

import type { AgentThread } from "./types";

export const INFINITE_THREADS_PAGE_SIZE = 50;

export const INFINITE_THREADS_QUERY_KEY_PREFIX = [
  "threads",
  "searchInfinite",
] as const;

async function fetchThreadPage({
  limit,
  offset,
}: {
  limit: number;
  offset: number;
}) {
  const search = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetchWithAuth(
    `${getBackendBaseURL()}/api/threads/listByUser?${search.toString()}`,
  );
  if (!response.ok) {
    if (response.status === 401) return [];
    throw new Error("Failed to fetch threads");
  }
  return response.json() as Promise<AgentThread[]>;
}

export function getInfiniteThreadsNextPageParam(
  lastPage: AgentThread[],
  allPages: AgentThread[][],
  pageSize: number = INFINITE_THREADS_PAGE_SIZE,
): number | undefined {
  if (lastPage.length < pageSize) {
    return undefined;
  }
  return allPages.reduce((sum, page) => sum + page.length, 0);
}

export function mapInfiniteThreadsCache(
  oldData: InfiniteData<AgentThread[]> | undefined,
  mapper: (thread: AgentThread) => AgentThread,
): InfiniteData<AgentThread[]> | undefined {
  if (!oldData) {
    return oldData;
  }
  return {
    ...oldData,
    pages: oldData.pages.map((page) => page.map(mapper)),
  };
}

export function filterInfiniteThreadsCache(
  oldData: InfiniteData<AgentThread[]> | undefined,
  predicate: (thread: AgentThread) => boolean,
): InfiniteData<AgentThread[]> | undefined {
  if (!oldData) {
    return oldData;
  }
  return {
    ...oldData,
    pages: oldData.pages.map((page) => page.filter(predicate)),
  };
}

export function upsertThreadInInfiniteCache(
  queryClient: QueryClient,
  thread: AgentThread,
) {
  queryClient.setQueriesData(
    {
      queryKey: INFINITE_THREADS_QUERY_KEY_PREFIX,
      exact: false,
    },
    (oldData: InfiniteData<AgentThread[]> | undefined) => {
      if (!oldData) {
        return oldData;
      }

      let exists = false;
      const pages = oldData.pages.map((page) =>
        page.map((existing) => {
          if (existing.thread_id !== thread.thread_id) {
            return existing;
          }
          exists = true;
          return {
            ...thread,
            ...existing,
            metadata: {
              ...(thread.metadata ?? {}),
              ...(existing.metadata ?? {}),
            },
            values: {
              ...thread.values,
              ...existing.values,
            },
          };
        }),
      );

      if (exists) {
        return { ...oldData, pages };
      }

      const firstPage = pages[0] ?? [];
      return {
        ...oldData,
        pages: [[thread, ...firstPage], ...pages.slice(1)],
      };
    },
  );
}

export function useThreads() {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  return useQuery<AgentThread[]>({
    queryKey: ["threads", "search", userId],
    queryFn: async () => {
      return fetchThreadPage({ limit: 100, offset: 0 });
    },
    refetchOnWindowFocus: false,
  });
}

export function useInfiniteThreads() {
  const { user } = useAuth();
  const userId = user?.id ?? null;
  return useInfiniteQuery<
    AgentThread[],
    Error,
    InfiniteData<AgentThread[]>,
    readonly unknown[],
    number
  >({
    queryKey: [...INFINITE_THREADS_QUERY_KEY_PREFIX, userId],
    initialPageParam: 0,
    queryFn: async ({ pageParam }) =>
      fetchThreadPage({
        limit: INFINITE_THREADS_PAGE_SIZE,
        offset: pageParam,
      }),
    getNextPageParam: (lastPage, allPages) =>
      getInfiniteThreadsNextPageParam(lastPage, allPages),
    refetchOnWindowFocus: false,
  });
}

export function useDeleteThread() {
  const queryClient = useQueryClient();
  const apiClient = getAPIClient();
  return useMutation({
    mutationFn: async ({
      threadId,
      onRemoteDeleted,
    }: {
      threadId: string;
      onRemoteDeleted?: () => void;
    }) => {
      await apiClient.threads.delete(threadId);
      onRemoteDeleted?.();

      const response = await fetchWithAuth(
        `${getBackendBaseURL()}/api/threads/${encodeURIComponent(threadId)}`,
        {
          method: "DELETE",
        },
      );

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Failed to delete local thread data." }));
        throw new Error(error.detail ?? "Failed to delete local thread data.");
      }
    },
    onSuccess(_, { threadId }) {
      queryClient.setQueriesData(
        {
          queryKey: ["threads", "search"],
          exact: false,
        },
        (oldData: Array<AgentThread> | undefined) => {
          if (oldData == null) {
            return oldData;
          }
          return oldData.filter((t) => t.thread_id !== threadId);
        },
      );
      queryClient.setQueriesData(
        {
          queryKey: INFINITE_THREADS_QUERY_KEY_PREFIX,
          exact: false,
        },
        (oldData: InfiniteData<AgentThread[]> | undefined) =>
          filterInfiniteThreadsCache(oldData, (t) => t.thread_id !== threadId),
      );
    },
    onSettled() {
      void queryClient.invalidateQueries({ queryKey: ["threads", "search"] });
      void queryClient.invalidateQueries({
        queryKey: INFINITE_THREADS_QUERY_KEY_PREFIX,
      });
    },
  });
}

export function useRenameThread() {
  const queryClient = useQueryClient();
  const apiClient = getAPIClient();
  return useMutation({
    mutationFn: async ({
      threadId,
      title,
    }: {
      threadId: string;
      title: string;
    }) => {
      await apiClient.threads.updateState(threadId, {
        values: { title },
      });
    },
    onSuccess(_, { threadId, title }) {
      queryClient.setQueriesData(
        {
          queryKey: ["threads", "search"],
          exact: false,
        },
        (oldData: Array<AgentThread>) => {
          return oldData.map((t) => {
            if (t.thread_id === threadId) {
              return {
                ...t,
                values: {
                  ...t.values,
                  title,
                },
              };
            }
            return t;
          });
        },
      );
      queryClient.setQueriesData(
        {
          queryKey: INFINITE_THREADS_QUERY_KEY_PREFIX,
          exact: false,
        },
        (oldData: InfiniteData<AgentThread[]> | undefined) =>
          mapInfiniteThreadsCache(oldData, (t) =>
            t.thread_id === threadId
              ? {
                  ...t,
                  values: {
                    ...t.values,
                    title,
                  },
                }
              : t,
          ),
      );
    },
  });
}
