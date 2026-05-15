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
 * Accumulate token usage across all AI messages in a thread.
 */
export function accumulateUsage(messages: Message[]): TokenUsage | null {
  const cumulative: TokenUsage = {
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
  };
  let hasUsage = false;
  for (const message of messages) {
    const usage = getUsageMetadata(message);
    if (usage) {
      hasUsage = true;
      cumulative.inputTokens += usage.inputTokens;
      cumulative.outputTokens += usage.outputTokens;
      cumulative.totalTokens += usage.totalTokens;
    }
  }
  return hasUsage ? cumulative : null;
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
 * One conversation turn: a slice of messages anchored at a human message
 * (or the prelude before the first human, if the thread starts with ai).
 *
 * Used to render a single token usage card per turn rather than per-message.
 */
export interface MessageTurn {
  /** Stable id for React keys: id of the leading human message, or a synthetic prelude id. */
  id: string;
  /** Index in the source `messages` array of the last visible ai message in this turn,
   * or -1 if the turn contains no ai message yet. */
  lastAiIndex: number;
  /** Slice of messages belonging to this turn (used by accumulateUsage). */
  messages: Message[];
}

/**
 * Split a flat thread message list into per-human-turn segments.
 *
 * A turn starts at a human message (or message[0] if the thread leads with ai)
 * and runs until the next human message (exclusive). Turns whose `lastAiIndex`
 * is -1 contain no ai message yet — callers that render an inline artifact
 * anchored to the last ai message simply skip them.
 */
export function splitTurns(messages: Message[]): MessageTurn[] {
  const turns: MessageTurn[] = [];
  let currentId: string | null = null;
  let currentStart = 0;
  let lastAi = -1;

  const flush = (endExclusive: number) => {
    if (currentId === null) return;
    turns.push({
      id: currentId,
      lastAiIndex: lastAi,
      messages: messages.slice(currentStart, endExclusive),
    });
    currentId = null;
    lastAi = -1;
  };

  for (let i = 0; i < messages.length; i++) {
    const m = messages[i]!;
    if (m.type === "human") {
      flush(i);
      currentId = m.id ?? `turn-${i}`;
      currentStart = i;
    } else {
      if (currentId === null) {
        currentId = `turn-prelude-${i}`;
        currentStart = i;
      }
      if (m.type === "ai") lastAi = i;
    }
  }
  flush(messages.length);
  return turns;
}
