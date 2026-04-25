"use client";

import { useI18n } from "@/core/i18n/hooks";
import type { Translations } from "@/core/i18n/locales/types";

import { Tooltip } from "./tooltip";

export type AgentMode = "chat" | "agent" | "swarm";

function getModeLabelKey(
  mode: AgentMode,
): keyof Pick<
  Translations["inputBox"],
  "chatMode" | "agentMode" | "swarmMode"
> {
  switch (mode) {
    case "chat":
      return "chatMode";
    case "agent":
      return "agentMode";
    case "swarm":
      return "swarmMode";
  }
}

function getModeDescriptionKey(
  mode: AgentMode,
): keyof Pick<
  Translations["inputBox"],
  "chatModeDescription" | "agentModeDescription" | "swarmModeDescription"
> {
  switch (mode) {
    case "chat":
      return "chatModeDescription";
    case "agent":
      return "agentModeDescription";
    case "swarm":
      return "swarmModeDescription";
  }
}

export function ModeHoverGuide({
  mode,
  children,
  showTitle = true,
}: {
  mode: AgentMode;
  children: React.ReactNode;
  /** When true, tooltip shows "ModeName: Description". When false, only description. */
  showTitle?: boolean;
}) {
  const { t } = useI18n();
  const label = t.inputBox[getModeLabelKey(mode)];
  const description = t.inputBox[getModeDescriptionKey(mode)];
  const content = showTitle ? `${label}: ${description}` : description;

  return <Tooltip content={content}>{children}</Tooltip>;
}
