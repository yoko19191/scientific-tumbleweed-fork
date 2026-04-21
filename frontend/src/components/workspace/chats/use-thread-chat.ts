"use client";

import { useParams, usePathname, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { uuid } from "@/core/utils/uuid";

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
