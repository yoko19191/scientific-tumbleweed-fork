import { CoinsIcon } from "lucide-react";

import { useI18n } from "@/core/i18n/hooks";
import { formatTokenCount, type TokenUsage } from "@/core/messages/usage";
import { cn } from "@/lib/utils";

/**
 * Inline token usage artifact.
 *
 * Renders nothing when disabled or when no usage data is available — the
 * caller is expected to pass an aggregated `usage` (e.g. from
 * `accumulateUsage(turn.messages)`) or `null`.
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
        {t.tokenUsage.input}: {formatTokenCount(usage.inputTokens)}
      </span>
      <span>
        {t.tokenUsage.output}: {formatTokenCount(usage.outputTokens)}
      </span>
      <span className="font-medium">
        {t.tokenUsage.total}: {formatTokenCount(usage.totalTokens)}
      </span>
    </div>
  );
}
