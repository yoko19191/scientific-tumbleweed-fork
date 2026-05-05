import type { BaseStream } from "@langchain/langgraph-sdk";
import { useEffect, useMemo } from "react";

import { useI18n } from "@/core/i18n/hooks";
import type { AgentThreadState } from "@/core/threads";

import { useThreadChat } from "./chats";
import { FlipDisplay } from "./flip-display";

const THINK_TAG_RE = /<think>[\s\S]*?<\/think>/gi;

function cleanTitle(raw: string | undefined | null): string | null {
  if (!raw) return null;
  const cleaned = raw.replace(THINK_TAG_RE, "").trim();
  return cleaned || null;
}

export function ThreadTitle({
  threadId,
  thread,
}: {
  className?: string;
  threadId: string;
  thread: BaseStream<AgentThreadState>;
}) {
  const { t } = useI18n();
  const { isNewThread } = useThreadChat();
  const title = useMemo(
    () => cleanTitle(thread.values?.title),
    [thread.values?.title],
  );

  useEffect(() => {
    let _title = t.pages.untitled;

    if (title) {
      _title = title;
    } else if (isNewThread) {
      _title = t.pages.newChat;
    }
    if (thread.isThreadLoading) {
      document.title = `Loading... - ${t.pages.appName}`;
    } else {
      document.title = `${_title} - ${t.pages.appName}`;
    }
  }, [
    isNewThread,
    title,
    t.pages.newChat,
    t.pages.untitled,
    t.pages.appName,
    thread.isThreadLoading,
  ]);

  if (!title) {
    return null;
  }
  return (
    <FlipDisplay uniqueKey={threadId}>
      {title}
    </FlipDisplay>
  );
}
