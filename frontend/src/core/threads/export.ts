import type { Message } from "@langchain/langgraph-sdk";

import {
  extractContentFromMessage,
  extractReasoningContentFromMessage,
  hasContent,
  hasToolCalls,
  isHiddenFromUIMessage,
  stripInternalMarkers,
} from "../messages/utils";

import type { AgentThread } from "./types";
import { titleOfThread } from "./utils";

export interface ExportOptions {
  includeHidden?: boolean;
  includeReasoning?: boolean;
  includeToolCalls?: boolean;
  includeToolMessages?: boolean;
}

function formatMessageContent(message: Message): string {
  const text = extractContentFromMessage(message);
  if (!text) return "";
  return stripInternalMarkers(text);
}

function formatToolCalls(message: Message): string {
  if (message.type !== "ai" || !hasToolCalls(message)) return "";
  const calls = message.tool_calls ?? [];
  return calls.map((call) => `- **Tool:** \`${call.name}\``).join("\n");
}

export function formatThreadAsMarkdown(
  thread: AgentThread,
  messages: Message[],
  options: ExportOptions = {},
): string {
  const title = titleOfThread(thread);
  const createdAt = thread.created_at
    ? new Date(thread.created_at).toLocaleString()
    : "Unknown";

  const lines: string[] = [
    `# ${title}`,
    "",
    `*Exported on ${new Date().toLocaleString()} · Created ${createdAt}*`,
    "",
    "---",
    "",
  ];

  for (const message of messages) {
    if (!options.includeHidden && isHiddenFromUIMessage(message)) continue;
    if (message.type === "tool" && !options.includeToolMessages) continue;

    if (message.type === "human") {
      const content = formatMessageContent(message);
      if (content) {
        lines.push(`## 🧑 User`, "", content, "", "---", "");
      }
    } else if (message.type === "ai") {
      const reasoning = options.includeReasoning
        ? extractReasoningContentFromMessage(message)
        : "";
      const content = formatMessageContent(message);
      const toolCalls = options.includeToolCalls ? formatToolCalls(message) : "";

      if (!content && !toolCalls && !reasoning) continue;

      lines.push(`## 🤖 Assistant`);

      if (reasoning) {
        lines.push(
          "",
          "<details>",
          "<summary>Thinking</summary>",
          "",
          reasoning,
          "",
          "</details>",
        );
      }

      if (toolCalls) {
        lines.push("", toolCalls);
      }

      if (content && hasContent(message)) {
        lines.push("", content);
      }

      lines.push("", "---", "");
    }
  }

  return lines.join("\n").trimEnd() + "\n";
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

export function exportThreadAsMarkdown(
  thread: AgentThread,
  messages: Message[],
) {
  const markdown = formatThreadAsMarkdown(thread, messages);
  const filename = `${sanitizeFilename(titleOfThread(thread))}.md`;
  downloadAsFile(markdown, filename, "text/markdown;charset=utf-8");
}

export function exportThreadAsJSON(thread: AgentThread, messages: Message[]) {
  const json = formatThreadAsJSON(thread, messages);
  const filename = `${sanitizeFilename(titleOfThread(thread))}.json`;
  downloadAsFile(json, filename, "application/json;charset=utf-8");
}
