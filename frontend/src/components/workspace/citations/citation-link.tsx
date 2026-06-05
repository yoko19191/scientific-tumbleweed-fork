import { ExternalLinkIcon } from "lucide-react";
import type { ComponentProps } from "react";

import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { useI18n } from "@/core/i18n/hooks";
import {
  getCitationLabelFromNode,
  getNodeText,
} from "@/core/messages/citations";
import { cn } from "@/lib/utils";

import { useCitation } from "./context";

/**
 * Inline citation renderer. Within a citation numbering context it renders a
 * compact gray superscript number (academic-style ¹²³); the hover card surfaces
 * the source's title, authors, year, venue, and citation count when available.
 * Clicking opens the source in a new tab.
 */
export function CitationLink({
  href,
  children,
  ...props
}: ComponentProps<"a">) {
  const { t } = useI18n();
  const { number, metadata } = useCitation(href);

  const domain = extractDomain(href ?? "");
  // children may already be stripped of the `citation:` prefix by callers, so
  // fall back to the raw node text when the prefix-aware label is absent.
  const childrenText =
    getCitationLabelFromNode(children) ?? getNodeText(children);
  const isGenericText =
    childrenText === "Source" ||
    childrenText === "来源" ||
    childrenText === t.citations.source;
  const meaningfulText = isGenericText ? null : childrenText;
  const fallbackText = meaningfulText ?? domain;

  // Prefer the curated registry title; fall back to the link's own text.
  const cardTitle = metadata?.title ?? fallbackText;
  const metaLine = metadata
    ? [
        metadata.authors?.slice(0, 3).join(", "),
        metadata.year ?? undefined,
        metadata.venue ?? undefined,
      ]
        .filter(Boolean)
        .join(" · ")
    : "";
  const { className, ...linkProps } = props;

  // No numbering context (e.g. rendered outside a provider): degrade to a
  // labeled gray chip so the citation is still visually distinct.
  const triggerLabel = number != null ? String(number) : fallbackText;

  return (
    <HoverCard closeDelay={0} openDelay={120}>
      <HoverCardTrigger asChild>
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "not-prose bg-muted text-muted-foreground hover:bg-muted-foreground/15 hover:text-foreground border-border/60 mx-0.5 inline-flex translate-y-[-0.35em] items-center justify-center rounded-[0.3rem] border align-baseline font-medium no-underline shadow-none transition-colors",
            number != null
              ? "h-[1.05rem] min-w-[1.05rem] px-1 text-[0.65em] leading-none tabular-nums"
              : "max-w-full gap-1 px-1.5 py-0.5 text-[0.72em] leading-none",
            "focus-visible:border-ring focus-visible:ring-ring/40 focus-visible:ring-[2px] focus-visible:outline-none",
            className,
          )}
          onClick={(e) => e.stopPropagation()}
          {...linkProps}
        >
          {number != null ? (
            triggerLabel
          ) : (
            <>
              <span className="min-w-0 truncate">{triggerLabel}</span>
              <ExternalLinkIcon className="size-3 shrink-0 opacity-60" />
            </>
          )}
        </a>
      </HoverCardTrigger>
      <HoverCardContent className="w-80 p-0" align="start">
        <div className="space-y-1.5 p-3">
          <div className="flex items-start gap-2">
            {number != null && (
              <span className="bg-muted text-muted-foreground border-border/60 mt-0.5 inline-flex size-5 shrink-0 items-center justify-center rounded-[0.3rem] border text-xs font-medium tabular-nums">
                {number}
              </span>
            )}
            <div className="min-w-0 space-y-1">
              {cardTitle && (
                <h4 className="text-foreground line-clamp-3 text-sm leading-tight font-medium">
                  {cardTitle}
                </h4>
              )}
              {metaLine && (
                <p className="text-muted-foreground truncate text-xs">
                  {metaLine}
                </p>
              )}
              {metadata?.citationCount != null && (
                <p className="text-muted-foreground text-xs">
                  {t.citations.citationsCount(metadata.citationCount)}
                </p>
              )}
            </div>
          </div>
          {href && (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary inline-flex items-center gap-1 pt-0.5 text-xs hover:underline"
            >
              {t.citations.visitSource}
              <ExternalLinkIcon className="size-3" />
            </a>
          )}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

function extractDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./i, "");
  } catch {
    return url;
  }
}
