"use client";

import type { ChatStatus } from "ai";
import {
  BotIcon,
  BrainIcon,
  CheckIcon,
  EyeIcon,
  MessageCircleIcon,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ComponentProps,
} from "react";

import {
  PromptInput,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenuGroup,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/core/i18n/hooks";
import { useModels } from "@/core/models/hooks";
import { useSandboxCapacity } from "@/core/sandbox";
import type { AgentThreadContext } from "@/core/threads";
import { cn } from "@/lib/utils";

import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorName,
  ModelSelectorTrigger,
} from "../../ai-elements/model-selector";
import { ModeHoverGuide } from "../mode-hover-guide";

import {
  type InputMode,
  type ReasoningEffort,
  getReasoningEffortLevels,
  getResolvedMode,
  resolveReasoningEffort,
} from "./mode-utils";
import { PlusMenuButton } from "./plus-menu-button";
import { SuggestionList } from "./suggestion-list";

export function InputBox({
  className,
  disabled,
  autoFocus,
  status = "ready",
  context,
  extraHeader,
  isWelcomeMode,
  isNewThread,
  threadId: _threadId,
  initialValue,
  onContextChange,
  onSubmit,
  onStop,
  ...props
}: Omit<ComponentProps<typeof PromptInput>, "onSubmit"> & {
  assistantId?: string | null;
  status?: ChatStatus;
  disabled?: boolean;
  context: Omit<
    AgentThreadContext,
    "thread_id" | "is_plan_mode" | "thinking_enabled" | "subagent_enabled"
  > & {
    mode: "chat" | "computer" | undefined;
    reasoning_effort?: ReasoningEffort;
    tone_style?: "normal" | "formal" | "concise" | "explanatory" | "encouraging";
  };
  extraHeader?: React.ReactNode;
  isWelcomeMode?: boolean;
  isNewThread?: boolean;
  threadId: string;
  initialValue?: string;
  onContextChange?: (
    context: Omit<
      AgentThreadContext,
      "thread_id" | "is_plan_mode" | "thinking_enabled" | "subagent_enabled"
    > & {
      mode: "chat" | "computer" | undefined;
      reasoning_effort?: ReasoningEffort;
      tone_style?: "normal" | "formal" | "concise" | "explanatory" | "encouraging";
    },
  ) => void;
  onSubmit?: (message: PromptInputMessage) => void;
  onStop?: () => void;
}) {
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const [modelDialogOpen, setModelDialogOpen] = useState(false);
  const [sandboxCapacityWarningOpen, setSandboxCapacityWarningOpen] =
    useState(false);
  const { models } = useModels();
  const { capacity: sandboxCapacity } = useSandboxCapacity({
    enabled: isNewThread === true,
  });
  const sandboxCapacitySaturated =
    sandboxCapacity?.enabled === true && sandboxCapacity.saturated;
  const sandboxCapacityUnavailableForMode =
    sandboxCapacitySaturated && context.mode === "computer";
  const showWelcomeMode = isWelcomeMode ?? isNewThread;
  const resolvedMode = getResolvedMode(context.mode);
  const [computerIgniting, setComputerIgniting] = useState(false);
  const previousModeRef = useRef<InputMode>(resolvedMode);

  useEffect(() => {
    const previousMode = previousModeRef.current;
    previousModeRef.current = resolvedMode;

    if (previousMode !== "computer" && resolvedMode === "computer") {
      setComputerIgniting(true);
      const timeout = window.setTimeout(() => {
        setComputerIgniting(false);
      }, 900);
      return () => window.clearTimeout(timeout);
    }

    if (resolvedMode !== "computer") {
      setComputerIgniting(false);
    }
  }, [resolvedMode]);

  useEffect(() => {
    if (models.length === 0) {
      return;
    }
    const currentModel = models.find((m) => m.name === context.model_name);
    const fallbackModel = currentModel ?? models[0]!;
    const nextModelName = fallbackModel.name;
    const nextMode = getResolvedMode(context.mode);
    const nextEffort = resolveReasoningEffort(
      context.reasoning_effort,
      fallbackModel,
    );

    if (
      context.model_name === nextModelName &&
      context.mode === nextMode &&
      context.reasoning_effort === nextEffort
    ) {
      return;
    }

    onContextChange?.({
      ...context,
      model_name: nextModelName,
      mode: nextMode,
      reasoning_effort: nextEffort,
    });
  }, [context, models, onContextChange]);

  const selectedModel = useMemo(() => {
    if (models.length === 0) {
      return undefined;
    }
    return models.find((m) => m.name === context.model_name) ?? models[0];
  }, [context.model_name, models]);

  const resolvedModelName = selectedModel?.name;

  const supportReasoningEffort = useMemo(
    () => selectedModel?.supports_reasoning_effort ?? false,
    [selectedModel],
  );

  const reasoningEffortLevels = useMemo(
    () => getReasoningEffortLevels(selectedModel),
    [selectedModel],
  );

  const handleModelSelect = useCallback(
    (model_name: string) => {
      const model = models.find((m) => m.name === model_name);
      if (!model) {
        return;
      }
      const nextMode = getResolvedMode(context.mode);
      const nextEffort = resolveReasoningEffort(
        context.reasoning_effort,
        model,
      );
      onContextChange?.({
        ...context,
        model_name,
        mode: nextMode,
        reasoning_effort: nextEffort,
      });
      setModelDialogOpen(false);
    },
    [onContextChange, context, models],
  );

  const handleModeSelect = useCallback(
    (mode: InputMode) => {
      const nextMode = getResolvedMode(mode);
      if (
        sandboxCapacitySaturated &&
        nextMode === "computer"
      ) {
        onContextChange?.({
          ...context,
          mode: "chat",
        });
        setSandboxCapacityWarningOpen(true);
        return;
      }
      onContextChange?.({
        ...context,
        mode: nextMode,
      });
    },
    [
      onContextChange,
      context,
      sandboxCapacitySaturated,
    ],
  );

  const handleReasoningEffortSelect = useCallback(
    (effort: ReasoningEffort) => {
      onContextChange?.({
        ...context,
        reasoning_effort: effort,
      });
    },
    [onContextChange, context],
  );

  const handleToneStyleSelect = useCallback(
    (
      toneStyle:
        | "normal"
        | "formal"
        | "concise"
        | "explanatory"
        | "encouraging",
    ) => {
      onContextChange?.({
        ...context,
        tone_style: toneStyle,
      });
    },
    [onContextChange, context],
  );

  const handleSubmit = useCallback(
    async (message: PromptInputMessage) => {
      if (status === "streaming") {
        onStop?.();
        return;
      }
      if (!message.text) {
        return;
      }
      if (
        sandboxCapacitySaturated &&
        context.mode === "computer"
      ) {
        onContextChange?.({
          ...context,
          mode: "chat",
        });
        setSandboxCapacityWarningOpen(true);
        return;
      }

      // Guard against submitting before the initial model auto-selection
      // effect has flushed thread settings to storage/state.
      if (resolvedModelName && context.model_name !== resolvedModelName) {
        onContextChange?.({
          ...context,
          model_name: resolvedModelName,
          mode: getResolvedMode(
            context.mode,
          ),
          reasoning_effort: resolveReasoningEffort(
            context.reasoning_effort,
            selectedModel,
          ),
        });
        setTimeout(() => onSubmit?.(message), 0);
        return;
      }

      const nextEffort = resolveReasoningEffort(
        context.reasoning_effort,
        selectedModel,
      );
      if (context.reasoning_effort !== nextEffort) {
        onContextChange?.({
          ...context,
          reasoning_effort: nextEffort,
        });
        setTimeout(() => onSubmit?.(message), 0);
        return;
      }

      onSubmit?.(message);
    },
    [
      context,
      onContextChange,
      onSubmit,
      onStop,
      resolvedModelName,
      sandboxCapacitySaturated,
      selectedModel,
      status,
    ],
  );

  return (
    <div
      className={cn(
        "relative flex flex-col",
        showWelcomeMode ? "gap-3" : "gap-2",
      )}
    >
      <PromptInput
        className={cn(
          "bg-background/85 rounded-2xl backdrop-blur-sm transition-all duration-300 ease-out *:data-[slot='input-group']:rounded-2xl",
          resolvedMode === "computer" &&
            !sandboxCapacityUnavailableForMode &&
            "computer-input-active",
          computerIgniting &&
            !sandboxCapacityUnavailableForMode &&
            "computer-input-ignite",
          sandboxCapacityUnavailableForMode &&
            "border-muted bg-muted/55 shadow-none grayscale-[0.15] *:data-[slot='input-group']:bg-muted/55",
          className,
        )}
        disabled={disabled}
        globalDrop
        multiple
        onSubmit={handleSubmit}
        {...props}
      >
        {extraHeader && (
          <div className="absolute top-0 right-0 left-0 z-10">
            <div className="absolute right-0 bottom-0 left-0 flex items-center justify-center">
              {extraHeader}
            </div>
          </div>
        )}
        <PromptInputAttachments>
          {(attachment) => <PromptInputAttachment data={attachment} />}
        </PromptInputAttachments>
        <PromptInputBody className="absolute top-0 right-0 left-0 z-3">
          <PromptInputTextarea
            className={cn(
              "size-full",
              sandboxCapacityUnavailableForMode &&
                "text-muted-foreground placeholder:text-muted-foreground/55",
            )}
            disabled={disabled}
            placeholder={t.inputBox.placeholder}
            autoFocus={autoFocus}
            defaultValue={initialValue}
          />
        </PromptInputBody>
        <PromptInputFooter className="flex">
          <PromptInputTools>
            {/* TODO: Add more connectors here
          <PromptInputActionMenu>
            <PromptInputActionMenuTrigger className="px-2!" />
            <PromptInputActionMenuContent>
              <PromptInputActionAddAttachments
                label={t.inputBox.addAttachments}
              />
            </PromptInputActionMenuContent>
          </PromptInputActionMenu> */}
            <PlusMenuButton
              className="px-2!"
              toneStyle={context.tone_style}
              onToneStyleSelect={handleToneStyleSelect}
            />
            <PromptInputActionMenu>
              <ModeHoverGuide
                mode={
                  context.mode === "chat" || context.mode === "computer"
                    ? context.mode
                    : "chat"
                }
              >
                <PromptInputActionMenuTrigger className="gap-1! px-2!">
                  <div>
                    {context.mode === "chat" && (
                      <MessageCircleIcon className="size-3" />
                    )}
                    {context.mode === "computer" && (
                      <BotIcon className="size-3" />
                    )}
                  </div>
                  <div className="text-xs font-normal">
                    {(context.mode === "chat" && t.inputBox.chatMode) ||
                      (context.mode === "computer" && t.inputBox.computerMode)}
                  </div>
                </PromptInputActionMenuTrigger>
              </ModeHoverGuide>
              <PromptInputActionMenuContent className="w-80">
                <DropdownMenuGroup>
                  <DropdownMenuLabel className="text-muted-foreground text-xs">
                    {t.inputBox.mode}
                  </DropdownMenuLabel>
                  <PromptInputActionMenu>
                    <PromptInputActionMenuItem
                      className={cn(
                        context.mode === "chat"
                          ? "text-accent-foreground"
                          : "text-muted-foreground/65",
                      )}
                      onSelect={() => handleModeSelect("chat")}
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-1 font-bold">
                          <MessageCircleIcon
                            className={cn(
                              "mr-2 size-4",
                              context.mode === "chat" &&
                                "text-accent-foreground",
                            )}
                          />
                          {t.inputBox.chatMode}
                        </div>
                        <div className="pl-7 text-xs">
                          {t.inputBox.chatModeDescription}
                        </div>
                      </div>
                      {context.mode === "chat" ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </PromptInputActionMenuItem>
                    <PromptInputActionMenuItem
                      className={cn(
                        context.mode === "computer"
                          ? "text-accent-foreground"
                          : "text-muted-foreground/65",
                      )}
                      onSelect={() => handleModeSelect("computer")}
                    >
                      <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-1 font-bold">
                          <BotIcon
                            className={cn(
                              "mr-2 size-4",
                              context.mode === "computer" &&
                                "text-accent-foreground",
                            )}
                          />
                          {t.inputBox.computerMode}
                        </div>
                        <div className="pl-7 text-xs">
                          {t.inputBox.computerModeDescription}
                        </div>
                      </div>
                      {context.mode === "computer" ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </PromptInputActionMenuItem>
                  </PromptInputActionMenu>
                </DropdownMenuGroup>
              </PromptInputActionMenuContent>
            </PromptInputActionMenu>
          </PromptInputTools>
          <PromptInputTools>
            {supportReasoningEffort && (
              <PromptInputActionMenu>
                <PromptInputActionMenuTrigger className="gap-1! px-2!">
                  <div className="text-xs font-normal">
                    {t.inputBox.reasoningEffort}:
                    {context.reasoning_effort === "none" &&
                      " " + t.inputBox.reasoningEffortNone}
                    {context.reasoning_effort === "minimal" &&
                      " " + t.inputBox.reasoningEffortMinimal}
                    {context.reasoning_effort === "low" &&
                      " " + t.inputBox.reasoningEffortLow}
                    {context.reasoning_effort === "medium" &&
                      " " + t.inputBox.reasoningEffortMedium}
                    {context.reasoning_effort === "high" &&
                      " " + t.inputBox.reasoningEffortHigh}
                    {context.reasoning_effort === "max" &&
                      " " + t.inputBox.reasoningEffortMax}
                    {context.reasoning_effort === "xhigh" &&
                      " " + t.inputBox.reasoningEffortXhigh}
                  </div>
                </PromptInputActionMenuTrigger>
                <PromptInputActionMenuContent className="w-70">
                  <DropdownMenuGroup>
                    <DropdownMenuLabel className="text-muted-foreground text-xs">
                      {t.inputBox.reasoningEffort}
                    </DropdownMenuLabel>
                    <PromptInputActionMenu>
                      {reasoningEffortLevels.map((level) => {
                        const label = {
                          none: t.inputBox.reasoningEffortNone,
                          minimal: t.inputBox.reasoningEffortMinimal,
                          low: t.inputBox.reasoningEffortLow,
                          medium: t.inputBox.reasoningEffortMedium,
                          high: t.inputBox.reasoningEffortHigh,
                          max: t.inputBox.reasoningEffortMax,
                          xhigh: t.inputBox.reasoningEffortXhigh,
                        }[level];
                        const description = {
                          none: t.inputBox.reasoningEffortNoneDescription,
                          minimal: t.inputBox.reasoningEffortMinimalDescription,
                          low: t.inputBox.reasoningEffortLowDescription,
                          medium: t.inputBox.reasoningEffortMediumDescription,
                          high: t.inputBox.reasoningEffortHighDescription,
                          max: t.inputBox.reasoningEffortMaxDescription,
                          xhigh: t.inputBox.reasoningEffortXhighDescription,
                        }[level];
                        const isSelected =
                          context.reasoning_effort === level ||
                          (!context.reasoning_effort &&
                            level === reasoningEffortLevels[0]);
                        return (
                          <PromptInputActionMenuItem
                            key={level}
                            className={cn(
                              isSelected
                                ? "text-accent-foreground"
                                : "text-muted-foreground/65",
                            )}
                            onSelect={() => handleReasoningEffortSelect(level)}
                          >
                            <div className="flex flex-col gap-2">
                              <div className="flex items-center gap-1 font-bold">
                                {label}
                              </div>
                              <div className="pl-2 text-xs">{description}</div>
                            </div>
                            {isSelected ? (
                              <CheckIcon className="ml-auto size-4" />
                            ) : (
                              <div className="ml-auto size-4" />
                            )}
                          </PromptInputActionMenuItem>
                        );
                      })}
                    </PromptInputActionMenu>
                  </DropdownMenuGroup>
                </PromptInputActionMenuContent>
              </PromptInputActionMenu>
            )}
            <ModelSelector
              open={modelDialogOpen}
              onOpenChange={setModelDialogOpen}
            >
              <ModelSelectorTrigger asChild>
                <PromptInputButton>
                  <div className="flex min-w-0 flex-col items-start text-left">
                    <ModelSelectorName className="text-xs font-normal">
                      {selectedModel?.display_name}
                    </ModelSelectorName>
                  </div>
                </PromptInputButton>
              </ModelSelectorTrigger>
              <ModelSelectorContent>
                <ModelSelectorInput placeholder={t.inputBox.searchModels} />
                <ModelSelectorList>
                  {models.map((m) => (
                    <ModelSelectorItem
                      key={m.name}
                      value={m.name}
                      onSelect={() => handleModelSelect(m.name)}
                    >
                      <div className="flex min-w-0 flex-1 flex-col">
                        <ModelSelectorName>
                          {m.display_name}
                        </ModelSelectorName>
                        <span className="text-muted-foreground truncate text-[10px]">
                          {m.description ?? m.model}
                        </span>
                      </div>
                      {m.supports_thinking && (
                        <BrainIcon className="size-3.5 shrink-0 text-pink-400" />
                      )}
                      {m.supports_vision && (
                        <EyeIcon className="size-3.5 shrink-0 text-emerald-500" />
                      )}
                      {m.name === context.model_name ? (
                        <CheckIcon className="ml-auto size-4" />
                      ) : (
                        <div className="ml-auto size-4" />
                      )}
                    </ModelSelectorItem>
                  ))}
                </ModelSelectorList>
              </ModelSelectorContent>
            </ModelSelector>
            <PromptInputSubmit
              className="rounded-full"
              disabled={disabled}
              variant="outline"
              status={status}
            />
          </PromptInputTools>
        </PromptInputFooter>
        {!showWelcomeMode && (
          <div
            className={cn(
              "pointer-events-none absolute right-0 -bottom-[17px] left-0 z-0 h-4",
              resolvedMode === "computer" && !sandboxCapacityUnavailableForMode
                ? "bg-transparent"
                : "bg-background",
            )}
          />
        )}
      </PromptInput>

      {showWelcomeMode && searchParams.get("mode") !== "skill" && (
        <div className="flex items-center justify-center pt-1">
          <SuggestionList />
        </div>
      )}

      <Dialog
        open={sandboxCapacityWarningOpen}
        onOpenChange={setSandboxCapacityWarningOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>沙盒容量告急</DialogTitle>
            <DialogDescription>
              当前服务器沙盒容量已满，Computer
              模式暂时无法创建新的沙盒。请切换到 Chat
              模式后继续对话，稍后再尝试需要沙盒的任务。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              onClick={() => setSandboxCapacityWarningOpen(false)}
            >
              我知道了
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
