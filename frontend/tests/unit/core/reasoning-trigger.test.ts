import assert from "node:assert/strict";
import test from "node:test";

import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";

void test("ReasoningTrigger default message uses phrasing content", () => {
  const html = renderToStaticMarkup(
    createElement(
      Reasoning,
      { isStreaming: false, defaultOpen: false },
      createElement(ReasoningTrigger, null),
      createElement(ReasoningContent, null, "test"),
    ),
  );

  assert.match(html, /Thought for a few seconds/);
  assert.doesNotMatch(html, /<button\b[^>]*>[\s\S]*?<p\b/i);
});
