import type { Message, Thread } from "@langchain/langgraph-sdk";

import type { ReasoningEffort } from "../models/types";
import type { Todo } from "../todos";

export interface AgentThreadState extends Record<string, unknown> {
  title: string;
  messages: Message[];
  artifacts: string[];
  todos?: Todo[];
}

export interface AgentThreadContext extends Record<string, unknown> {
  thread_id: string;
  model_name: string | undefined;
  thinking_enabled: boolean;
  is_plan_mode: boolean;
  subagent_enabled: boolean;
  mode?: "chat" | "computer";
  reasoning_effort?: ReasoningEffort;
  max_concurrent_subagents?: number;
  agent_name?: string;
  tone_style?: "normal" | "formal" | "concise" | "explanatory" | "encouraging";
}

export interface AgentThread extends Thread<AgentThreadState> {
  context?: AgentThreadContext;
}

export interface ThreadTokenUsageModelBreakdown {
  tokens: number;
  runs: number;
}

export interface ThreadTokenUsageCallerBreakdown {
  lead_agent: number;
  subagent: number;
  middleware: number;
}

export interface ThreadTokenUsageResponse {
  thread_id: string;
  total_tokens: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_runs: number;
  by_model: Record<string, ThreadTokenUsageModelBreakdown>;
  by_caller: ThreadTokenUsageCallerBreakdown;
}
