import type { Model } from "@/core/models/types";

export type InputMode = "chat" | "agent" | "swarm";
export type ReasoningEffort = "minimal" | "low" | "medium" | "high" | "max";

export const REASONING_EFFORT_VALUES = [
  "minimal",
  "low",
  "medium",
  "high",
  "max",
] as const satisfies readonly ReasoningEffort[];

export const DEFAULT_REASONING_EFFORT_LEVELS: ReasoningEffort[] = [
  "minimal",
  "low",
  "medium",
  "high",
];

export function getResolvedMode(
  mode: InputMode | undefined,
  supportsThinking: boolean,
): InputMode {
  const validModes = new Set<InputMode>(["chat", "agent", "swarm"]);
  const effectiveMode =
    mode && validModes.has(mode) ? mode : undefined;

  if (!supportsThinking && effectiveMode !== "chat") {
    return "chat";
  }
  if (effectiveMode) {
    return effectiveMode;
  }
  return supportsThinking ? "agent" : "chat";
}

export function isReasoningEffort(value: string | undefined | null): value is ReasoningEffort {
  return REASONING_EFFORT_VALUES.includes(value as ReasoningEffort);
}

export function getModeDefaultReasoningEffort(mode: InputMode | undefined): ReasoningEffort {
  return mode === "swarm" ? "high" : mode === "agent" ? "high" : "medium";
}

export function getReasoningEffortLevels(model: Model | undefined): ReasoningEffort[] {
  const configuredLevels = model?.reasoning_effort_levels
    ?.filter(isReasoningEffort);
  if (configuredLevels && configuredLevels.length > 0) {
    return configuredLevels;
  }
  return DEFAULT_REASONING_EFFORT_LEVELS;
}

export function resolveReasoningEffort(
  current: ReasoningEffort | undefined,
  model: Model | undefined,
  mode: InputMode | undefined,
  preferModeDefault = false,
): ReasoningEffort | undefined {
  if (!model?.supports_reasoning_effort) {
    return undefined;
  }
  const levels = getReasoningEffortLevels(model);
  const modelDefault = isReasoningEffort(model.default_reasoning_effort)
    ? model.default_reasoning_effort
    : undefined;
  const modeDefault = getModeDefaultReasoningEffort(mode);
  const candidates = preferModeDefault
    ? [modeDefault, modelDefault, current, levels[0]]
    : [current, modelDefault, modeDefault, levels[0]];
  return candidates.find((effort): effort is ReasoningEffort =>
    Boolean(effort && levels.includes(effort)),
  );
}
