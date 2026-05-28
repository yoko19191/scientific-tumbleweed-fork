# Phase 6 - Run State, Streaming, and Persistence

## Scope

This phase centralizes run-facing runtime helpers:

- `packages/harness/deerflow/runtime/runs/records.py`
- `packages/harness/deerflow/runtime/runs/checkpoints.py`
- `packages/harness/deerflow/runtime/stream_bridge/sse.py`
- `app/gateway/routers/thread_runs.py`
- `app/gateway/routers/runs.py`
- `app/gateway/services.py`

## Constraints

- SSE wire format stays unchanged.
- The LangGraph checkpoint backend stays unchanged.
- Gateway response models stay in the Gateway layer.
- Harness runtime helpers must not import `app.*`.

## Interface

Run persistence mapping is exposed through:

- `RunRecord.from_store_row(row)`

Checkpoint-backed state reads are exposed through:

- `thread_checkpoint_config(thread_id, checkpoint_id=None, checkpoint_ns="")`
- `checkpoint_channel_values(checkpoint_tuple)`
- `read_thread_checkpoint_values(checkpointer, thread_id, checkpoint_id=None, checkpoint_ns="")`
- `read_thread_final_state(checkpointer, thread_id, checkpoint_ns="")`

SSE frame formatting is exposed through:

- `format_sse_frame(event, data, event_id=None)`

Gateway `format_sse()` remains as a compatibility wrapper around
`format_sse_frame()`.

## Adapter

The checkpoint adapter owns the LangGraph root checkpoint namespace convention
(`checkpoint_ns=""`) and the extraction of `checkpoint.channel_values`.
`read_thread_final_state()` then applies the canonical runtime serializer so
internal LangGraph keys such as `__pregel_*` and `__interrupt__` are stripped
before HTTP wait endpoints return a state payload.

`RunRecord.from_store_row()` owns hydration from persistent `RunStore` rows to
read-only runtime records. `RunManager` still owns in-memory lifecycle,
concurrency, and persistence calls, but store-row shape conversion is now on the
value object instead of hidden inside manager internals.

`format_sse_frame()` owns the LangGraph-compatible SSE field order:
`event`, `data`, optional `id`, blank line.

## Migration Rules

- Run wait routes must call `read_thread_final_state()` instead of hand-reading
  checkpointer tuples.
- Title sync may read raw channel values through `read_thread_checkpoint_values()`.
- Store hydration must call `RunRecord.from_store_row()`.
- Gateway code may keep HTTP response shaping locally, but stream wire
  formatting should delegate to the harness runtime helper.

## Done when

1. Thread-scoped and stateless wait paths share the checkpoint final-state
   helper.
2. Stream formatting has a harness-level protocol helper and gateway wrapper.
3. RunStore hydration goes through `RunRecord.from_store_row()`.
4. Phase test gate passes.

## Stop if

- Multi-process streaming requires Redis or another durable stream backend.
- The frontend requires a different SSE wire shape.
- Checkpoint reads need backend-specific behavior that cannot fit the shared
  adapter.

## Test Evidence

Validated with:

```bash
PYTHONPATH=. uv run python -m pytest tests/test_run_manager.py tests/test_stream_bridge.py tests/test_sse_format.py tests/test_run_worker_rollback.py tests/test_thread_runs_router.py tests/test_runs_router_ownership.py -q
```

Result: `73 passed`.

Validated with:

```bash
PYTHONPATH=. uv run ruff check packages/harness/deerflow/runtime/runs/records.py packages/harness/deerflow/runtime/runs/checkpoints.py packages/harness/deerflow/runtime/runs/manager.py packages/harness/deerflow/runtime/runs/__init__.py packages/harness/deerflow/runtime/stream_bridge/sse.py packages/harness/deerflow/runtime/stream_bridge/__init__.py packages/harness/deerflow/runtime/__init__.py app/gateway/services.py app/gateway/routers/thread_runs.py app/gateway/routers/runs.py tests/test_run_manager.py tests/test_sse_format.py tests/test_thread_runs_router.py
```

Result: `All checks passed!`.
