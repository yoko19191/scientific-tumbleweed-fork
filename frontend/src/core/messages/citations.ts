export type CitationLike = {
  citationUrl?: unknown;
  citationTitle?: unknown;
  paperId?: unknown;
  title?: unknown;
  url?: unknown;
};

export type FetchedCitation = {
  citationUrl: string | null;
  citationTitle: string | null;
};

export function getCitationLabelFromNode(children: unknown) {
  const text = getNodeText(children);
  return text == null ? null : stripCitationPrefix(text);
}

/** Concatenate the plain-text content of a React children node, if any. */
export function getNodeText(children: unknown): string | null {
  if (typeof children === "string" || typeof children === "number") {
    const text = String(children).trim();
    return text.length ? text : null;
  }
  if (Array.isArray(children)) {
    const text = children
      .map((child) =>
        typeof child === "string" || typeof child === "number"
          ? String(child)
          : "",
      )
      .join("")
      .trim();
    return text.length ? text : null;
  }
  return null;
}

export function stripCitationPrefix(text: string) {
  const match = /^citation:\s*(.+)$/i.exec(text.trim());
  return match?.[1]?.trim() ?? null;
}

export function getCanonicalCitationUrl(item: CitationLike | null | undefined) {
  const value = item?.citationUrl;
  if (typeof value !== "string") {
    return null;
  }
  const url = value.trim();
  if (!/^https?:\/\//i.test(url)) {
    return null;
  }
  return url;
}

export function getToolCardCitationHref(
  item: CitationLike | null | undefined,
) {
  return getCanonicalCitationUrl(item);
}

export function getCitationDisplayTitle(
  item: CitationLike | null | undefined,
) {
  const citationTitle = item?.citationTitle;
  if (typeof citationTitle === "string" && citationTitle.trim()) {
    return citationTitle.trim();
  }
  const title = item?.title;
  if (typeof title === "string" && title.trim()) {
    return title.trim();
  }
  return null;
}

export function extractFetchedCitation(content: string): FetchedCitation {
  return {
    citationUrl: extractHeaderValue(content, "citationUrl"),
    citationTitle: extractHeaderValue(content, "citationTitle"),
  };
}

function extractHeaderValue(content: string, key: string) {
  const match = new RegExp(`^${key}:\\s*(.+?)\\s*$`, "im").exec(content);
  const value = match?.[1]?.trim();
  return value?.length ? value : null;
}

/* -------------------------------------------------------------------------- */
/* Citation registry + numbering                                             */
/*                                                                            */
/* The model emits citations in answer prose as Markdown links — either       */
/* `[citation:Title](url)` or plain `[Title](url)`. The rich metadata for a    */
/* citation (authors, year, venue, citation count) only exists in the tool     */
/* results that produced it. We build a url -> metadata registry from those    */
/* tool messages, then assign stable 1..N numbers to the citations that        */
/* appear in a given block of Markdown.                                        */
/* -------------------------------------------------------------------------- */

export type CitationMetadata = {
  url: string;
  title: string | null;
  authors?: string[] | null;
  year?: number | null;
  venue?: string | null;
  citationCount?: number | null;
  provider?: string | null;
  type?: string | null;
};

export type CitationRegistry = Map<string, CitationMetadata>;

export type MarkdownLink = {
  text: string;
  href: string;
  isCitationPrefixed: boolean;
};

export type CitationEntry = {
  number: number;
  href: string;
  metadata: CitationMetadata | null;
};

export type CitationNumbering = {
  /** Normalized href -> display number. */
  byHref: Map<string, number>;
  /** Ordered, de-duplicated citations as they first appear. */
  entries: CitationEntry[];
};

type ToolMessageLike = {
  type?: unknown;
  name?: unknown;
  content?: unknown;
};

/** Normalize a URL for use as a registry/numbering key (trim + drop trailing slash). */
export function normalizeCitationUrl(url: string | null | undefined): string {
  if (typeof url !== "string") {
    return "";
  }
  let value = url.trim();
  if (value.length > 1 && value.endsWith("/")) {
    value = value.slice(0, -1);
  }
  return value;
}

function asTrimmedString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function asFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() && !Number.isNaN(Number(value))) {
    return Number(value);
  }
  return null;
}

function asStringArray(value: unknown): string[] | null {
  if (!Array.isArray(value)) {
    return null;
  }
  const items = value.filter(
    (item): item is string => typeof item === "string" && item.trim().length > 0,
  );
  return items.length ? items : null;
}

function toolMessageText(content: unknown): string {
  if (typeof content === "string") {
    return content;
  }
  if (Array.isArray(content)) {
    return content
      .map((part) =>
        part &&
        typeof part === "object" &&
        "text" in part &&
        typeof (part as { text: unknown }).text === "string"
          ? (part as { text: string }).text
          : "",
      )
      .join("\n");
  }
  return "";
}

/** Pull citation-shaped records out of a parsed tool result of unknown shape. */
function collectCitationItems(json: unknown): Record<string, unknown>[] {
  const out: Record<string, unknown>[] = [];
  const push = (value: unknown) => {
    if (value && typeof value === "object" && !Array.isArray(value)) {
      out.push(value as Record<string, unknown>);
    }
  };
  if (Array.isArray(json)) {
    json.forEach(push);
    return out;
  }
  if (json && typeof json === "object") {
    const obj = json as Record<string, unknown>;
    if (Array.isArray(obj.results)) {
      obj.results.forEach(push);
    }
    if (Array.isArray(obj.nodes)) {
      obj.nodes.forEach(push);
    }
    push(obj.paper);
    if ("citationUrl" in obj || "paperId" in obj || "url" in obj) {
      push(obj);
    }
  }
  return out;
}

function registerCitationItem(
  registry: CitationRegistry,
  item: Record<string, unknown>,
) {
  const aliasUrls = [
    item.citationUrl,
    item.doiUrl,
    item.providerUrl,
    item.url,
  ]
    .map(asTrimmedString)
    .filter((value): value is string => Boolean(value));

  const primary = asTrimmedString(item.citationUrl) ?? aliasUrls[0] ?? null;
  if (!primary) {
    return;
  }

  const metadata: CitationMetadata = {
    url: primary,
    title: asTrimmedString(item.citationTitle) ?? asTrimmedString(item.title),
    authors: asStringArray(item.authors),
    year: asFiniteNumber(item.year),
    venue: asTrimmedString(item.venue),
    citationCount: asFiniteNumber(item.citationCount),
    provider: asTrimmedString(item.citationProvider),
    type: asTrimmedString(item.citationType),
  };

  for (const url of aliasUrls) {
    const key = normalizeCitationUrl(url);
    if (key && !registry.has(key)) {
      registry.set(key, metadata);
    }
  }
}

/**
 * Scan a thread's tool messages and build a url -> metadata registry.
 * Academic / web search results are parsed as JSON; `web_fetch` results carry
 * citation provenance in a Markdown header.
 */
export function buildCitationRegistry(
  messages: readonly ToolMessageLike[] | null | undefined,
): CitationRegistry {
  const registry: CitationRegistry = new Map();
  if (!messages) {
    return registry;
  }
  for (const message of messages) {
    if (message?.type !== "tool") {
      continue;
    }
    const text = toolMessageText(message.content);
    if (!text) {
      continue;
    }
    if (message.name === "web_fetch") {
      const fetched = extractFetchedCitation(text);
      const url = fetched.citationUrl;
      if (url) {
        const key = normalizeCitationUrl(url);
        if (key && !registry.has(key)) {
          registry.set(key, {
            url,
            title: fetched.citationTitle,
            type: "web_page",
            provider: extractHeaderValue(text, "citationProvider"),
          });
        }
      }
      continue;
    }
    let json: unknown;
    try {
      json = JSON.parse(text);
    } catch {
      continue;
    }
    for (const item of collectCitationItems(json)) {
      registerCitationItem(registry, item);
    }
  }
  return registry;
}

const MARKDOWN_LINK_RE =
  /(!?)\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+"[^"]*")?\s*\)/g;

/** Parse external Markdown links (skips images and non-http links). */
export function parseMarkdownLinks(content: string): MarkdownLink[] {
  const links: MarkdownLink[] = [];
  if (!content) {
    return links;
  }
  MARKDOWN_LINK_RE.lastIndex = 0;
  let match: RegExpExecArray | null;
  while ((match = MARKDOWN_LINK_RE.exec(content)) !== null) {
    if (match[1] === "!") {
      continue;
    }
    const text = match[2] ?? "";
    const href = match[3] ?? "";
    if (!/^https?:\/\//i.test(href)) {
      continue;
    }
    links.push({
      text,
      href,
      isCitationPrefixed: /^citation:/i.test(text.trim()),
    });
  }
  return links;
}

/**
 * Assign stable 1..N numbers to the citations in a block of Markdown.
 * A link is treated as a citation when it carries the `citation:` prefix or
 * its href is present in the registry. Numbers are local to the block and
 * de-duplicated by normalized href.
 */
export function buildCitationNumbering(
  content: string,
  registry?: CitationRegistry | null,
): CitationNumbering {
  const byHref = new Map<string, number>();
  const entries: CitationEntry[] = [];
  for (const link of parseMarkdownLinks(content)) {
    const key = normalizeCitationUrl(link.href);
    const isCitation =
      link.isCitationPrefixed || (registry?.has(key) ?? false);
    if (!isCitation || byHref.has(key)) {
      continue;
    }
    const number = entries.length + 1;
    byHref.set(key, number);
    entries.push({
      number,
      href: link.href,
      metadata: registry?.get(key) ?? null,
    });
  }
  return { byHref, entries };
}

/** Look up citation metadata for a link href, normalizing the key. */
export function lookupCitationMetadata(
  registry: CitationRegistry | null | undefined,
  href: string | null | undefined,
): CitationMetadata | null {
  if (!registry || !href) {
    return null;
  }
  return registry.get(normalizeCitationUrl(href)) ?? null;
}
