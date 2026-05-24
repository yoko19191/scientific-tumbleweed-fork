"use client";

import type { Message } from "@langchain/langgraph-sdk";
import type { ChatStatus } from "ai";
import { XIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
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

export function FollowupSuggestions({
  followups,
  followupsLoading,
  showFollowups,
  setFollowupsHidden,
  onSelect,
}: {
  followups: string[];
  followupsLoading: boolean;
  showFollowups: boolean;
  setFollowupsHidden: (hidden: boolean) => void;
  onSelect: (suggestion: string) => void;
}) {
  const { t } = useI18n();

  const handleClick = useCallback(
    (suggestion: string) => {
      onSelect(suggestion);
    },
    [onSelect],
  );

  if (!showFollowups) return null;

  return (
    <>
      <div className="flex items-center justify-center pb-1">
        <div className="flex items-center gap-2">
          {followupsLoading ? (
            <div className="text-muted-foreground bg-background/80 rounded-full border px-4 py-1.5 text-xs backdrop-blur-sm">
              {t.inputBox.followupLoading}
            </div>
          ) : (
            <Suggestions className="w-fit items-center">
              {followups.map((s) => (
                <Tooltip key={s}>
                  <TooltipTrigger asChild>
                    <Suggestion
                      className="max-w-[min(22rem,calc(100vw-6rem))] overflow-hidden py-1.5 text-left whitespace-nowrap"
                      suggestion={<span className="min-w-0 truncate">{s}</span>}
                      onClick={() => handleClick(s)}
                    />
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[min(28rem,calc(100vw-2rem))] text-left break-words whitespace-normal">
                    {s}
                  </TooltipContent>
                </Tooltip>
              ))}
              <Button
                aria-label={t.common.close}
                className="text-muted-foreground h-auto cursor-pointer rounded-full px-2.5 py-1.5 text-xs font-normal"
                variant="outline"
                size="sm"
                type="button"
                onClick={() => setFollowupsHidden(true)}
              >
                <XIcon className="size-4" />
              </Button>
            </Suggestions>
          )}
        </div>
      </div>
    </>
  );
}
