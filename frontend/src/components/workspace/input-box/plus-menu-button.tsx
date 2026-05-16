"use client";

import {
  CheckIcon,
  PaperclipIcon,
  PlusIcon,
  SlidersHorizontalIcon,
} from "lucide-react";
import { useMemo } from "react";

import {
  PromptInputButton,
  usePromptInputAttachments,
} from "@/components/ai-elements/prompt-input";
import {
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/core/i18n/hooks";
import { cn } from "@/lib/utils";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../ui/dropdown-menu";

export function PlusMenuButton({
  className,
  toneStyle,
  onToneStyleSelect,
}: {
  className?: string;
  toneStyle?: "normal" | "formal" | "concise" | "explanatory" | "encouraging";
  onToneStyleSelect?: (
    tone: "normal" | "formal" | "concise" | "explanatory" | "encouraging",
  ) => void;
}) {
  const { t } = useI18n();
  const attachments = usePromptInputAttachments();
  const currentTone = toneStyle ?? "normal";

  const toneOptions = useMemo(
    () =>
      [
        {
          value: "normal" as const,
          label: t.inputBox.toneStyleNormal,
          description: t.inputBox.toneStyleNormalDescription,
        },
        {
          value: "formal" as const,
          label: t.inputBox.toneStyleFormal,
          description: t.inputBox.toneStyleFormalDescription,
        },
        {
          value: "concise" as const,
          label: t.inputBox.toneStyleConcise,
          description: t.inputBox.toneStyleConciseDescription,
        },
        {
          value: "explanatory" as const,
          label: t.inputBox.toneStyleExplanatory,
          description: t.inputBox.toneStyleExplanatoryDescription,
        },
        {
          value: "encouraging" as const,
          label: t.inputBox.toneStyleEncouraging,
          description: t.inputBox.toneStyleEncouragingDescription,
        },
      ] as const,
    [t],
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <PromptInputButton className={cn("px-2!", className)}>
          <PlusIcon className="size-3" />
        </PromptInputButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuItem onClick={() => attachments.openFileDialog()}>
          <PaperclipIcon className="mr-2 size-4" />
          {t.inputBox.addAttachments}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuSub>
          <DropdownMenuSubTrigger>
            <SlidersHorizontalIcon className="mr-2 size-4" />
            {t.inputBox.toneStyle}
          </DropdownMenuSubTrigger>
          <DropdownMenuSubContent className="w-56">
            {toneOptions.map((option) => (
              <DropdownMenuItem
                key={option.value}
                className={cn(
                  currentTone === option.value
                    ? "text-accent-foreground"
                    : "text-muted-foreground/65",
                )}
                onClick={() => onToneStyleSelect?.(option.value)}
              >
                <div className="flex flex-col gap-0.5">
                  <div className="font-medium">{option.label}</div>
                  <div className="text-xs opacity-70">
                    {option.description}
                  </div>
                </div>
                {currentTone === option.value ? (
                  <CheckIcon className="ml-auto size-4 shrink-0" />
                ) : (
                  <div className="ml-auto size-4 shrink-0" />
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuSubContent>
        </DropdownMenuSub>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
