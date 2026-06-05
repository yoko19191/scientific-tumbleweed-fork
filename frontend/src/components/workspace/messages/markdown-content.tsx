"use client";

import { useMemo } from "react";
import type { AnchorHTMLAttributes } from "react";

import {
  MessageResponse,
  type MessageResponseProps,
} from "@/components/ai-elements/message";
import {
  getCitationLabelFromNode,
  getNodeText,
  normalizeCitationUrl,
} from "@/core/messages/citations";
import { streamdownPlugins } from "@/core/streamdown";
import { cn } from "@/lib/utils";

import { CitationLink } from "../citations/citation-link";
import {
  CitationNumberingProvider,
  useCitationRegistry,
} from "../citations/context";

function isExternalUrl(href: string | undefined): boolean {
  return !!href && /^https?:\/\//.test(href);
}

export type MarkdownContentProps = {
  content: string;
  isLoading: boolean;
  rehypePlugins: MessageResponseProps["rehypePlugins"];
  className?: string;
  remarkPlugins?: MessageResponseProps["remarkPlugins"];
  components?: MessageResponseProps["components"];
};

/** Renders markdown content. */
export function MarkdownContent({
  content,
  rehypePlugins,
  className,
  remarkPlugins = streamdownPlugins.remarkPlugins,
  components: componentsFromProps,
}: MarkdownContentProps) {
  const registry = useCitationRegistry();

  const components = useMemo(() => {
    // The citation-aware `a` must win over any caller-provided `a`, otherwise
    // a spread override (e.g. artifact link resolution) silently disables
    // citation rendering. We compose: caller override first, then a wrapper
    // that intercepts citations before delegating.
    const { a: callerAnchor, ...restFromProps } = componentsFromProps ?? {};

    const anchor = (props: AnchorHTMLAttributes<HTMLAnchorElement>) => {
      // A link is a citation when it carries the `citation:` prefix OR its
      // href is a known source in the thread registry.
      const citationText = getCitationLabelFromNode(props.children);
      const hrefKey = normalizeCitationUrl(props.href);
      const isRegistered = !!hrefKey && (registry?.has(hrefKey) ?? false);
      if (citationText || isRegistered) {
        const label = citationText ?? getNodeText(props.children) ?? undefined;
        return <CitationLink {...props}>{label ?? props.children}</CitationLink>;
      }

      // Delegate non-citation links to the caller's override if present.
      if (callerAnchor) {
        const Anchor = callerAnchor as (
          p: AnchorHTMLAttributes<HTMLAnchorElement>,
        ) => React.ReactNode;
        return <Anchor {...props} />;
      }

      // Sanitize href — block dangerous protocols
      const href = props.href?.trim().toLowerCase();
      if (
        href &&
        !href.startsWith("http://") &&
        !href.startsWith("https://") &&
        !href.startsWith("mailto:") &&
        !href.startsWith("#") &&
        !href.startsWith("/")
      ) {
        // Strip dangerous protocols (javascript:, data:, vbscript:, etc.)
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { href: _blocked, ...safeProps } = props;
        return <span {...safeProps} />;
      }
      const { className, target, rel, ...rest } = props;
      const external = isExternalUrl(props.href);
      return (
        <a
          {...rest}
          className={cn(
            "text-primary decoration-primary/30 hover:decoration-primary/60 underline underline-offset-2 transition-colors",
            className,
          )}
          target={target ?? (external ? "_blank" : undefined)}
          rel={rel ?? (external ? "noopener noreferrer" : undefined)}
        />
      );
    };

    return {
      ...restFromProps,
      a: anchor,
    };
  }, [componentsFromProps, registry]);

  if (!content) return null;

  return (
    <CitationNumberingProvider content={content}>
      <MessageResponse
        className={className}
        remarkPlugins={remarkPlugins}
        rehypePlugins={rehypePlugins}
        components={components}
      >
        {content}
      </MessageResponse>
    </CitationNumberingProvider>
  );
}
