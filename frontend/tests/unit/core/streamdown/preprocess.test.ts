import assert from "node:assert/strict";
import test from "node:test";

const { capMarkdownNesting } = await import(
  new URL("../../../../src/core/streamdown/preprocess.ts", import.meta.url).href
);

void test("capMarkdownNesting limits blockquote depth", () => {
  const input = "> > > > too deep";

  assert.equal(capMarkdownNesting(input, 2), "> > too deep");
});

void test("capMarkdownNesting limits nested list indentation", () => {
  const input = "            - deeply nested";

  assert.equal(capMarkdownNesting(input, 3), "    - deeply nested");
});

void test("capMarkdownNesting preserves fenced code blocks", () => {
  const input = ["```md", "> > > keep me", "            - keep me too", "```"].join(
    "\n",
  );

  assert.equal(capMarkdownNesting(input, 2), input);
});
