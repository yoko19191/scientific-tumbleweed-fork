# Phase 2 - Runtime Context and Run Launch

## Scope

This phase centralizes Gateway run context merging and harness runtime context
installation.

Covered modules:

- `app.gateway.services`
- `packages/harness/deerflow/runtime/context.py`
- `packages/harness/deerflow/runtime/runs/worker.py`

## Constraints

- External LangGraph-compatible request and SSE shapes stay unchanged.
- `config.context` mode remains compatible with LangGraph >= 0.6.
- `config.configurable` remains supported for backward-compatible callers.
- Request body `context.thread_id` and `context.run_id` are never trusted as
  canonical run identity.

## Interface

Gateway run launch uses:

- `build_run_config(thread_id, request_config, metadata, assistant_id=...)`
- `apply_runtime_context_overrides(config, body.context)`
- `start_run(body, thread_id, request)`

Harness runtime execution uses:

- `RuntimeContext.from_config(thread_id=..., run_id=..., config=..., app_config=...)`
- `install_runtime_context(config, runtime_context)`

`RuntimeContext` owns the canonical `thread_id`, `run_id`, `user_id`,
`agent_name`, and `app_config` fields used in LangGraph `Runtime.context`.

## Adapter

`apply_runtime_context_overrides()` adapts the Gateway request body `context`
field into the active runtime options container:

- If the request already selected `config.context`, overrides are merged into
  `config.context`.
- Otherwise overrides are merged into `config.configurable`.
- Only agent-runtime option keys are accepted.
- Existing runtime options win over body-level overrides.

`RuntimeContext.from_config()` adapts the final `RunnableConfig` into the
LangGraph runtime context. It preserves non-reserved caller context values but
overwrites canonical run identity fields with the server-created `thread_id`
and `run_id`.

## Migration Rules

- Do not copy body-context merge logic in routes or tests.
- Do not add `config.configurable` when the request is already in
  `config.context` mode.
- Resolve custom-agent `agent_name` through the active run config container.
- Resolve `user_id` from context first, then run metadata.
- Always install `app_config` through `RuntimeContext`, not an ambient singleton.

## Done when

1. Gateway service tests call `apply_runtime_context_overrides()` instead of
   hand-copying merge logic.
2. Harness worker installs `RuntimeContext` before constructing
   `langgraph.runtime.Runtime`.
3. Reserved caller-supplied context fields cannot override server run identity.
4. Phase test gate passes.

## Stop if

- LangGraph requires mutually incompatible `context` and `configurable`
  semantics for supported runtime versions.
- Frontend requests must change how `context` or `config.configurable` are sent.
- A custom agent must derive `agent_name` from outside the active runtime config.

## Test Evidence

Validated with:

```bash
PYTHONPATH=. uv run python -m pytest tests/test_gateway_services.py tests/test_run_worker_rollback.py tests/test_lead_agent_model_resolution.py -q
```

Result: `63 passed`.
