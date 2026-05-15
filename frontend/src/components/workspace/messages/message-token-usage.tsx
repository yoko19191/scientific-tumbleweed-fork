import { CoinsIcon } from "lucide-react";

import { useI18n } from "@/core/i18n/hooks";
import { formatTokenCount, type TokenUsage } from "@/core/messages/usage";
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
