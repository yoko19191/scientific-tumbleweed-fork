"use client";

import { BotIcon, PlusSquare } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { PromptInputMessage } from "@/components/ai-elements/prompt-input";
import { usePromptInputController } from "@/components/ai-elements/prompt-input/context";
import { Button } from "@/components/ui/button";
import { AgentWelcome } from "@/components/workspace/agent-welcome";
import { ArtifactTrigger } from "@/components/workspace/artifacts";
import { SandboxTrigger } from "@/components/workspace/artifacts/sandbox-trigger";
import { ChatBox, useThreadChat } from "@/components/workspace/chats";
import { ExportTrigger } from "@/components/workspace/export-trigger";
import { useFollowupSuggestions } from "@/components/workspace/followup-suggestions";
import { InputBox } from "@/components/workspace/input-box";
import {
  MessageList,
  MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
} from "@/components/workspace/messages";
import type { ClarificationResponse } from "@/components/workspace/messages/clarification-ui";
import { ThreadContext } from "@/components/workspace/messages/context";
import { ThreadTitle } from "@/components/workspace/thread-title";
import { TodoList } from "@/components/workspace/todo-list";
import { TokenUsageIndicator } from "@/components/workspace/token-usage-indicator";
import { Tooltip } from "@/components/workspace/tooltip";
import { useAgent } from "@/core/agents";
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

export default function AgentChatPage() {
  const { t } = useI18n();
  const router = useRouter();

  const { agent_name } = useParams<{
    agent_name: string;
  }>();

  const { agent } = useAgent(agent_name);

  const { threadId, setThreadId, isNewThread, setIsNewThread } =
    useThreadChat();
  const [isWelcomeMode, setIsWelcomeMode] = useState(isNewThread);
  const [settings, setSettings] = useThreadSettings(threadId);
  const { tokenUsageEnabled } = useModels();

  const { showNotification } = useNotification();

  useEffect(() => {
    setIsWelcomeMode(isNewThread);
  }, [isNewThread]);

  const [thread, sendMessage, , pendingUsageMessages] = useThreadStream({
    threadId: isNewThread ? undefined : threadId,
    context: { ...settings.context, agent_name: agent_name },
    onSend: () => {
      setIsWelcomeMode(false);
    },
    onStart: (createdThreadId) => {
      setThreadId(createdThreadId);
      setIsNewThread(false);
      // ! Important: Never use next.js router for navigation in this case, otherwise it will cause the thread to re-mount and lose all states. Use native history API instead.
      history.replaceState(
        null,
        "",
        `/workspace/agents/${agent_name}/chats/${createdThreadId}`,
      );
    },
    onFinish: (state) => {
      if (document.hidden || !document.hasFocus()) {
        let body = "Conversation finished";
        const lastMessage = state.messages[state.messages.length - 1];
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
    enabled: tokenUsageEnabled && !isNewThread && tokenUsagePreset !== "off",
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

  const threadStatus = thread.error
    ? ("error" as const)
    : thread.isLoading
      ? ("streaming" as const)
      : ("ready" as const);

  const { followups, followupsLoading, showFollowups, setFollowupsHidden } =
    useFollowupSuggestions({
      threadId,
      status: threadStatus,
      disabled: env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true",
      isNewThread,
      isMock: false,
      modelName: settings.context.model_name,
      messages: thread.messages,
    });

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      // Hide previously-shown follow-ups now that a new turn is starting;
      // the hook will resurface fresh suggestions after the next AI reply.
      setFollowupsHidden(true);
      void sendMessage(threadId, message, { agent_name });
    },
    [sendMessage, threadId, agent_name, setFollowupsHidden],
  );

  const handleStop = useCallback(async () => {
    await thread.stop();
  }, [thread]);

  const promptInputController = usePromptInputController();
  const handleFollowupSelect = useCallback(
    (suggestion: string) => {
      promptInputController.textInput.setInput(suggestion);
      requestAnimationFrame(() => {
        const textarea = document.querySelector<HTMLTextAreaElement>(
          "textarea[name='message']",
        );
        if (textarea) {
          textarea.focus();
          const len = textarea.value.length;
          textarea.setSelectionRange(len, len);
        }
      });
    },
    [promptInputController],
  );

  const followupBlock = useMemo(
    () => ({
      followups,
      followupsLoading,
      showFollowups,
      setFollowupsHidden,
      onSelect: handleFollowupSelect,
    }),
    [
      followups,
      followupsLoading,
      showFollowups,
      setFollowupsHidden,
      handleFollowupSelect,
    ],
  );

  const handleClarificationSubmit = useCallback(
    (response: ClarificationResponse) => {
      let text: string;
      if (response.type === "chat_escape") {
        text = response.message;
      } else {
        text = JSON.stringify({
          _genui_response: true,
          action: response.action,
          data: response.data,
        });
      }
      void sendMessage(threadId, { text, files: [] }, { agent_name });
    },
    [sendMessage, threadId, agent_name],
  );

  const todos = thread.values.todos ?? [];

  return (
    <ThreadContext.Provider value={{ thread }}>
      <ChatBox threadId={threadId}>
        <div className="relative flex size-full min-h-0 justify-between">
          <header
            className={cn(
              "absolute top-0 right-0 left-0 z-30 flex h-12 shrink-0 items-center gap-2 px-4",
              isWelcomeMode
                ? "bg-background/0 backdrop-blur-none"
                : "bg-background/80 shadow-xs backdrop-blur",
            )}
          >
            {/* Agent badge */}
            <div className="flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-1">
              <BotIcon className="text-primary h-3.5 w-3.5" />
              <span className="text-xs font-medium">
                {agent?.name ?? agent_name}
              </span>
            </div>

            <div className="flex w-full items-center text-sm font-medium">
              <ThreadTitle threadId={threadId} thread={thread} />
            </div>
            <div className="mr-4 flex items-center">
              <Tooltip content={t.agents.newChat}>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => {
                    router.push(`/workspace/agents/${agent_name}/chats/new`);
                  }}
                >
                  <PlusSquare /> {t.agents.newChat}
                </Button>
              </Tooltip>
              <TokenUsageIndicator
                enabled={tokenUsageEnabled}
                usage={headerTokenUsage}
                preset={tokenUsagePreset}
                onPresetChange={(preset) =>
                  setSettings("tokenUsage", { preset })
                }
              />
              <SandboxTrigger />
              <ExportTrigger threadId={threadId} />
              <ArtifactTrigger />
            </div>
          </header>

          <main className="flex min-h-0 max-w-full grow flex-col">
            <div className="flex min-h-0 flex-1 justify-center">
              <MessageList
                className={cn("size-full", !isWelcomeMode && "pt-10")}
                threadId={threadId}
                thread={thread}
                paddingBottom={MESSAGE_LIST_DEFAULT_PADDING_BOTTOM}
                tokenUsagePreset={tokenUsageEnabled ? tokenUsagePreset : "off"}
                onClarificationSubmit={handleClarificationSubmit}
                followupBlock={isWelcomeMode ? undefined : followupBlock}
              />
            </div>

            <div
              className={cn(
                "right-0 bottom-0 left-0 z-30 flex justify-center px-4",
                isWelcomeMode ? "absolute" : "relative shrink-0",
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
                  </div>
                </div>

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
                    isWelcomeMode && (
                      <AgentWelcome agent={agent} agentName={agent_name} />
                    )
                  }
                  disabled={env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true"}
                  onContextChange={(context) => setSettings("context", context)}
                  onSubmit={handleSubmit}
                  onStop={handleStop}
                />
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
