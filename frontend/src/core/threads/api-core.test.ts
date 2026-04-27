import assert from "node:assert/strict";
import test from "node:test";

const { createThreadWithDeps } = await import(
  new URL("./api-core.ts", import.meta.url).href
);

void test("creates a thread with the requested thread_id", async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];

  const result = await createThreadWithDeps(
    "788f569d-c917-4b8c-a8f7-bdc9b36f85d6",
    { agent_name: "demo" },
    {
      getBackendBaseURL: () => "http://localhost:2026",
      fetchWithAuth: async (url, init) => {
        calls.push({ url, init });
        return Response.json({
          thread_id: "788f569d-c917-4b8c-a8f7-bdc9b36f85d6",
          status: "idle",
          created_at: "1",
          updated_at: "1",
          metadata: { agent_name: "demo" },
          values: {},
          interrupts: {},
        });
      },
    },
  );

  assert.equal(result.thread_id, "788f569d-c917-4b8c-a8f7-bdc9b36f85d6");
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.url, "http://localhost:2026/api/threads");
  assert.equal(calls[0]?.init?.method, "POST");
  const body = calls[0]?.init?.body;
  assert.equal(typeof body, "string");
  assert.deepEqual(
    JSON.parse(body),
    {
      thread_id: "788f569d-c917-4b8c-a8f7-bdc9b36f85d6",
      metadata: { agent_name: "demo" },
    },
  );
});

void test("throws backend error detail when create thread fails", async () => {
  await assert.rejects(
    () =>
      createThreadWithDeps("thread-1", {}, {
        getBackendBaseURL: () => "",
        fetchWithAuth: async () =>
          Response.json(
            { detail: "Thread ownership conflict" },
            { status: 403 },
          ),
      }),
    /Thread ownership conflict/,
  );
});
