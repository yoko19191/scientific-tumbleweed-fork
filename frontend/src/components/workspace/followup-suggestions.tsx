"use client";

import type { Message } from "@langchain/langgraph-sdk";
import type { ChatStatus } from "ai";
import { XIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { fetchWithAuth } from "@/core/auth/fetcher";
import { getBackendBaseURL } from "@/core/config";
import { useI18n } from "@/core/i18n/hooks";
import { textOfMessage } from "@/core/threads/utils";
import { cn } from "@/lib/utils";

export interface UseFollowupSuggestionsOptions {
  threadId: string;
  status: ChatStatus;
  disabled?: boolean;
  isNewThread?: boolean;
  isMock?: boolean;
  modelName?: string;
  messages: Message[];
  onVisibilityChange?: (visible: boolean) => void;
}

export function useFollowupSuggestions({
  threadId,
  status,
  disabled,
  isNewThread,
  isMock,
  modelName,
  messages,
  onVisibilityChange,
}: UseFollowupSuggestionsOptions) {
  const [followups, setFollowups] = useState<string[]>([]);
  const [followupsHidden, setFollowupsHidden] = useState(false);
  const [followupsLoading, setFollowupsLoading] = useState(false);
  const lastGeneratedForAiIdRef = useRef<string | null>(null);
  const wasStreamingRef = useRef(false);

  const showFollowups =
    !disabled &&
    !isNewThread &&
    !followupsHidden &&
    (followupsLoading || followups.length > 0);

  const visibilityChangeRef = useRef(onVisibilityChange);
  useEffect(() => {
    visibilityChangeRef.current = onVisibilityChange;
  }, [onVisibilityChange]);

  useEffect(() => {
    visibilityChangeRef.current?.(showFollowups);
  }, [showFollowups]);

  useEffect(() => {
    return () => visibilityChangeRef.current?.(false);
  }, []);

  useEffect(() => {
    const streaming = status === "streaming";
    const wasStreaming = wasStreamingRef.current;
    wasStreamingRef.current = streaming;
    if (!wasStreaming || streaming) return;
    if (disabled || isMock) return;

    const lastAi = [...messages].reverse().find((m) => m.type === "ai");
    const lastAiId = lastAi?.id ?? null;
    if (!lastAiId || lastAiId === lastGeneratedForAiIdRef.current) return;
    lastGeneratedForAiIdRef.current = lastAiId;

    const recent = messages
      .filter((m) => m.type === "human" || m.type === "ai")
      .map((m) => {
        const role = m.type === "human" ? "user" : "assistant";
        const content = textOfMessage(m) ?? "";
        return { role, content };
      })
      .filter((m) => m.content.trim().length > 0)
      .slice(-6);

    if (recent.length === 0) return;

    const controller = new AbortController();
    setFollowupsHidden(false);
    setFollowupsLoading(true);
    setFollowups([]);

    fetchWithAuth(
      `${getBackendBaseURL()}/api/threads/${threadId}/suggestions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: recent,
          n: 3,
          model_name: modelName ?? undefined,
        }),
        signal: controller.signal,
      },
    )
      .then(async (res) => {
        if (!res.ok) return { suggestions: [] as string[] };
        return (await res.json()) as { suggestions?: string[] };
      })
      .then((data) => {
        const suggestions = (data.suggestions ?? [])
          .map((s) => (typeof s === "string" ? s.trim() : ""))
          .filter((s) => s.length > 0)
          .slice(0, 5);
        setFollowups(suggestions);
      })
      .catch(() => setFollowups([]))
      .finally(() => setFollowupsLoading(false));

    return () => controller.abort();
  }, [modelName, disabled, isMock, status, messages, threadId]);

  return {
    followups,
    followupsLoading,
    showFollowups,
    setFollowupsHidden,
  };
}

export interface FollowupSuggestionsProps {
  followups: string[];
  followupsLoading: boolean;
  showFollowups: boolean;
  setFollowupsHidden: (hidden: boolean) => void;
  onSelect: (suggestion: string) => void;
  className?: string;
}

/**
 * Inline follow-up suggestions rendered under the last AI turn,
 * left-aligned with the assistant response and Token Usage badge.
 *
 * Clicking a suggestion is expected to paste the text into the chat input
 * (the parent's onSelect handler controls actual behavior).
 */
export function FollowupSuggestions({
  followups,
  followupsLoading,
  showFollowups,
  setFollowupsHidden,
  onSelect,
  className,
}: FollowupSuggestionsProps) {
  const { t } = useI18n();

  const handleClick = useCallback(
    (suggestion: string) => {
      onSelect(suggestion);
    },
    [onSelect],
  );

  if (!showFollowups) return null;

  return (
    <div
      className={cn(
        "text-muted-foreground mt-2 flex flex-col items-start gap-1.5",
        className,
      )}
    >
      {followupsLoading ? (
        <span className="text-[11px]">{t.inputBox.followupLoading}</span>
      ) : (
        <>
          <span className="text-[11px]">{t.inputBox.followupHeader}</span>
          <div className="flex flex-wrap items-center gap-1.5">
            {followups.map((s) => (
              <Tooltip key={s}>
                <TooltipTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="text-muted-foreground bg-muted/40 hover:bg-muted h-auto max-w-[min(22rem,calc(100vw-6rem))] cursor-pointer rounded-full border-transparent px-2.5 py-1 text-left text-[11px] font-normal"
                    onClick={() => handleClick(s)}
                  >
                    <span className="min-w-0 truncate">{s}</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="max-w-[min(28rem,calc(100vw-2rem))] text-left wrap-break-word whitespace-normal">
                  {s}
                </TooltipContent>
              </Tooltip>
            ))}
            <Button
              aria-label={t.common.close}
              className="text-muted-foreground hover:bg-muted h-auto cursor-pointer rounded-full px-1.5 py-1 text-[11px] font-normal"
              variant="ghost"
              size="sm"
              type="button"
              onClick={() => setFollowupsHidden(true)}
            >
              <XIcon className="size-3.5" />
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
