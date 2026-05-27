"use client";

import { ChevronDownIcon, CoinsIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useI18n } from "@/core/i18n/hooks";
import { formatTokenCount, type TokenUsage } from "@/core/messages/usage";
import {
  TOKEN_USAGE_PRESETS,
  type TokenUsagePreset,
} from "@/core/messages/usage-model";
import { cn } from "@/lib/utils";

interface TokenUsageIndicatorProps {
  usage: TokenUsage | null;
  enabled?: boolean;
  preset: TokenUsagePreset;
  onPresetChange: (preset: TokenUsagePreset) => void;
  className?: string;
}

export function TokenUsageIndicator({
  usage,
  enabled = false,
  preset,
  onPresetChange,
  className,
}: TokenUsageIndicatorProps) {
  const { t } = useI18n();

  if (!enabled) {
    return null;
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          className={cn(
            "text-muted-foreground bg-background/70 hover:bg-background/90 flex h-auto items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-normal",
            !usage && "opacity-60",
            className,
          )}
        >
          <CoinsIcon size={14} />
          <span className="font-mono">
            {preset === "off"
              ? t.tokenUsage.presets.off
              : usage
                ? formatTokenCount(usage.totalTokens)
                : "-"}
          </span>
          <ChevronDownIcon className="size-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="bottom" align="end" className="w-80">
        <DropdownMenuLabel>{t.tokenUsage.title}</DropdownMenuLabel>
        <div className="px-2 py-1 text-xs">
          {usage ? (
            <div className="space-y-1">
              <div className="flex justify-between gap-4">
                <span>{t.tokenUsage.input}</span>
                <span className="font-mono">
                  {formatTokenCount(usage.inputTokens)}
                </span>
              </div>
              <div className="flex justify-between gap-4">
                <span>{t.tokenUsage.output}</span>
                <span className="font-mono">
                  {formatTokenCount(usage.outputTokens)}
                </span>
              </div>
              <div className="border-t pt-1">
                <div className="flex justify-between gap-4">
                  <span>{t.tokenUsage.total}</span>
                  <span className="font-mono font-medium">
                    {formatTokenCount(usage.totalTokens)}
                  </span>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-muted-foreground max-w-56">
              {t.tokenUsage.unavailable}
            </div>
          )}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>{t.tokenUsage.view}</DropdownMenuLabel>
        <DropdownMenuRadioGroup
          value={preset}
          onValueChange={(value) => onPresetChange(value as TokenUsagePreset)}
        >
          {TOKEN_USAGE_PRESETS.map((value) => (
            <DropdownMenuRadioItem key={value} value={value}>
              <div className="grid gap-0.5">
                <span>{t.tokenUsage.presets[value]}</span>
                <span className="text-muted-foreground text-xs">
                  {t.tokenUsage.presetDescriptions[value]}
                </span>
              </div>
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
        <DropdownMenuSeparator />
        <div className="text-muted-foreground px-2 py-2 text-xs leading-relaxed">
          {t.tokenUsage.note}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
