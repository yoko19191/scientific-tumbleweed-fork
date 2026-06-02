import type { Model, ReasoningEffort } from "@/core/models/types";

export type InputMode = "chat" | "computer";
export type { ReasoningEffort };

export const REASONING_EFFORT_VALUES = [
  "none",
  "minimal",
  "low",
  "medium",
  "high",
  "max",
  "xhigh",
] as const satisfies readonly ReasoningEffort[];

export const DEFAULT_REASONING_EFFORT_LEVELS: ReasoningEffort[] = [
  "minimal",
  "low",
  "medium",
  "high",
];

export function getResolvedMode(
  mode: InputMode | undefined,
): InputMode {
  const validModes = new Set<InputMode>(["chat", "computer"]);
  const effectiveMode =
    mode && validModes.has(mode) ? mode : undefined;

  if (effectiveMode) {
    return effectiveMode;
  }
  return "chat";
}

export function isReasoningEffort(value: string | undefined | null): value is ReasoningEffort {
  return REASONING_EFFORT_VALUES.includes(value as ReasoningEffort);
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
): ReasoningEffort | undefined {
  if (!model?.supports_reasoning_effort) {
    return undefined;
  }
  const levels = getReasoningEffortLevels(model);
  const modelDefault = isReasoningEffort(model.default_reasoning_effort)
    ? model.default_reasoning_effort
    : undefined;
  const candidates = [current, modelDefault, levels[0]];
  return candidates.find((effort): effort is ReasoningEffort =>
    Boolean(effort && levels.includes(effort)),
  );
}
