"use client";

import { createContext, useContext, useMemo } from "react";

import {
  buildCitationNumbering,
  lookupCitationMetadata,
  normalizeCitationUrl,
  type CitationMetadata,
  type CitationNumbering,
  type CitationRegistry,
} from "@/core/messages/citations";

/**
 * Thread-level registry mapping citation URLs to their rich metadata
 * (title, authors, year, venue, citation count). Built once from the thread's
 * tool messages and shared with every rendered Markdown block.
 */
const CitationRegistryContext = createContext<CitationRegistry | null>(null);

/**
 * Block-level numbering. Each Markdown block (an answer, a subtask prompt, an
 * artifact) assigns its own 1..N citation numbers, so the same source gets a
 * stable number within that block.
 */
const CitationNumberingContext = createContext<CitationNumbering | null>(null);

export function CitationRegistryProvider({
  registry,
  children,
}: {
  registry: CitationRegistry;
  children: React.ReactNode;
}) {
  return (
    <CitationRegistryContext.Provider value={registry}>
      {children}
    </CitationRegistryContext.Provider>
  );
}

export function CitationNumberingProvider({
  content,
  children,
}: {
  content: string;
  children: React.ReactNode;
}) {
  const registry = useContext(CitationRegistryContext);
  const numbering = useMemo(
    () => buildCitationNumbering(content, registry),
    [content, registry],
  );
  return (
    <CitationNumberingContext.Provider value={numbering}>
      {children}
    </CitationNumberingContext.Provider>
  );
}

export function useCitationRegistry(): CitationRegistry | null {
  return useContext(CitationRegistryContext);
}

/**
 * Resolve the display number + metadata for a citation link href within the
 * current block. Returns `null` number when no numbering context is present
 * (e.g. content rendered outside a provider) so callers can fall back.
 */
export function useCitation(href: string | null | undefined): {
  number: number | null;
  metadata: CitationMetadata | null;
} {
  const registry = useContext(CitationRegistryContext);
  const numbering = useContext(CitationNumberingContext);
  const key = normalizeCitationUrl(href);
  const number = key ? (numbering?.byHref.get(key) ?? null) : null;
  const metadata = lookupCitationMetadata(registry, href);
  return { number, metadata };
}
