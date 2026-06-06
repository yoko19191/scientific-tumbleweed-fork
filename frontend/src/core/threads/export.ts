import type { Message } from "@langchain/langgraph-sdk";
import rehypeKatex from "rehype-katex";
import rehypeSanitize, {
  defaultSchema,
  type Options as SanitizeSchema,
} from "rehype-sanitize";
import rehypeStringify from "rehype-stringify";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import { unified } from "unified";

import {
  extractContentFromMessage,
  extractPresentFilesFromMessage,
  extractReasoningContentFromMessage,
  isHiddenFromUIMessage,
  parseUploadedFiles,
  stripInternalMarkers,
} from "../messages/extraction";

import type { AgentThread } from "./types";
import { titleOfThread } from "./utils";

export interface ExportOptions {
  includeHidden?: boolean;
  includeReasoning?: boolean;
  includeToolCalls?: boolean;
  includeToolMessages?: boolean;
  userDisplayName?: string;
}

type ExportRole = "human" | "assistant";

interface HTMLToolCallView {
  name: string;
  argsJson: string;
}

interface HTMLMessageView {
  role: ExportRole;
  id?: string;
  timestamp?: string;
  contentHtml: string;
  reasoningHtml?: string;
  toolCalls: HTMLToolCallView[];
  placeholders: string[];
}

interface HTMLThreadView {
  title: string;
  threadId: string;
  createdAt: string;
  exportedAt: string;
  userDisplayName?: string;
  messages: HTMLMessageView[];
}

const MARKDOWN_IMAGE_RE = /!\[([^\]]*)\]\(([^)]+)\)/g;
const INTERNAL_TOOL_CALL_NAMES = new Set(["task", "present_files"]);

const mathSanitizeSchema: SanitizeSchema = {
  ...defaultSchema,
  tagNames: [
    ...(defaultSchema.tagNames ?? []),
    "annotation",
    "math",
    "menclose",
    "merror",
    "mfrac",
    "mi",
    "mmultiscripts",
    "mn",
    "mo",
    "mover",
    "mpadded",
    "mphantom",
    "mprescripts",
    "mroot",
    "mrow",
    "ms",
    "mspace",
    "msqrt",
    "mstyle",
    "msub",
    "msubsup",
    "msup",
    "mtable",
    "mtd",
    "mtext",
    "mtr",
    "munder",
    "munderover",
    "semantics",
  ],
  attributes: {
    ...defaultSchema.attributes,
    "*": [
      ...(defaultSchema.attributes?.["*"] ?? []),
      "aria-hidden",
      "className",
    ],
    annotation: ["encoding"],
    math: ["display", "xmlns"],
    mspace: ["height", "width"],
    mstyle: ["scriptlevel"],
    mtable: ["columnalign", "rowspacing"],
    mtd: ["columnalign"],
  },
};

const markdownProcessor = unified()
  .use(remarkParse)
  .use(remarkGfm)
  .use(remarkMath, { singleDollarTextMath: true })
  .use(remarkRehype, { allowDangerousHtml: false })
  .use(rehypeKatex, { output: "mathml" })
  .use(rehypeSanitize, mathSanitizeSchema)
  .use(rehypeStringify);

function escapeHTML(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value: string): string {
  return escapeHTML(value).replace(/`/g, "&#96;");
}

function renderMarkdown(markdown: string): string {
  if (!markdown.trim()) return "";
  return String(markdownProcessor.processSync(markdown));
}

function formatMessageContent(message: Message): string {
  const text = extractContentFromMessage(message);
  if (!text) return "";
  return stripInternalMarkers(text);
}

function extractMarkdownImagePlaceholders(markdown: string) {
  const placeholders: string[] = [];
  const cleaned = markdown
    .replace(MARKDOWN_IMAGE_RE, (_match, alt: string) => {
      placeholders.push(
        alt.trim() ? `${alt.trim()} image placeholder` : "Image placeholder",
      );
      return "";
    })
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  return { cleaned, placeholders };
}

function filenameFromPath(path: string): string {
  return path.split(/[\\/]/).filter(Boolean).at(-1) ?? path;
}

function getUploadedFilePlaceholders(message: Message, rawContent: string) {
  const files = message.additional_kwargs?.files;
  const parsedFiles =
    Array.isArray(files) && files.length > 0
      ? files
      : parseUploadedFiles(rawContent);

  return parsedFiles.flatMap((file) => {
    if (!file || typeof file !== "object") return [];
    const candidate =
      "filename" in file && typeof file.filename === "string"
        ? file.filename
        : "path" in file && typeof file.path === "string"
          ? filenameFromPath(file.path)
          : "";
    return candidate ? [`${candidate} placeholder`] : [];
  });
}

function getArtifactPlaceholders(message: Message) {
  return extractPresentFilesFromMessage(message).map(
    (path) => `Artifact: ${filenameFromPath(path)}`,
  );
}

function getMessageTimestamp(message: Message): string | undefined {
  const candidates = [
    (message as { created_at?: unknown }).created_at,
    (message as { timestamp?: unknown }).timestamp,
    message.additional_kwargs?.created_at,
    message.additional_kwargs?.timestamp,
    (message.response_metadata as { created_at?: unknown } | undefined)
      ?.created_at,
    (message.response_metadata as { timestamp?: unknown } | undefined)
      ?.timestamp,
  ];

  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate;
    }
  }
  return undefined;
}

function normalizeOptionalText(value: string | undefined): string | undefined {
  const normalized = value?.trim();
  return normalized && normalized.length > 0 ? normalized : undefined;
}

function normalizeToolCalls(message: Message): HTMLToolCallView[] {
  if (message.type !== "ai") return [];
  return (message.tool_calls ?? []).flatMap((call) => {
    if (INTERNAL_TOOL_CALL_NAMES.has(call.name)) return [];
    return [
      {
        name: call.name,
        argsJson: JSON.stringify(call.args ?? {}, null, 2),
      },
    ];
  });
}

function normalizeMessagesForHTML(
  messages: Message[],
  options: ExportOptions = {},
): HTMLMessageView[] {
  return messages.flatMap((message) => {
    if (!options.includeHidden && isHiddenFromUIMessage(message)) return [];
    if (message.type === "tool") return [];
    if (message.type !== "human" && message.type !== "ai") return [];

    const role: ExportRole = message.type === "human" ? "human" : "assistant";
    const rawContent = extractContentFromMessage(message);
    const content = formatMessageContent(message);
    const uploadedPlaceholders = getUploadedFilePlaceholders(message, rawContent);
    const artifactPlaceholders =
      message.type === "ai" ? getArtifactPlaceholders(message) : [];
    const { cleaned, placeholders: imagePlaceholders } =
      extractMarkdownImagePlaceholders(content);
    const reasoning =
      message.type === "ai" && options.includeReasoning !== false
        ? extractReasoningContentFromMessage(message)
        : "";
    const toolCalls =
      message.type === "ai" && options.includeToolCalls !== false
        ? normalizeToolCalls(message)
        : [];
    const placeholders = [
      ...uploadedPlaceholders,
      ...imagePlaceholders,
      ...artifactPlaceholders,
    ];

    if (
      !cleaned &&
      !reasoning &&
      toolCalls.length === 0 &&
      placeholders.length === 0
    ) {
      return [];
    }

    return [
      {
        role,
        id: message.id,
        timestamp: getMessageTimestamp(message),
        contentHtml: renderMarkdown(cleaned),
        reasoningHtml: reasoning ? renderMarkdown(reasoning) : undefined,
        toolCalls,
        placeholders,
      },
    ];
  });
}

function normalizeThreadForHTML(
  thread: AgentThread,
  messages: Message[],
  options: ExportOptions = {},
): HTMLThreadView {
  return {
    title: titleOfThread(thread),
    threadId: thread.thread_id,
    createdAt: thread.created_at
      ? new Date(thread.created_at).toLocaleString()
      : "Unknown",
    exportedAt: new Date().toLocaleString(),
    userDisplayName: normalizeOptionalText(options.userDisplayName),
    messages: normalizeMessagesForHTML(messages, options),
  };
}

function renderPlaceholderChips(placeholders: string[]) {
  if (placeholders.length === 0) return "";
  return `
              <div class="placeholder-list">
${placeholders
  .map(
    (placeholder) =>
      `                <span class="placeholder">${escapeHTML(placeholder)}</span>`,
  )
  .join("\n")}
              </div>`;
}

function renderToolCalls(toolCalls: HTMLToolCallView[]) {
  return toolCalls
    .map(
      (toolCall) => `
              <details class="tool-call">
                <summary>
                  <span>Tool Call: <span class="tool-name">${escapeHTML(
                    toolCall.name,
                  )}</span></span>
                </summary>
                <div class="details-body">
                  <pre><code>${escapeHTML(toolCall.argsJson)}</code></pre>
                  <p>Tool result omitted in export.</p>
                </div>
              </details>`,
    )
    .join("\n");
}

function renderMessage(message: HTMLMessageView) {
  const roleLabel = message.role === "human" ? "Human" : "Assistant";
  const avatarLabel = message.role === "human" ? "YOU" : "AI";
  const timestamp = message.timestamp
    ? `<span>${escapeHTML(message.timestamp)}</span>`
    : "";
  const id = message.id
    ? `<span class="message-id">${escapeHTML(message.id)}</span>`
    : "";
  const reasoning = message.reasoningHtml
    ? `
              <details class="thinking">
                <summary>Thinking</summary>
                <div class="details-body">${message.reasoningHtml}</div>
              </details>`
    : "";
  const toolCalls = renderToolCalls(message.toolCalls);
  const placeholders = renderPlaceholderChips(message.placeholders);

  if (message.role === "human") {
    return `
          <article class="message human">
            <div class="bubble">
              <div class="message-meta">
                <span class="role">${roleLabel}</span>
                ${timestamp}
                ${id}
              </div>
              <div class="message-content">${message.contentHtml}</div>
              ${placeholders}
            </div>
            <div class="avatar">${avatarLabel}</div>
          </article>`;
  }

  return `
          <article class="message assistant">
            <div class="avatar">${avatarLabel}</div>
            <div class="bubble">
              <div class="message-meta">
                <span class="role">${roleLabel}</span>
                ${timestamp}
                ${id}
              </div>
              ${reasoning}
              ${toolCalls}
              <div class="message-content">${message.contentHtml}</div>
              ${placeholders}
            </div>
          </article>`;
}

const EXPORT_HTML_CSS = `
      :root {
        color-scheme: light;
        --page: #f8f8f7;
        --surface: #ffffff;
        --surface-soft: #f2f5f4;
        --ink: #202423;
        --ink-muted: #68716f;
        --line: #dde4e0;
        --assistant: #ffffff;
        --human: #e8f4ff;
        --human-line: #b7d8f4;
        --accent: #127c74;
        --tool: #f3eefb;
        --tool-line: #d9c8f0;
        --code: #101414;
        --code-ink: #edf7f4;
        --shadow: 0 16px 40px rgb(27 38 35 / 10%);
        --radius-lg: 22px;
        --radius-md: 14px;
        --radius-sm: 8px;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        background: var(--page);
        color: var(--ink);
        font-family:
          ui-sans-serif,
          "Avenir Next",
          "Segoe UI",
          "PingFang SC",
          "Hiragino Sans GB",
          sans-serif;
        font-size: 16px;
        line-height: 1.65;
      }

      .page {
        min-height: 100vh;
        padding: 42px 24px 72px;
      }

      .export-shell {
        width: min(1120px, 100%);
        margin: 0 auto;
      }

      .document-header {
        position: sticky;
        top: 0;
        z-index: 10;
        margin: -42px -24px 34px;
        padding: 28px 24px 18px;
        background: color-mix(in srgb, var(--page) 88%, transparent);
        border-bottom: 1px solid color-mix(in srgb, var(--line) 75%, transparent);
        backdrop-filter: blur(18px);
      }

      .header-inner {
        width: min(1120px, 100%);
        margin: 0 auto;
      }

      .eyebrow {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
        color: var(--ink-muted);
        font-size: 13px;
      }

      .badge {
        display: inline-flex;
        align-items: center;
        border: 1px solid var(--line);
        border-radius: 999px;
        padding: 3px 10px;
        background: var(--surface);
      }

      h1 {
        max-width: 860px;
        margin: 0;
        font-family:
          ui-serif,
          "Iowan Old Style",
          "Songti SC",
          Georgia,
          serif;
        font-size: clamp(30px, 5vw, 52px);
        font-weight: 700;
        line-height: 1.08;
        letter-spacing: 0;
      }

      .summary {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 22px 0 34px;
      }

      .summary-item {
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        padding: 14px 16px;
        background: var(--surface);
      }

      .summary-item span {
        display: block;
        color: var(--ink-muted);
        font-size: 12px;
      }

      .summary-item strong {
        display: block;
        margin-top: 2px;
        font-size: 15px;
      }

      .transcript {
        display: flex;
        flex-direction: column;
        gap: 22px;
      }

      .message {
        display: grid;
        grid-template-columns: 44px minmax(0, 760px) 44px;
        justify-content: start;
        gap: 14px;
      }

      .message.human {
        justify-content: end;
      }

      .avatar {
        display: grid;
        grid-row: 1;
        width: 40px;
        height: 40px;
        place-items: center;
        border: 1px solid var(--line);
        border-radius: 50%;
        background: var(--surface);
        color: var(--ink-muted);
        font-size: 12px;
        font-weight: 700;
      }

      .human .avatar {
        grid-column: 3;
        border-color: var(--human-line);
        background: var(--human);
        color: #24506b;
      }

      .bubble {
        grid-column: 2;
        grid-row: 1;
        border: 1px solid var(--line);
        border-radius: var(--radius-lg);
        padding: 22px 24px;
        background: var(--assistant);
        box-shadow: var(--shadow);
      }

      .human .bubble {
        border-color: var(--human-line);
        background: var(--human);
      }

      .message-meta {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 8px 12px;
        margin-bottom: 12px;
        color: var(--ink-muted);
        font-size: 12px;
      }

      .role {
        color: var(--ink);
        font-weight: 700;
      }

      .message-id {
        max-width: 240px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .message-content:empty {
        display: none;
      }

      .bubble h2,
      .bubble h3 {
        margin: 18px 0 8px;
        line-height: 1.28;
        letter-spacing: 0;
      }

      .bubble h2:first-child,
      .bubble h3:first-child,
      .message-content > :first-child {
        margin-top: 0;
      }

      .message-content > :last-child {
        margin-bottom: 0;
      }

      .bubble p {
        margin: 10px 0;
      }

      .bubble ul,
      .bubble ol {
        margin: 10px 0 14px;
        padding-left: 1.35rem;
      }

      .bubble li + li {
        margin-top: 4px;
      }

      .bubble a {
        color: var(--accent);
        text-underline-offset: 3px;
      }

      .bubble blockquote {
        margin: 14px 0;
        border-left: 3px solid var(--accent);
        padding: 4px 0 4px 14px;
        color: var(--ink-muted);
        background: var(--surface-soft);
        border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
      }

      pre {
        overflow-x: auto;
        margin: 14px 0;
        border-radius: var(--radius-md);
        padding: 16px;
        background: var(--code);
        color: var(--code-ink);
        font-size: 13px;
        line-height: 1.55;
      }

      code {
        font-family:
          "SFMono-Regular",
          "Cascadia Code",
          "Liberation Mono",
          monospace;
      }

      p code,
      li code {
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 1px 5px;
        background: var(--surface-soft);
        color: #31524e;
        font-size: 0.92em;
      }

      table {
        display: block;
        width: 100%;
        overflow-x: auto;
        margin: 14px 0;
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        border-spacing: 0;
        background: var(--surface);
        font-size: 14px;
      }

      th,
      td {
        border-bottom: 1px solid var(--line);
        padding: 10px 12px;
        text-align: left;
        vertical-align: top;
      }

      th {
        background: var(--surface-soft);
        font-size: 12px;
        letter-spacing: 0.02em;
        text-transform: uppercase;
      }

      tr:last-child td {
        border-bottom: 0;
      }

      .katex {
        display: inline-block;
        max-width: 100%;
        overflow-x: auto;
        font-family:
          "STIX Two Math",
          "Cambria Math",
          Georgia,
          serif;
      }

      .math-display {
        display: block;
        margin: 14px 0;
        border: 1px solid var(--line);
        border-radius: var(--radius-md);
        padding: 14px 16px;
        background: #fbfbfd;
        text-align: center;
      }

      details {
        margin: 12px 0;
        border-radius: var(--radius-md);
      }

      summary {
        cursor: pointer;
        user-select: none;
      }

      .thinking,
      .tool-call {
        border: 1px solid var(--line);
        background: var(--surface-soft);
      }

      .thinking summary,
      .tool-call summary {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 12px 14px;
        color: var(--ink);
        font-weight: 700;
      }

      .thinking summary::after,
      .tool-call summary::after {
        content: "展开";
        color: var(--ink-muted);
        font-size: 12px;
        font-weight: 500;
      }

      .thinking[open] summary::after,
      .tool-call[open] summary::after {
        content: "收起";
      }

      .details-body {
        border-top: 1px solid var(--line);
        padding: 12px 14px 14px;
        color: var(--ink-muted);
        font-size: 14px;
      }

      .tool-call {
        border-color: var(--tool-line);
        background: var(--tool);
      }

      .tool-name {
        color: #5d3c86;
      }

      .placeholder-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 14px;
      }

      .placeholder {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        border: 1px dashed var(--line);
        border-radius: 999px;
        padding: 6px 10px;
        background: color-mix(in srgb, var(--surface) 70%, transparent);
        color: var(--ink-muted);
        font-size: 13px;
      }

      .placeholder::before {
        content: "";
        display: block;
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--accent);
      }

      .export-footer {
        margin-top: 42px;
        color: var(--ink-muted);
        font-size: 12px;
        text-align: center;
      }

      @media (max-width: 760px) {
        .page {
          padding: 28px 12px 48px;
        }

        .document-header {
          margin: -28px -12px 24px;
          padding: 22px 12px 16px;
        }

        .summary {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .message {
          grid-template-columns: 34px minmax(0, 1fr);
          gap: 10px;
        }

        .human .avatar {
          grid-column: 1;
        }

        .human .bubble,
        .bubble {
          grid-column: 2;
        }

        .avatar {
          width: 32px;
          height: 32px;
        }

        .bubble {
          padding: 18px 16px;
          border-radius: 18px;
        }
      }`;

function renderThreadHTML(view: HTMLThreadView) {
  const toolCallCount = view.messages.reduce(
    (count, message) => count + message.toolCalls.length,
    0,
  );
  const placeholderCount = view.messages.reduce(
    (count, message) => count + message.placeholders.length,
    0,
  );
  const messagesHTML = view.messages.map(renderMessage).join("\n");

  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>${escapeHTML(view.title)}</title>
    <style>${EXPORT_HTML_CSS}
    </style>
  </head>
  <body>
    <main class="page">
      <header class="document-header">
        <div class="header-inner">
          <div class="eyebrow">
            <span class="badge">Scientific Tumbleweed Export</span>
            <span class="badge">HTML</span>
            ${
              view.userDisplayName
                ? `<span class="badge">User: ${escapeHTML(
                    view.userDisplayName,
                  )}</span>`
                : ""
            }
            <span class="badge">${escapeHTML(view.exportedAt)}</span>
          </div>
          <h1>${escapeHTML(view.title)}</h1>
        </div>
      </header>

      <div class="export-shell">
        <section class="summary" aria-label="Export summary">
          <div class="summary-item">
            <span>Messages</span>
            <strong>${view.messages.length}</strong>
          </div>
          <div class="summary-item">
            <span>Tool Calls</span>
            <strong>${toolCallCount} folded</strong>
          </div>
          <div class="summary-item">
            <span>Placeholders</span>
            <strong>${placeholderCount}</strong>
          </div>
          <div class="summary-item">
            <span>Thread ID</span>
            <strong title="${escapeAttribute(view.threadId)}">${escapeHTML(
              view.threadId,
            )}</strong>
          </div>
        </section>

        <section class="transcript" aria-label="Conversation transcript">
${messagesHTML}
        </section>

        <footer class="export-footer">
          Exported as a single readable HTML file. Tool results and artifact bodies are intentionally omitted.
        </footer>
      </div>
    </main>
  </body>
</html>
`;
}

export function formatThreadAsHTML(
  thread: AgentThread,
  messages: Message[],
  options: ExportOptions = {},
): string {
  return renderThreadHTML(normalizeThreadForHTML(thread, messages, options));
}

export function formatThreadAsJSON(
  thread: AgentThread,
  messages: Message[],
  options: ExportOptions = {},
): string {
  const exportedMessages = messages.flatMap((msg) => {
    if (!options.includeHidden && isHiddenFromUIMessage(msg)) return [];
    if (msg.type === "tool" && !options.includeToolMessages) return [];

    const content = formatMessageContent(msg);
    const reasoning =
      msg.type === "ai" && options.includeReasoning
        ? extractReasoningContentFromMessage(msg)
        : "";
    const toolCalls =
      msg.type === "ai" && options.includeToolCalls && msg.tool_calls?.length
        ? msg.tool_calls
        : undefined;

    if (!content && !reasoning && !toolCalls) return [];

    return [
      {
        type: msg.type,
        id: msg.id,
        content,
        ...(reasoning ? { reasoning } : {}),
        ...(toolCalls ? { tool_calls: toolCalls } : {}),
      },
    ];
  });

  const exportData = {
    title: titleOfThread(thread),
    thread_id: thread.thread_id,
    created_at: thread.created_at,
    exported_at: new Date().toISOString(),
    messages: exportedMessages,
  };
  return JSON.stringify(exportData, null, 2);
}

function sanitizeFilename(name: string): string {
  return name.replace(/[^\p{L}\p{N}_\- ]/gu, "").trim() || "conversation";
}

export function filenameForThreadExport(
  thread: AgentThread,
  extension: "html" | "json",
) {
  return `${sanitizeFilename(titleOfThread(thread))}.${extension}`;
}

export function downloadAsFile(
  content: string,
  filename: string,
  mimeType: string,
) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportThreadAsHTML(
  thread: AgentThread,
  messages: Message[],
  options: ExportOptions = {},
) {
  const html = formatThreadAsHTML(thread, messages, options);
  const filename = filenameForThreadExport(thread, "html");
  downloadAsFile(html, filename, "text/html;charset=utf-8");
}

export function exportThreadAsJSON(thread: AgentThread, messages: Message[]) {
  const json = formatThreadAsJSON(thread, messages);
  const filename = filenameForThreadExport(thread, "json");
  downloadAsFile(json, filename, "application/json;charset=utf-8");
}
