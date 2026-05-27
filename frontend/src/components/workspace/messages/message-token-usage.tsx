import { CoinsIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useI18n } from "@/core/i18n/hooks";
import { formatTokenCount, type TokenUsage } from "@/core/messages/usage";
import type { TokenDebugStep } from "@/core/messages/usage-model";
import { useTweenNumber } from "@/core/utils/use-tween-number";
import { cn } from "@/lib/utils";

/**
 * Inline token usage artifact.
 *
 * Renders nothing when disabled or when no usage data is available — the
 * caller passes an aggregated `usage` (e.g. from `accumulateUsage(turn)`) or
 * `null`. Numeric fields tween between updates so live streaming counts feel
 * animated rather than snapping.
 */
export function MessageTokenUsage({
  className,
  enabled = false,
  usage,
}: {
  className?: string;
  enabled?: boolean;
  usage: TokenUsage | null;
}) {
  const { t } = useI18n();

  // Hooks must run unconditionally; render is short-circuited below.
  const inputDisplay = useTweenNumber(usage?.inputTokens ?? 0);
  const outputDisplay = useTweenNumber(usage?.outputTokens ?? 0);
  const totalDisplay = useTweenNumber(usage?.totalTokens ?? 0);

  if (!enabled || !usage) {
    return null;
  }

  return (
    <div
      className={cn(
        "text-muted-foreground border-border/60 mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 border-t pt-2 text-[11px]",
        className,
      )}
    >
      <span className="inline-flex items-center gap-1 font-medium">
        <CoinsIcon className="size-3" />
        {t.tokenUsage.label}
      </span>
      <span>
        {t.tokenUsage.input}:{" "}
        <span className="tabular-nums">
          {formatTokenCount(Math.round(inputDisplay))}
        </span>
      </span>
      <span>
        {t.tokenUsage.output}:{" "}
        <span className="tabular-nums">
          {formatTokenCount(Math.round(outputDisplay))}
        </span>
      </span>
      <span className="font-medium">
        {t.tokenUsage.total}:{" "}
        <span className="tabular-nums">
          {formatTokenCount(Math.round(totalDisplay))}
        </span>
      </span>
    </div>
  );
}

export function MessageTokenUsageDebugList({
  className,
  enabled = false,
  steps,
}: {
  className?: string;
  enabled?: boolean;
  steps: TokenDebugStep[];
}) {
  const { t } = useI18n();

  if (!enabled || steps.length === 0) {
    return null;
  }

  return (
    <div className={cn("border-border/60 mt-1 border-t pt-2", className)}>
      <div className="space-y-2">
        {steps.map((step) => (
          <div
            key={step.id}
            className="bg-muted/30 border-border/50 flex items-start justify-between gap-3 rounded-md border px-3 py-2"
          >
            <div className="min-w-0 flex-1 space-y-1">
              <div className="text-foreground flex items-center gap-2 text-xs font-medium">
                <CoinsIcon className="text-muted-foreground size-3" />
                <span className="truncate">{step.label}</span>
              </div>
              {step.secondaryLabels.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {step.secondaryLabels.map((label, index) => (
                    <Badge
                      key={`${step.id}-${index}-${label}`}
                      className="px-1.5 py-0 text-[10px] font-normal"
                      variant="secondary"
                    >
                      {label}
                    </Badge>
                  ))}
                </div>
              )}
              {step.sharedAttribution && (
                <div className="text-muted-foreground text-[11px]">
                  {t.tokenUsage.sharedAttribution}
                </div>
              )}
              <div className="text-muted-foreground text-[11px]">
                {step.usage ? (
                  <>
                    {t.tokenUsage.input}:{" "}
                    {formatTokenCount(step.usage.inputTokens)}
                    {" · "}
                    {t.tokenUsage.output}:{" "}
                    {formatTokenCount(step.usage.outputTokens)}
                  </>
                ) : (
                  t.tokenUsage.unavailableShort
                )}
              </div>
            </div>
            <Badge className="shrink-0 font-mono" variant="outline">
              {step.usage
                ? `${formatTokenCount(step.usage.totalTokens)} ${t.tokenUsage.label}`
                : t.tokenUsage.unavailableShort}
            </Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
