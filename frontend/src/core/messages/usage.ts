import type { Message } from "@langchain/langgraph-sdk";

export interface TokenUsage {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
}

/**
 * Extract usage_metadata from an AI message if present.
 * The field is added by the backend (PR #1218) but not typed in the SDK.
 */
export function getUsageMetadata(message: Message): TokenUsage | null {
  if (message.type !== "ai") {
    return null;
  }
  const usage = (message as Record<string, unknown>).usage_metadata as
    | { input_tokens?: number; output_tokens?: number; total_tokens?: number }
    | undefined;
  if (!usage) {
    return null;
  }
  return {
    inputTokens: usage.input_tokens ?? 0,
    outputTokens: usage.output_tokens ?? 0,
    totalTokens: usage.total_tokens ?? 0,
  };
}

/**
 * Accumulate token usage across AI messages.
 *
 * Some rendering paths can see the same AI message more than once. Usage is
 * attached to the message, so a message id should only contribute once.
 */
export function accumulateUsage(messages: Message[]): TokenUsage | null {
  const cumulative: TokenUsage = {
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
  };
  let hasUsage = false;
  const countedMessageIds = new Set<string>();

  for (const message of messages) {
    const usage = getUsageMetadata(message);
    if (!usage) {
      continue;
    }

    if (message.id) {
      if (countedMessageIds.has(message.id)) {
        continue;
      }
      countedMessageIds.add(message.id);
    }

    hasUsage = true;
    cumulative.inputTokens += usage.inputTokens;
    cumulative.outputTokens += usage.outputTokens;
    cumulative.totalTokens += usage.totalTokens;
  }
  return hasUsage ? cumulative : null;
}

export function hasNonZeroUsage(
  usage: TokenUsage | null | undefined,
): usage is TokenUsage {
  return (
    usage !== null &&
    usage !== undefined &&
    (usage.inputTokens > 0 || usage.outputTokens > 0 || usage.totalTokens > 0)
  );
}

export function addUsage(base: TokenUsage, delta: TokenUsage): TokenUsage {
  return {
    inputTokens: base.inputTokens + delta.inputTokens,
    outputTokens: base.outputTokens + delta.outputTokens,
    totalTokens: base.totalTokens + delta.totalTokens,
  };
}

export function selectHeaderTokenUsage({
  backendUsage,
  messages,
  pendingMessages = [],
}: {
  backendUsage?: TokenUsage | null;
  messages: Message[];
  pendingMessages?: Message[];
}): TokenUsage | null {
  if (hasNonZeroUsage(backendUsage)) {
    const pendingUsage = accumulateUsage(pendingMessages);
    return pendingUsage ? addUsage(backendUsage, pendingUsage) : backendUsage;
  }
  return accumulateUsage(messages);
}

/**
 * Format a token count for display: 1234 -> "1,234", 12345 -> "12.3K"
 */
export function formatTokenCount(count: number): string {
  if (count < 10_000) {
    return count.toLocaleString();
  }
  return `${(count / 1000).toFixed(1)}K`;
}

/**
 * One conversation turn: messages from a human up to (but not including)
 * the next human. The leading `human` message is included so callers can
 * key React lists by it.
 *
 * If the thread starts with non-human messages, those form a synthetic
 * "prelude" turn whose `humanId` is null.
 */
export interface MessageTurn {
  /** id of the leading human message, or null for the prelude. */
  humanId: string | null;
  /** Stable id for React keys (humanId or "turn-prelude-<startIdx>"). */
  id: string;
  /** Slice of messages belonging to this turn. */
  messages: Message[];
}

/**
 * Split a flat thread message list into per-human-turn segments.
 *
 * A turn starts at a human message (or message[0] if the thread leads with
 * ai/tool) and runs until the next human message (exclusive). The function
 * preserves message order and never re-orders.
 */
export function splitTurns(messages: Message[]): MessageTurn[] {
  const turns: MessageTurn[] = [];
  let currentId: string | null = null;
  let currentHumanId: string | null = null;
  let currentStart = 0;

  const flush = (endExclusive: number) => {
    if (currentId === null) return;
    turns.push({
      id: currentId,
      humanId: currentHumanId,
      messages: messages.slice(currentStart, endExclusive),
    });
    currentId = null;
    currentHumanId = null;
  };

  for (let i = 0; i < messages.length; i++) {
    const m = messages[i]!;
    if (m.type === "human") {
      flush(i);
      currentHumanId = m.id ?? null;
      currentId = m.id ?? `turn-${i}`;
      currentStart = i;
    } else if (currentId === null) {
      currentHumanId = null;
      currentId = `turn-prelude-${i}`;
      currentStart = i;
    }
  }
  flush(messages.length);
  return turns;
}
