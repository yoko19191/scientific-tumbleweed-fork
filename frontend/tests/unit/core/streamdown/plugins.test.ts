import assert from "node:assert/strict";
import test from "node:test";

import rehypeRaw from "rehype-raw";

import { reasoningPlugins, streamdownPlugins } from "@/core/streamdown/plugins";

void test("streamdownPlugins includes rehypeRaw", () => {
  assert.ok(streamdownPlugins.rehypePlugins?.includes(rehypeRaw));
});

void test("reasoningPlugins does not include rehypeRaw", () => {
  const flat = reasoningPlugins.rehypePlugins?.flat();
  assert.equal(flat?.includes(rehypeRaw), false);
});
