import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { dirname, extname, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import type { Message } from "@langchain/langgraph-sdk";

import type { AgentThread } from "../../../../src/core/threads/types";

type ResolveHookContext = {
  parentURL?: string;
};

type ResolveHookResult = {
  shortCircuit?: boolean;
  url: string;
};

const nodeModule = (await import("node:module")) as unknown as {
  registerHooks(hooks: {
    resolve(
      specifier: string,
      context: ResolveHookContext,
      nextResolve: (
        specifier: string,
        context: ResolveHookContext,
      ) => ResolveHookResult,
    ): ResolveHookResult;
  }): void;
};

nodeModule.registerHooks({
  resolve(specifier, context, nextResolve) {
    if (
      context.parentURL?.startsWith("file:") &&
      specifier.startsWith(".") &&
      !extname(specifier)
    ) {
      const parentDir = dirname(fileURLToPath(context.parentURL));
      for (const candidate of [
        resolve(parentDir, `${specifier}.ts`),
        resolve(parentDir, specifier, "index.ts"),
      ]) {
        if (existsSync(candidate)) {
          return {
            shortCircuit: true,
            url: pathToFileURL(candidate).href,
          };
        }
      }
    }
    return nextResolve(specifier, context);
  },
});

const { filenameForThreadExport, formatThreadAsHTML } = await import(
  new URL("../../../../src/core/threads/export.ts", import.meta.url).href
);

const thread = {
  thread_id: "thread-export-html",
  created_at: "2026-06-06T08:00:00.000Z",
  updated_at: "2026-06-06T08:00:00.000Z",
  metadata: {},
  status: "idle",
  interrupts: {},
  values: {
    title: "Readable HTML Export",
  },
} as AgentThread;

void test("renders thread title, metadata, roles, and html filename", () => {
  const html = formatThreadAsHTML(
    thread,
    [
      {
        id: "human-1",
        type: "human",
        content: "Hello",
      } as Message,
      {
        id: "ai-1",
        type: "ai",
        content: "Hi",
      } as Message,
    ],
    { userDisplayName: "张三 (@zhang_san)" },
  );

  assert.match(html, /<title>Readable HTML Export<\/title>/);
  assert.match(html, /Scientific Tumbleweed Export/);
  assert.match(html, /User: 张三 \(@zhang_san\)/);
  assert.match(html, /<span class="role">Human<\/span>/);
  assert.match(html, /<span class="role">Assistant<\/span>/);
  assert.match(html, /thread-export-html/);
  assert.equal(filenameForThreadExport(thread, "html"), "Readable HTML Export.html");
});

void test("renders markdown blocks as real html", () => {
  const html = formatThreadAsHTML(thread, [
    {
      id: "ai-1",
      type: "ai",
      content: [
        "## Section",
        "",
        "- First",
        "- Second",
        "",
        "| Name | Value |",
        "| --- | --- |",
        "| alpha | beta |",
        "",
        "```ts",
        "const value = 1;",
        "```",
        "",
        "$$x^2$$",
      ].join("\n"),
    } as Message,
  ]);

  assert.match(html, /<h2>Section<\/h2>/);
  assert.match(html, /<li>First<\/li>/);
  assert.match(html, /<table>/);
  assert.match(html, /<code class="language-ts">const value = 1;/);
  assert.match(html, /<math/);
});

void test("exports thinking and tool calls as closed details without tool results", () => {
  const html = formatThreadAsHTML(thread, [
    {
      id: "ai-1",
      type: "ai",
      content: "Final answer",
      additional_kwargs: {
        reasoning_content: "Private reasoning summary",
      },
      tool_calls: [
        {
          id: "call-1",
          name: "web_search",
          args: { query: "solid phase synthesis" },
        },
      ],
    } as Message,
    {
      id: "tool-1",
      type: "tool",
      tool_call_id: "call-1",
      content: "This tool result must not be exported",
    } as Message,
  ]);

  assert.match(html, /<details class="thinking">/);
  assert.doesNotMatch(html, /<details class="thinking" open>/);
  assert.match(html, /<summary>Thinking<\/summary>/);
  assert.match(html, /<details class="tool-call">/);
  assert.match(html, /web_search/);
  assert.match(html, /solid phase synthesis/);
  assert.doesNotMatch(html, /This tool result must not be exported/);
});

void test("exports upload, image, and artifact placeholders only", () => {
  const html = formatThreadAsHTML(thread, [
    {
      id: "human-1",
      type: "human",
      content: [
        "Please inspect this image.",
        "![gel](https://example.com/gel.png)",
        "<uploaded_files>",
        "- notes.pdf (123)",
        "  Path: /mnt/data/notes.pdf",
        "</uploaded_files>",
      ].join("\n"),
    } as Message,
    {
      id: "ai-1",
      type: "ai",
      content: "I created an artifact.",
      tool_calls: [
        {
          id: "call-1",
          name: "present_files",
          args: { filepaths: ["/mnt/data/primer-design-outline.md"] },
        },
      ],
    } as Message,
  ]);

  assert.match(html, /gel image placeholder/);
  assert.match(html, /notes\.pdf placeholder/);
  assert.match(html, /Artifact: primer-design-outline\.md/);
  assert.doesNotMatch(html, /https:\/\/example\.com\/gel\.png/);
  assert.doesNotMatch(html, /\/mnt\/data\/notes\.pdf/);
});

void test("sanitizes raw html and dangerous links", () => {
  const html = formatThreadAsHTML(thread, [
    {
      id: "human-1",
      type: "human",
      content:
        "[bad](javascript:alert(1)) <script>alert('x')</script><img src=x onerror=alert(1)>",
    } as Message,
  ]);

  assert.doesNotMatch(html, /<script/);
  assert.doesNotMatch(html, /onerror/);
  assert.doesNotMatch(html, /href="javascript:/);
});
