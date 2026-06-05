import type { BaseStream } from "@langchain/langgraph-sdk/react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useEffect, useMemo } from "react";
import { useStickToBottomContext } from "use-stick-to-bottom";

import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { useI18n } from "@/core/i18n/hooks";
import { buildCitationRegistry } from "@/core/messages/citations";
import {
  accumulateUsage,
  splitTurns,
  type TokenUsage,
} from "@/core/messages/usage";
import {
  buildTokenDebugSteps,
  type TokenUsagePreset,
} from "@/core/messages/usage-model";
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
import { parseSubtaskResult, type Subtask } from "@/core/tasks";
import { useSetSubtasks } from "@/core/tasks/context";
import type { AgentThreadState } from "@/core/threads";
import { cn } from "@/lib/utils";

import { ArtifactFileList } from "../artifacts/artifact-file-list";
import { CitationRegistryProvider } from "../citations/context";
import { FollowupSuggestions } from "../followup-suggestions";
import { StreamingIndicator } from "../streaming-indicator";

import {
  ClarificationUI,
  type ClarificationResponse,
} from "./clarification-ui";
import { MarkdownContent } from "./markdown-content";
import { MessageGroup } from "./message-group";
import { MessageListItem } from "./message-list-item";
import {
  MessageTokenUsage,
  MessageTokenUsageDebugList,
} from "./message-token-usage";
import { MessageListSkeleton } from "./skeleton";
import { SubtaskCard } from "./subtask-card";

export const MESSAGE_LIST_DEFAULT_PADDING_BOTTOM = 24;
const VIRTUALIZED_TURN_THRESHOLD = 40;

export interface FollowupBlock {
  followups: string[];
  followupsLoading: boolean;
  showFollowups: boolean;
  setFollowupsHidden: (hidden: boolean) => void;
  onSelect: (suggestion: string) => void;
}

export function MessageList({
  className,
  threadId,
  thread,
  paddingBottom = MESSAGE_LIST_DEFAULT_PADDING_BOTTOM,
  tokenUsagePreset = "off",
  onClarificationSubmit,
  followupBlock,
}: {
  className?: string;
  threadId: string;
  thread: BaseStream<AgentThreadState>;
  paddingBottom?: number;
  tokenUsagePreset?: TokenUsagePreset;
  onClarificationSubmit?: (response: ClarificationResponse) => void;
  followupBlock?: FollowupBlock;
}) {
  const { t } = useI18n();
  const rehypePlugins = useRehypeSplitWordsIntoSpans(thread.isLoading);
  const setSubtasks = useSetSubtasks();
  const messages = thread.messages;
  const groupedMessages = useMemo(
    () =>
      groupMessages(messages, (group) => ({
        id: group.id,
        messages: group.messages,
        type: group.type,
      })),
    [messages],
  );
  const messageTurns = useMemo(() => splitTurns(messages), [messages]);
  const citationRegistry = useMemo(
    () => buildCitationRegistry(messages),
    [messages],
  );
  const showTurnUsage = tokenUsagePreset === "per_turn";
  const showStepDebug = tokenUsagePreset === "step_debug";

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
          Object.assign(existing, parseSubtaskResult(result));
        }
      }
    }
    setSubtasks((prev) => {
      let changed = Object.keys(prev).length !== Object.keys(next).length;
      const merged: Record<string, Subtask> = {};
      for (const [id, task] of Object.entries(next)) {
        const mergedTask = { ...prev[id], ...task };
        merged[id] = mergedTask;
        if (!areSubtasksShallowEqual(prev[id], mergedTask)) {
          changed = true;
        }
      }
      return changed ? merged : prev;
    });
  }, [messages, setSubtasks]);

  const { debugStepsByHumanId, turnUsageByHumanId } = useMemo(() => {
    const turnUsageByHumanId = new Map<string | null, TokenUsage | null>();
    const debugStepsByHumanId = new Map<
      string | null,
      ReturnType<typeof buildTokenDebugSteps>
    >();
    if (showTurnUsage || showStepDebug) {
      for (const turn of messageTurns) {
        if (showTurnUsage) {
          turnUsageByHumanId.set(turn.humanId, accumulateUsage(turn.messages));
        }
        if (showStepDebug) {
          debugStepsByHumanId.set(
            turn.humanId,
            buildTokenDebugSteps(turn.messages, t),
          );
        }
      }
    }
    return { debugStepsByHumanId, turnUsageByHumanId };
  }, [messageTurns, showStepDebug, showTurnUsage, t]);

  if (thread.isThreadLoading && messages.length === 0) {
    return <MessageListSkeleton />;
  }

  // Render each group via the existing per-type branches, capturing the
  // group's id alongside its node so we can inject a single token card at
  // the end of every turn afterwards.
  type GroupRender = {
    id: string | undefined;
    type: string;
    node: React.ReactNode;
  };
  const rendered: GroupRender[] = groupedMessages.map((group) => {
    let node: React.ReactNode = null;
    if (group.type === "human" || group.type === "assistant") {
      node = group.messages.map((msg) => (
        <MessageListItem
          key={`${group.id}/${msg.id}`}
          message={msg}
          isLoading={thread.isLoading}
          threadId={threadId}
          rehypePlugins={rehypePlugins}
        />
      ));
    } else if (group.type === "assistant:clarification") {
      const message = group.messages[0];
      if (message && hasContent(message)) {
        const rawUiSchema = (
          message as { additional_kwargs?: { ui_schema?: unknown } }
        ).additional_kwargs?.ui_schema;
        const uiSchema =
          typeof rawUiSchema === "string" ? rawUiSchema : undefined;
        const msgIndex = messages.findIndex((m) => m.id === message.id);
        const isAnswered = messages
          .slice(msgIndex + 1)
          .some((m) => m.type === "human");

        if (uiSchema) {
          node = (
            <div key={group.id} className="w-full">
              <ClarificationUI
                schema={uiSchema}
                fallbackContent={extractContentFromMessage(message)}
                onSubmit={(response: ClarificationResponse) => {
                  onClarificationSubmit?.(response);
                }}
                disabled={isAnswered}
              />
            </div>
          );
        } else {
          node = (
            <div key={group.id} className="w-full">
              <MarkdownContent
                content={extractContentFromMessage(message)}
                isLoading={thread.isLoading}
                rehypePlugins={rehypePlugins}
              />
            </div>
          );
        }
      }
    } else if (group.type === "assistant:present-files") {
      const files: string[] = [];
      for (const message of group.messages) {
        if (hasPresentFiles(message)) {
          const presentFiles = extractPresentFilesFromMessage(message);
          files.push(...presentFiles);
        }
      }
      node = (
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
              rehypePlugins={rehypePlugins}
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
              rehypePlugins={rehypePlugins}
            />,
          );
        }
      }
      node = (
        <div
          key={"subtask-group-" + group.id}
          className="relative z-1 flex flex-col gap-2"
        >
          {results}
        </div>
      );
    } else {
      node = (
        <div key={"group-" + group.id} className="w-full">
          <MessageGroup
            messages={group.messages}
            isLoading={thread.isLoading}
            rehypePlugins={rehypePlugins}
          />
        </div>
      );
    }
    return { id: group.id, type: group.type, node };
  });

  // Walk the rendered groups in order, segmenting at every `human` group.
  // After each turn's groups output a single MessageTokenUsage card. The
  // current human-id tracks which turn's aggregated usage to read.
  const turnItems: TurnRender[] = [];
  let currentHumanId: string | null = null;
  let buffer: React.ReactNode[] = [];
  let turnIndex = 0;

  const flushTurn = () => {
    if (buffer.length === 0) return;
    const usage = turnUsageByHumanId.get(currentHumanId) ?? null;
    const debugSteps = debugStepsByHumanId.get(currentHumanId) ?? [];
    turnItems.push({
      debugSteps,
      key: `turn-${currentHumanId ?? "prelude"}-${turnIndex}`,
      nodes: buffer,
      usage,
    });
    buffer = [];
    turnIndex += 1;
  };

  for (const g of rendered) {
    if (g.type === "human") {
      flushTurn();
      currentHumanId = g.id ?? null;
    }
    if (g.node !== null) buffer.push(g.node);
  }
  flushTurn();

  // Attach the follow-up suggestions block to the last turn so the pills
  // render under the most recent AI response, left-aligned with it.
  if (followupBlock && turnItems.length > 0) {
    const lastTurn = turnItems[turnItems.length - 1]!;
    turnItems[turnItems.length - 1] = { ...lastTurn, followupBlock };
  }

  return (
    <CitationRegistryProvider registry={citationRegistry}>
      <Conversation
        className={cn("flex size-full flex-col justify-center", className)}
      >
        <ConversationScrollButton bottomOffset={paddingBottom + 16} />
        <ConversationContent className="mx-auto w-full max-w-(--container-width-md) gap-8 pt-12">
          <TurnList
            turnItems={turnItems}
            showStepDebug={showStepDebug}
            showTurnUsage={showTurnUsage}
          />
          {thread.isLoading && <StreamingIndicator className="my-4" />}
          <div style={{ height: `${paddingBottom}px` }} />
        </ConversationContent>
      </Conversation>
    </CitationRegistryProvider>
  );
}

type TurnRender = {
  debugSteps: ReturnType<typeof buildTokenDebugSteps>;
  key: string;
  nodes: React.ReactNode[];
  usage: TokenUsage | null;
  followupBlock?: FollowupBlock;
};

function TurnList({
  turnItems,
  showStepDebug,
  showTurnUsage,
}: {
  turnItems: TurnRender[];
  showStepDebug: boolean;
  showTurnUsage: boolean;
}) {
  if (turnItems.length > VIRTUALIZED_TURN_THRESHOLD) {
    return (
      <VirtualizedTurnList
        turnItems={turnItems}
        showStepDebug={showStepDebug}
        showTurnUsage={showTurnUsage}
      />
    );
  }

  return turnItems.map((item) => (
    <TurnContent
      key={item.key}
      item={item}
      showStepDebug={showStepDebug}
      showTurnUsage={showTurnUsage}
    />
  ));
}

function VirtualizedTurnList({
  turnItems,
  showStepDebug,
  showTurnUsage,
}: {
  turnItems: TurnRender[];
  showStepDebug: boolean;
  showTurnUsage: boolean;
}) {
  const { scrollRef } = useStickToBottomContext();
  const rowVirtualizer = useVirtualizer<HTMLElement, HTMLDivElement>({
    count: turnItems.length,
    estimateSize: () => 360,
    getScrollElement: () => scrollRef.current,
    overscan: 6,
  });

  return (
    <div
      className="relative w-full"
      style={{ height: rowVirtualizer.getTotalSize() }}
    >
      {rowVirtualizer.getVirtualItems().map((virtualItem) => {
        const item = turnItems[virtualItem.index];
        if (!item) {
          return null;
        }

        return (
          <div
            key={item.key}
            ref={rowVirtualizer.measureElement}
            data-index={virtualItem.index}
            className="absolute top-0 left-0 w-full pb-8"
            style={{ transform: `translateY(${virtualItem.start}px)` }}
          >
            <TurnContent
              item={item}
              showStepDebug={showStepDebug}
              showTurnUsage={showTurnUsage}
            />
          </div>
        );
      })}
    </div>
  );
}

function TurnContent({
  item,
  showStepDebug,
  showTurnUsage,
}: {
  item: TurnRender;
  showStepDebug: boolean;
  showTurnUsage: boolean;
}) {
  return (
    <div className="flex w-full flex-col gap-8">
      {item.nodes}
      {showTurnUsage && item.usage && (
        <MessageTokenUsage enabled usage={item.usage} />
      )}
      {showStepDebug && (
        <MessageTokenUsageDebugList enabled steps={item.debugSteps} />
      )}
      {item.followupBlock && (
        <FollowupSuggestions
          followups={item.followupBlock.followups}
          followupsLoading={item.followupBlock.followupsLoading}
          showFollowups={item.followupBlock.showFollowups}
          setFollowupsHidden={item.followupBlock.setFollowupsHidden}
          onSelect={item.followupBlock.onSelect}
        />
      )}
    </div>
  );
}

function areSubtasksShallowEqual(
  prev: Subtask | undefined,
  next: Subtask,
): boolean {
  if (!prev) {
    return false;
  }
  const prevKeys = Object.keys(prev) as Array<keyof Subtask>;
  const nextKeys = Object.keys(next) as Array<keyof Subtask>;
  if (prevKeys.length !== nextKeys.length) {
    return false;
  }
  return nextKeys.every((key) => Object.is(prev[key], next[key]));
}
