import assert from "node:assert/strict";
import test from "node:test";

const { parseSubtaskResult } = await import(
  new URL("../../../../src/core/tasks/subtask-result.ts", import.meta.url).href
);

void test("parseSubtaskResult prefers structured completed status", () => {
  assert.deepEqual(
    parseSubtaskResult("legacy text", {
      status: "completed",
      result: "structured result",
    }),
    {
      status: "completed",
      result: "structured result",
    },
  );
});

void test("parseSubtaskResult maps structured timeout to failed UI status", () => {
  assert.deepEqual(
    parseSubtaskResult("legacy text", {
      status: "timed_out",
      error: "slow",
    }),
    {
      status: "failed",
      error: "slow",
    },
  );
});

void test("parseSubtaskResult falls back to legacy task prefixes", () => {
  assert.deepEqual(parseSubtaskResult("Task Succeeded. Result: done"), {
    status: "completed",
    result: "done",
  });
});
