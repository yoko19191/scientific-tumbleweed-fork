"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { type PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import { SandboxTrigger } from "@/components/workspace/artifacts/sandbox-trigger";
import {
  ChatBox,
  useSpecificChatMode,
  useThreadChat,
} from "@/components/workspace/chats";
import { ExportTrigger } from "@/components/workspace/export-trigger";
import {
  FollowupSuggestions,
  useFollowupSuggestions,
} from "@/components/workspace/followup-suggestions";
import { InputBox } from "@/components/workspace/input-box";
import {
  MessageList,
  MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
} from "@/components/workspace/messages";
import type { ClarificationResponse } from "@/components/workspace/messages/clarification-ui";
import { ThreadContext } from "@/components/workspace/messages/context";
import { SandboxCapacityIndicator } from "@/components/workspace/sandbox-capacity-indicator";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoList } from "@/components/workspace/todo-list";
import { TokenUsageIndicator } from "@/components/workspace/token-usage-indicator";
import { Welcome } from "@/components/workspace/welcome";
import { useAuth } from "@/core/auth/AuthProvider";
import { useI18n } from "@/core/i18n/hooks";
import { selectHeaderTokenUsage } from "@/core/messages/usage";
import { useModels } from "@/core/models/hooks";
import { useNotification } from "@/core/notification/hooks";
import { useThreadSettings } from "@/core/settings";
import { useThreadStream, useThreadTokenUsage } from "@/core/threads/hooks";
import { threadTokenUsageToTokenUsage } from "@/core/threads/token-usage";
import { textOfMessage } from "@/core/threads/utils";
import { env } from "@/env";
import { cn } from "@/lib/utils";

export default function ChatPage() {
  const { t } = useI18n();
  const router = useRouter();
  const { user } = useAuth();
  const { threadId, setThreadId, isNewThread, setIsNewThread, isMock } =
    useThreadChat();
  // `isNewThread` tracks whether the backend has the thread yet - gates the
  // SDK's history fetch (see issue #2746).  `isWelcomeMode` is the visual
  // welcome layout (centered input, hero, quick actions); we flip it to false
  // the moment the user submits so the UI animates immediately, even though
  // `isNewThread` stays true until the backend actually creates the thread.
  const [isWelcomeMode, setIsWelcomeMode] = useState(isNewThread);
  const [settings, setSettings] = useThreadSettings(threadId);
  const [mounted, setMounted] = useState(false);
  const [threadInaccessible, setThreadInaccessible] = useState(false);
  const { tokenUsageEnabled } = useModels();
  useSpecificChatMode();

  useEffect(() => {
    setMounted(true);
  }, []);

  // Reset inaccessible state when thread changes
  useEffect(() => {
    setThreadInaccessible(false);
  }, [threadId]);

  // Keep welcome layout in sync when navigating between threads (sidebar
  // clicks, "new chat" button).  Submitting in /chats/new flips the layout
  // via onSend below; `isNewThread` stays true until onStart, so this effect
  // is harmless during the submit transition.
  useEffect(() => {
    setIsWelcomeMode(isNewThread);
  }, [isNewThread]);

  const { showNotification } = useNotification();

  const [thread, sendMessage, isUploading, pendingUsageMessages] =
    useThreadStream({
      threadId: isNewThread ? undefined : threadId,
      context: settings.context,
      isMock,
      userId: user?.id,
      // onSend only animates the UI; do NOT flip `isNewThread` here - the
      // LangGraph SDK eagerly fetches /history the moment it receives a
      // thread id and assumes the thread exists on the backend (issue #2746).
      onSend: () => {
        setIsWelcomeMode(false);
      },
      onStart: (createdThreadId) => {
        setThreadId(createdThreadId);
        setIsNewThread(false);
        // ! Important: Never use next.js router for navigation in this case, otherwise it will cause the thread to re-mount and lose all states. Use native history API instead.
        history.replaceState(null, "", `/workspace/chats/${createdThreadId}`);
      },
      onFinish: (state) => {
        if (document.hidden || !document.hasFocus()) {
          let body = "Conversation finished";
          const lastMessage = state.messages.at(-1);
          if (lastMessage) {
            const textContent = textOfMessage(lastMessage);
            if (textContent) {
              body =
                textContent.length > 200
                  ? textContent.substring(0, 200) + "..."
                  : textContent;
            }
          }
          showNotification(state.title, { body });
        }
      },
    });
  const tokenUsagePreset = settings.tokenUsage.preset;
  const threadTokenUsage = useThreadTokenUsage(threadId, {
    enabled:
      tokenUsageEnabled &&
      !isNewThread &&
      !isMock &&
      tokenUsagePreset !== "off",
    includeActive: thread.isLoading,
  });
  const backendTokenUsage = useMemo(
    () => threadTokenUsageToTokenUsage(threadTokenUsage.data),
    [threadTokenUsage.data],
  );
  const headerTokenUsage = useMemo(
    () =>
      selectHeaderTokenUsage({
        backendUsage: backendTokenUsage,
        messages: thread.messages,
        pendingMessages: backendTokenUsage ? [] : pendingUsageMessages,
      }),
    [backendTokenUsage, pendingUsageMessages, thread.messages],
  );

  // Detect 401/403/404 errors from the stream - thread is not accessible to this user
  useEffect(() => {
    if (!thread.error || isNewThread) return;
    const err = thread.error as unknown;
    const status =
      typeof err === "object" && err !== null && "status" in err
        ? (err as { status: number }).status
        : typeof err === "object" && err !== null && "statusCode" in err
          ? (err as { statusCode: number }).statusCode
          : null;
    if (status === 401 || status === 403 || status === 404) {
      setThreadInaccessible(true);
    }
  }, [thread.error, isNewThread]);

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      const sendPromise = sendMessage(threadId, message);
      if ((message.files?.length ?? 0) > 0) {
        return sendPromise;
      }
      void sendPromise;
    },
    [sendMessage, threadId],
  );
  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);

  const threadStatus = thread.error
    ? ("error" as const)
    : thread.isLoading
      ? ("streaming" as const)
      : ("ready" as const);

  const { followups, followupsLoading, showFollowups, setFollowupsHidden } =
    useFollowupSuggestions({
      threadId,
      status: threadStatus,
      disabled: env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" || isUploading,
      isNewThread,
      isMock,
      modelName: settings.context.model_name,
      messages: thread.messages,
    });

  const handleFollowupSelect = useCallback(
    (suggestion: string) => {
      void sendMessage(threadId, { text: suggestion, files: [] });
      setFollowupsHidden(true);
    },
    [sendMessage, threadId, setFollowupsHidden],
  );

  const handleClarificationSubmit = useCallback(
    (response: ClarificationResponse) => {
      let text: string;
      if (response.type === "chat_escape") {
        text = response.message;
      } else {
        // Structured response: serialize as JSON with marker
        text = JSON.stringify({
          _genui_response: true,
          action: response.action,
          data: response.data,
        });
      }
      void sendMessage(threadId, { text, files: [] });
    },
    [sendMessage, threadId],
  );

  const todos = thread.values.todos ?? [];
  const showSandboxCapacity =
    isNewThread &&
    (settings.context.mode === "agent" || settings.context.mode === "swarm");

  // Show inaccessible state when thread is not owned by the current user
  if (threadInaccessible) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
        <p className="text-muted-foreground text-sm">
          {t.workspace.threadInaccessible ??
            "This conversation is not accessible."}
        </p>
        <button
          type="button"
          className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-md px-4 py-2 text-sm"
          onClick={() => router.push("/workspace/chats/new")}
        >
          {t.workspace.startNewChat ?? "Start a new chat"}
        </button>
      </div>
    );
  }

  return (
    <ThreadContext.Provider value={{ thread, isMock }}>
      <ChatBox threadId={threadId}>
        <div className="relative flex size-full min-h-0 justify-between">
          <header
            className={cn(
              "absolute top-0 right-0 left-0 z-30 flex h-12 shrink-0 items-center px-4",
              isWelcomeMode
                ? "bg-background/0 backdrop-blur-none"
                : "bg-background/80 shadow-xs backdrop-blur",
            )}
          >
            <div className="flex min-w-0 flex-1 items-center text-sm font-medium">
              <ThreadTitle threadId={threadId} thread={thread} />
            </div>
            <div className="flex items-center gap-2">
              {!isNewThread && (
                <>
                  <TokenUsageIndicator
                    enabled={tokenUsageEnabled}
                    usage={headerTokenUsage}
                    preset={tokenUsagePreset}
                    onPresetChange={(preset) =>
                      setSettings("tokenUsage", { preset })
                    }
                  />
                  <SandboxTrigger />
                </>
              )}
              <ExportTrigger threadId={threadId} />
              <ArtifactTrigger />
            </div>
          </header>
          {showSandboxCapacity && <SandboxCapacityIndicator />}
          <main className="flex min-h-0 max-w-full grow flex-col">
            <div className="flex min-h-0 flex-1 justify-center">
              <MessageList
                className={cn("size-full", !isWelcomeMode && "pt-10")}
                threadId={threadId}
                thread={thread}
                paddingBottom={MESSAGE_LIST_DEFAULT_PADDING_BOTTOM}
                tokenUsagePreset={tokenUsageEnabled ? tokenUsagePreset : "off"}
                onClarificationSubmit={handleClarificationSubmit}
              />
            </div>
            <div
              className={cn(
                "right-0 bottom-0 left-0 z-30 flex justify-center px-4",
                isWelcomeMode ? "absolute pb-[6px]" : "relative shrink-0 pb-4",
              )}
            >
              <div
                className={cn(
                  "relative w-full",
                  isWelcomeMode && "-translate-y-[calc(50vh-96px)]",
                  isWelcomeMode
                    ? "max-w-(--container-width-sm)"
                    : "max-w-(--container-width-md)",
                )}
              >
                <div
                  className={cn(
                    "right-0 left-0 z-0",
                    isWelcomeMode ? "absolute -top-4" : "relative",
                  )}
                >
                  <div
                    className={cn(
                      "right-0 bottom-0 left-0 flex flex-col-reverse",
                      isWelcomeMode ? "absolute" : "relative",
                    )}
                  >
                    {todos.length > 0 && (
                      <TodoList className="bg-background/5" todos={todos} />
                    )}
                    <FollowupSuggestions
                      followups={followups}
                      followupsLoading={followupsLoading}
                      showFollowups={showFollowups}
                      setFollowupsHidden={setFollowupsHidden}
                      onSelect={handleFollowupSelect}
                    />
                  </div>
                </div>
                {mounted ? (
                  <InputBox
                    className={cn(
                      "bg-background/5 w-full",
                      isWelcomeMode && "-translate-y-4",
                    )}
                    isWelcomeMode={isWelcomeMode}
                    isNewThread={isNewThread}
                    threadId={threadId}
                    autoFocus={isWelcomeMode}
                    status={threadStatus}
                    context={settings.context}
                    extraHeader={
                      isWelcomeMode && <Welcome mode={settings.context.mode} />
                    }
                    disabled={
                      env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ||
                      isUploading
                    }
                    onContextChange={(context) =>
                      setSettings("context", context)
                    }
                    onSubmit={handleSubmit}
                    onStop={handleStop}
                  />
                ) : (
                  <div
                    aria-hidden="true"
                    className={cn(
                      "bg-background/5 h-32 w-full rounded-2xl border",
                      isWelcomeMode && "-translate-y-4",
                    )}
                  />
                )}
                {!isNewThread && (
                  <p
                    className="text-muted-foreground/50 relative z-10 mt-2 text-center text-[10px] leading-none"
                  >
                    {t.inputBox.aiDisclaimer}
                  </p>
                )}
                {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" && (
                  <div className="text-muted-foreground/67 w-full translate-y-12 text-center text-xs">
                    {t.common.notAvailableInDemoMode}
                  </div>
                )}
              </div>
            </div>
          </main>
        </div>
      </ChatBox>
    </ThreadContext.Provider>
  );
}
