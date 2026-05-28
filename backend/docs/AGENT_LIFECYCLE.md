# Agent Lifecycle

本文定义 Scientific Tumbleweed 后端中一次 Agent 运行的语义边界。目标不是重复所有实现细节，而是说明一个请求从 Gateway 进入，到 Agent 构建、执行、流式输出、持久化和最终状态读取的稳定生命周期。

## Scope

本文覆盖 Gateway mode 下的 Agent 生命周期：

- 前端或 IM channel 通过 Gateway 发起 runs 请求。
- Gateway 创建 `RunRecord` 并启动后台 worker。
- Harness 构建 LangGraph agent、安装 runtime context、执行 middleware chain。
- Worker 发布 stream events、更新 run status、写入 checkpoint 和 run metadata。
- Gateway 读取 final state 或持续输出 SSE。

本文不改变 HTTP 协议、SSE wire protocol、LangGraph checkpoint backend、OpenDAL key 布局或前端调用方式。

## High-Level Lifecycle

```text
Client / Channel
  -> Gateway route
  -> authenticated thread resource
  -> start_run()
  -> RunManager.create_or_reject()
  -> run_agent() background task
  -> RuntimeContext installation
  -> make_lead_agent() / create_deerflow_agent()
  -> canonical middleware chain
  -> LangGraph execution
  -> StreamBridge events + checkpoint writes + RunStore updates
  -> wait final state / SSE stream / join stream / cancel
```

## Semantic Layers

### 1. Client Boundary

The external API shape is stable:

- Thread-scoped runs use `/api/threads/{thread_id}/runs/*`.
- Stateless runs use `/api/runs/*`.
- Stream responses use LangGraph-compatible SSE frames with `event`, `data`, optional `id`, and a blank line.
- Request config may use either LangGraph `context` mode or legacy `configurable` mode.

Frontend code does not need to know whether the backend is using local runtime helpers, a checkpointer adapter, or a specific run store implementation.

### 2. Thread Resource Boundary

Thread-scoped routes must resolve an authenticated thread resource before touching any thread-local file or namespace.

Primary interface:

- `app.gateway.thread_resources.get_authenticated_thread_resource()`

This boundary owns:

- thread ownership verification
- user-scoped namespace selection
- user-prefixed thread directory resolution
- virtual `/mnt/user-data/...` path translation for Gateway file access

Routes should not hand-build user namespaces or resolve thread paths directly when this interface applies.

### 3. Run Launch Boundary

Gateway run launch is centralized in:

- `app.gateway.services.start_run()`

This function owns:

- resolving authenticated `user_id`
- validating requested model name
- creating or rejecting the run through `RunManager`
- building LangGraph config through `build_run_config()`
- merging request body `context` through `apply_runtime_context_overrides()`
- normalizing input messages
- creating the `run_agent()` background task
- ensuring stateless threads appear in thread search
- scheduling title sync after run completion

Routers should not duplicate config merge, custom-agent injection, model validation, or run creation logic.

### 4. Runtime Context Boundary

Harness runtime context is represented by:

- `deerflow.runtime.RuntimeContext`
- `deerflow.runtime.install_runtime_context()`

The canonical fields are:

- `thread_id`
- `run_id`
- `user_id`
- `agent_name`
- `app_config`

These fields are resolved by the worker and installed into LangGraph `Runtime.context`. Middleware, tools, and agent factories should read these values from runtime context instead of re-parsing HTTP request bodies or Gateway-specific objects.

### 5. Agent Construction Boundary

The lead agent and SDK-created agents share the same middleware ordering module:

- `deerflow.agents.middleware_builder.build_ordered_middleware_chain()`
- `deerflow.agents.middleware_builder.build_canonical_middleware_chain()`
- `deerflow.agents.middleware_builder.insert_extra_middlewares()`

`make_lead_agent()` may decide which concrete middleware slots are enabled for Gateway execution. `create_deerflow_agent()` may expose SDK-level customization. Both must delegate final relative ordering to the canonical builder.

Key ordering invariants:

- `ClarificationMiddleware` is always last.
- subagent limit, loop detection, safety finish handling, and clarification ordering is test-locked.
- `extra_middleware` insertion goes through the shared insertion helper.

### 6. Execution Boundary

The background worker is:

- `deerflow.runtime.runs.worker.run_agent()`

It owns:

- setting run status transitions
- attaching checkpointer and store to the agent
- capturing pre-run checkpoint snapshots for rollback
- installing `RuntimeContext`
- streaming LangGraph events through `StreamBridge`
- persisting token usage and completion summaries
- publishing terminal stream events
- applying cancel/rollback behavior

The worker is the only layer that should combine run status, graph execution, checkpoint rollback, and stream publication.

### 7. Stream Boundary

Producer/consumer stream decoupling is owned by:

- `deerflow.runtime.stream_bridge.StreamBridge`
- `deerflow.runtime.stream_bridge.MemoryStreamBridge`
- `deerflow.runtime.format_sse_frame()`

The stream bridge owns event retention and `Last-Event-ID` replay semantics. Gateway services own only HTTP consumption:

- `app.gateway.services.sse_consumer()`
- `app.gateway.services.format_sse()` as a compatibility wrapper

SSE frame shape remains:

```text
event: <event-name>
data: <json-payload>
id: <optional-event-id>

```

### 8. Persistence Boundary

Run metadata and LangGraph state are separate:

- `RunStore` stores run metadata, status, token usage, and ownership metadata.
- LangGraph checkpointer stores graph state and channel values.
- LangGraph Store stores app-visible thread records and other runtime records.
- OpenDAL stores object-like persistent files such as custom agents, user profiles, and per-user extension overrides.

RunStore hydration is mapped through:

- `RunRecord.from_store_row()`

Checkpoint-backed final state reads go through:

- `deerflow.runtime.runs.checkpoints.thread_checkpoint_config()`
- `deerflow.runtime.runs.checkpoints.read_thread_checkpoint_values()`
- `deerflow.runtime.runs.checkpoints.read_thread_final_state()`

Routers should not hand-read checkpoint tuples for final wait responses.

## Run State Model

`RunRecord.status` is the lifecycle state visible to Gateway run APIs.

```text
pending
  -> running
  -> success
  -> error
  -> interrupted
```

State meanings:

- `pending`: the run was accepted and recorded but graph execution has not started.
- `running`: the worker is executing the graph.
- `success`: graph execution completed normally.
- `error`: graph execution failed and the failure was captured.
- `interrupted`: the run was cancelled or superseded by an interrupt/rollback strategy.

Historical records loaded from `RunStore` are marked `store_only=True`; they can be listed and inspected but cannot be cancelled on the current worker.

## Request Lifecycle

### Create Run

```text
POST /api/threads/{thread_id}/runs
  -> require_thread_owner()
  -> start_run()
  -> RunManager.create_or_reject()
  -> asyncio.create_task(run_agent(...))
  -> RunResponse
```

The response returns immediately after the background task is scheduled.

### Stream Run

```text
POST /api/threads/{thread_id}/runs/stream
  -> require_thread_owner()
  -> start_run()
  -> sse_consumer(StreamBridge.subscribe(...))
  -> text/event-stream
```

If the client disconnects and `on_disconnect="cancel"`, the consumer asks `RunManager` to cancel the run. If `on_disconnect="continue"`, the background run continues and events are discarded for that disconnected client.

### Wait Run

```text
POST /api/threads/{thread_id}/runs/wait
  -> require_thread_owner()
  -> start_run()
  -> await record.task
  -> read_thread_final_state(checkpointer, thread_id)
  -> serialized channel values
```

Final state is read from the root checkpoint namespace and serialized through the runtime serializer. Internal LangGraph keys such as `__pregel_*` and `__interrupt__` are stripped.

### Join Existing Run

```text
GET /api/threads/{thread_id}/runs/{run_id}/join
  -> require_thread_owner()
  -> RunManager.get()
  -> sse_consumer(StreamBridge.subscribe(...))
```

The stream bridge uses retained events plus `Last-Event-ID` to replay events when possible.

### Cancel Run

```text
POST /api/threads/{thread_id}/runs/{run_id}/cancel
  -> require_thread_owner()
  -> RunManager.get()
  -> RunManager.cancel(action="interrupt" | "rollback")
```

`interrupt` keeps the current checkpoint state. `rollback` restores the pre-run checkpoint snapshot when one was captured.

## Middleware Lifecycle

Middleware is selected at agent construction time and executed by LangGraph during the run.

Conceptual order:

```text
thread data
uploads
sandbox
dangling tool call repair
LLM/provider error handling
guardrails / sandbox audit / permission / hooks
dynamic context
summarization / compaction / todo list
token usage
title generation
memory queueing
vision image injection
deferred tool filtering
subagent limit
loop detection
safety finish handling
clarification
```

The exact enabled set depends on app config, runtime context, model capabilities, and request mode. The ordering contract belongs to `middleware_builder.py`, not to individual routers or tools.

## Custom Agent Lifecycle

Custom agents are storage-backed configuration overlays for the lead-agent runtime.

Primary interface:

- `deerflow.config.agents_config.CustomAgentStore`
- `deerflow.config.agents_config.normalize_agent_name()`

The lifecycle is:

```text
create custom agent
  -> normalize name
  -> write config.yaml + SOUL.md
  -> assistant_id selects agent_name during run config build
  -> RuntimeContext exposes agent_name
  -> make_lead_agent() loads matching custom config and soul
```

Gateway routes and built-in setup/update tools share the same store interface.

## Skills and MCP Lifecycle

Global extension definitions remain developer-level config. Per-user enablement lives in object storage.

Primary interface:

- `get_effective_extensions_config(user_id=None)`
- `aget_effective_extensions_config(user_id=None)`
- `aset_user_skill_enabled(user_id, skill_name, enabled)`
- `aset_user_mcp_server_enabled(user_id, server_name, enabled)`

The effective config lifecycle is:

```text
global extensions_config.json
  + user-extensions/{user_id}/extensions_config.json
  -> effective config
  -> skills loader / MCP router / tool assembly
```

Skills and MCP should not implement separate user override merge rules.

## Failure Semantics

### Run Creation Conflict

`RunManager.create_or_reject()` applies the requested multitask strategy:

- `reject`: fail if the thread already has an inflight run.
- `interrupt`: interrupt inflight runs before creating the new run.
- `rollback`: interrupt inflight runs and request checkpoint rollback.

### Worker Error

Worker failures become `RunStatus.error`, emit an error stream event where possible, and persist the error message to the run store.

### Checkpoint Read Failure

Wait endpoints log final-state read failures and fall back to:

```json
{"status": "<run-status>", "error": "<error-or-null>"}
```

### Stream Disconnect

Disconnect behavior is controlled by `on_disconnect`:

- `cancel`: cancel pending/running work.
- `continue`: leave the background task running.

## Ownership and Isolation Rules

- Thread-scoped HTTP routes must verify thread ownership before resource access.
- User-specific thread files live under user-prefixed directories.
- Run metadata stores `user_id` when authentication is available.
- Store lookups that support `user_id` must filter by it.
- Harness code must not import `app.*`.

## Stable Contracts

The current stable contracts are:

- HTTP request/response schema stays Gateway-owned.
- Runtime context fields are resolved once by the harness worker.
- Middleware ordering is centralized in the canonical builder.
- Final state reads go through the checkpoint adapter.
- SSE formatting goes through the runtime stream helper.
- RunStore rows hydrate through `RunRecord.from_store_row()`.
- Skills/MCP effective config has one merge path.
- Custom agent storage has one lifecycle interface.

These contracts are the reference points for future backend changes. If a new feature needs to bypass one of them, it should first define the new seam explicitly and add a focused regression test.
