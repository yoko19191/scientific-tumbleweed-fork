import type { BaseStream } from "@langchain/langgraph-sdk/react";
import { Fragment, useEffect } from "react";

import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { useI18n } from "@/core/i18n/hooks";
import {
  accumulateUsage,
  splitTurns,
  type TokenUsage,
} from "@/core/messages/usage";
import {
  extractContentFromMessage,
  extractPresentFilesFromMessage,
  extractTextFromMessage,
  groupMessages,
  hasContent,
  hasPresentFiles,
  hasReasoning,
  hasSubagent,
} from "@/core/messages/utils";
import { useRehypeSplitWordsIntoSpans } from "@/core/rehype";
import type { Subtask } from "@/core/tasks";
import { useSubtaskContext } from "@/core/tasks/context";
import type { AgentThreadState } from "@/core/threads";
import { cn } from "@/lib/utils";

import { ArtifactFileList } from "../artifacts/artifact-file-list";
import { StreamingIndicator } from "../streaming-indicator";

import { MarkdownContent } from "./markdown-content";
import { MessageGroup } from "./message-group";
import { MessageListItem } from "./message-list-item";
import { MessageTokenUsage } from "./message-token-usage";
import { MessageListSkeleton } from "./skeleton";
import { SubtaskCard } from "./subtask-card";

export const MESSAGE_LIST_DEFAULT_PADDING_BOTTOM = 160;
export const MESSAGE_LIST_FOLLOWUPS_EXTRA_PADDING_BOTTOM = 80;

export function MessageList({
  className,
  threadId,
  thread,
  paddingBottom = MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
  tokenUsageEnabled = false,
}: {
  className?: string;
  threadId: string;
  thread: BaseStream<AgentThreadState>;
  paddingBottom?: number;
  tokenUsageEnabled?: boolean;
}) {
  const { t } = useI18n();
  const rehypePlugins = useRehypeSplitWordsIntoSpans(thread.isLoading);
  const { setTasks: setSubtasks } = useSubtaskContext();
  const messages = thread.messages;

  // Sync subtask state from messages in an effect, not during render.
  useEffect(() => {
    const next: Record<string, Subtask> = {};
    for (const message of messages) {
      if (message.type === "ai" && hasSubagent(message)) {
        for (const toolCall of message.tool_calls ?? []) {
          if (toolCall.name === "task" && toolCall.id) {
            next[toolCall.id] = {
              id: toolCall.id,
              subagent_type: toolCall.args.subagent_type,
              description: toolCall.args.description,
              prompt: toolCall.args.prompt,
              status: "in_progress",
            };
          }
        }
      } else if (message.type === "tool" && message.tool_call_id) {
        const existing = next[message.tool_call_id];
        if (existing) {
          const result = extractTextFromMessage(message);
          if (result.startsWith("Task Succeeded. Result:")) {
            existing.status = "completed";
            existing.result = result.split("Task Succeeded. Result:")[1]?.trim();
          } else if (result.startsWith("Task failed.")) {
            existing.status = "failed";
            existing.error = result.split("Task failed.")[1]?.trim();
          } else if (result.startsWith("Task timed out")) {
            existing.status = "failed";
            existing.error = result;
          }
        }
      }
    }
    setSubtasks((prev) => {
      // Preserve latestMessage and other fields not derived from messages
      const merged: Record<string, Subtask> = {};
      for (const [id, task] of Object.entries(next)) {
        merged[id] = { ...prev[id], ...task };
      }
      if (JSON.stringify(merged) === JSON.stringify(prev)) return prev;
      return merged;
    });
  }, [messages, setSubtasks]);

  if (thread.isThreadLoading && messages.length === 0) {
    return <MessageListSkeleton />;
  }

  // Aggregate token usage per turn (one human → next human exclusive).
  // The aggregated total is keyed by the message-id of the last visible ai
  // message in that turn; the renderer below appends a single inline token
  // card after the group whose last ai message matches that id.
  const turnUsageByLastAiId = new Map<string, TokenUsage>();
  if (tokenUsageEnabled) {
    const turns = splitTurns(messages);
    for (const turn of turns) {
      if (turn.lastAiIndex < 0) continue;
      const usage = accumulateUsage(turn.messages);
      if (!usage) continue;
      const anchor = messages[turn.lastAiIndex];
      const anchorId = anchor?.id;
      if (anchorId) turnUsageByLastAiId.set(anchorId, usage);
    }
  }

  /**
   * If `group` ends with the last ai message of a turn (and we have usage
   * for that turn), return its token usage so the caller can render a card
   * right after the group's content.
   */
  const groupTrailingUsage = (group: {
    messages: { id?: string; type: string }[];
  }): TokenUsage | null => {
    if (turnUsageByLastAiId.size === 0) return null;
    let lastAiId: string | undefined;
    for (const m of group.messages) {
      if (m.type === "ai" && m.id) lastAiId = m.id;
    }
    if (!lastAiId) return null;
    return turnUsageByLastAiId.get(lastAiId) ?? null;
  };

  return (
    <Conversation
      className={cn("flex size-full flex-col justify-center", className)}
    >
      <ConversationScrollButton bottomOffset={paddingBottom + 16} />
      <ConversationContent className="mx-auto w-full max-w-(--container-width-md) gap-8 pt-12">
        {groupMessages(messages, (group) => {
          const trailingUsage = groupTrailingUsage(group);
          const trailingCard = trailingUsage ? (
            <MessageTokenUsage enabled usage={trailingUsage} />
          ) : null;

          if (group.type === "human" || group.type === "assistant") {
            const items = group.messages.map((msg) => (
              <MessageListItem
                key={`${group.id}/${msg.id}`}
                message={msg}
                isLoading={thread.isLoading}
                threadId={threadId}
              />
            ));
            if (!trailingCard) return items;
            return (
              <Fragment key={`group-frag-${group.id}`}>
                {items}
                {trailingCard}
              </Fragment>
            );
          } else if (group.type === "assistant:clarification") {
            const message = group.messages[0];
            if (message && hasContent(message)) {
              return (
                <div key={group.id} className="w-full">
                  <MarkdownContent
                    content={extractContentFromMessage(message)}
                    isLoading={thread.isLoading}
                    rehypePlugins={rehypePlugins}
                  />
                  {trailingCard}
                </div>
              );
            }
            return null;
          } else if (group.type === "assistant:present-files") {
            const files: string[] = [];
            for (const message of group.messages) {
              if (hasPresentFiles(message)) {
                const presentFiles = extractPresentFilesFromMessage(message);
                files.push(...presentFiles);
              }
            }
            return (
              <div className="w-full" key={group.id}>
                {group.messages[0] && hasContent(group.messages[0]) && (
                  <MarkdownContent
                    content={extractContentFromMessage(group.messages[0])}
                    isLoading={thread.isLoading}
                    rehypePlugins={rehypePlugins}
                    className="mb-4"
                  />
                )}
                <ArtifactFileList files={files} threadId={threadId} />
                {trailingCard}
              </div>
            );
          } else if (group.type === "assistant:subagent") {
            const taskIds: string[] = [];
            for (const message of group.messages) {
              if (message.type === "ai") {
                for (const toolCall of message.tool_calls ?? []) {
                  if (toolCall.name === "task" && toolCall.id) {
                    taskIds.push(toolCall.id);
                  }
                }
              }
            }
            const results: React.ReactNode[] = [];
            for (const message of group.messages.filter(
              (message) => message.type === "ai",
            )) {
              if (hasReasoning(message)) {
                results.push(
                  <MessageGroup
                    key={"thinking-group-" + message.id}
                    messages={[message]}
                    isLoading={thread.isLoading}
                  />,
                );
              }
              results.push(
                <div
                  key="subtask-count"
                  className="text-muted-foreground pt-2 text-sm font-normal"
                >
                  {t.subtasks.executing(taskIds.length)}
                </div>,
              );
              const msgTaskIds = message.tool_calls
                ?.filter((toolCall) => toolCall.name === "task")
                .map((toolCall) => toolCall.id);
              for (const taskId of msgTaskIds ?? []) {
                results.push(
                  <SubtaskCard
                    key={"task-group-" + taskId}
                    taskId={taskId!}
                    isLoading={thread.isLoading}
                  />,
                );
              }
            }
            return (
              <div
                key={"subtask-group-" + group.id}
                className="relative z-1 flex flex-col gap-2"
              >
                {results}
                {trailingCard}
              </div>
            );
          }
          return (
            <div key={"group-" + group.id} className="w-full">
              <MessageGroup
                messages={group.messages}
                isLoading={thread.isLoading}
              />
              {trailingCard}
            </div>
          );
        })}
        {thread.isLoading && <StreamingIndicator className="my-4" />}
        <div style={{ height: `${paddingBottom}px` }} />
      </ConversationContent>
    </Conversation>
  );
}
