"use client";

import { useParams, usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { uuid } from "@/core/utils/uuid";

export const THREAD_CHAT_RESET_EVENT = "scientific-tumbleweed:thread-chat-reset";

type ThreadChatResetDetail = {
  deletedThreadId: string;
  nextPath: string;
  force?: boolean;
};

export function resetThreadChatAfterDelete(detail: ThreadChatResetDetail) {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(
    new CustomEvent<ThreadChatResetDetail>(THREAD_CHAT_RESET_EVENT, {
      detail,
    }),
  );
}

/** Validate that a string looks like a UUID (v4). */
function isValidUUID(id: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    id,
  );
}

export function useThreadChat() {
  const { thread_id: threadIdFromPath } = useParams<{ thread_id: string }>();
  const pathname = usePathname();

  const searchParams = useSearchParams();
  const [threadId, setThreadId] = useState(() => {
    if (threadIdFromPath === "new") return uuid();
    if (threadIdFromPath && isValidUUID(threadIdFromPath))
      return threadIdFromPath;
    // Invalid thread ID in URL — generate a fresh one to avoid 422
    return uuid();
  });

  const [isNewThread, setIsNewThread] = useState(
    () => threadIdFromPath === "new" || !isValidUUID(threadIdFromPath ?? ""),
  );

  useEffect(() => {
    const resetToNewThread = (event: Event) => {
      const detail = (event as CustomEvent<ThreadChatResetDetail>).detail;
      if (!detail?.nextPath) {
        return;
      }

      const currentPathname = window.location.pathname;
      const deletingCurrentThread =
        detail.force === true ||
        detail.deletedThreadId === threadId ||
        detail.deletedThreadId === threadIdFromPath ||
        currentPathname.endsWith(`/${detail.deletedThreadId}`);

      if (!deletingCurrentThread) {
        return;
      }

      setIsNewThread(true);
      setThreadId(uuid());
    };

    window.addEventListener(THREAD_CHAT_RESET_EVENT, resetToNewThread);
    return () =>
      window.removeEventListener(THREAD_CHAT_RESET_EVENT, resetToNewThread);
  }, [threadId, threadIdFromPath]);

  useEffect(() => {
    if (pathname.endsWith("/new")) {
      setIsNewThread(true);
      setThreadId(uuid());
      return;
    }
    // Guard: after history.replaceState updates the URL from /chats/new to
    // /chats/{UUID}, Next.js useParams may still return the stale "new" value
    // because replaceState does not trigger router updates.  Avoid propagating
    // this invalid thread ID to downstream hooks (e.g. useStream), which would
    // cause a 422 from LangGraph Server.
    if (!threadIdFromPath || threadIdFromPath === "new") {
      return;
    }
    // Reject any non-UUID thread ID from the URL
    if (!isValidUUID(threadIdFromPath)) {
      return;
    }
    setIsNewThread(false);
    setThreadId(threadIdFromPath);
  }, [pathname, threadIdFromPath]);
  const isMock = searchParams.get("mock") === "true";
  return { threadId, setThreadId, isNewThread, setIsNewThread, isMock };
}
