# Phase 3 - Canonical Agent Entry and Middleware Chain

## Scope

This phase centralizes middleware ordering for both agent entry points:

- `packages/harness/deerflow/agents/lead_agent/agent.py`
- `packages/harness/deerflow/agents/factory.py`
- `packages/harness/deerflow/agents/middleware_builder.py`

## Constraints

- `make_lead_agent()` and `create_deerflow_agent()` keep their public call
  shapes.
- Middleware behavior stays owned by each middleware implementation.
- Entry points may decide which concrete middleware slots are enabled, but not
  the final relative order.
- `ClarificationMiddleware` remains the final middleware whenever present.
- `SafetyFinishReasonMiddleware` remains after custom middleware and before
  clarification so reverse-order `after_model` dispatch suppresses unsafe tool
  calls before loop/subagent accounting observes them.

## Interface

Canonical ordering is exposed through:

- `build_ordered_middleware_chain(...)`
- `insert_extra_middlewares(chain, extras)`
- `ensure_clarification_last(chain)`

`build_ordered_middleware_chain()` accepts concrete middleware slots and returns
the ordered list used by LangChain `create_agent()`.

## Adapter

`make_lead_agent()` still resolves runtime configuration, model capabilities,
plan mode, subagent limits, loop detection, and safety configuration in the
lead-agent module. It now passes those concrete middleware instances into the
shared builder.

`create_deerflow_agent()` still adapts SDK `RuntimeFeatures` into concrete
middleware instances and feature-injected tools. It now delegates ordering and
`extra_middleware` insertion to the shared builder.

## Migration Rules

- Do not append lead-agent middleware order directly in
  `lead_agent/agent.py`.
- Do not add SDK-only ordering rules in `factory.py`.
- Add new middleware categories as named slots in `middleware_builder.py`.
- Keep extra middleware insertion in `insert_extra_middlewares()` so `@Next`,
  `@Prev`, circular-anchor detection, and clarification-tail repair stay shared.

## Done when

1. `make_lead_agent()` middleware assembly uses
   `build_ordered_middleware_chain()`.
2. `create_deerflow_agent()` middleware assembly uses
   `build_ordered_middleware_chain()` and `insert_extra_middlewares()`.
3. Tests prove both entry points delegate to the shared builder.
4. Tests prove `SubagentLimitMiddleware`, `LoopDetectionMiddleware`,
   `SafetyFinishReasonMiddleware`, and `ClarificationMiddleware` keep their
   tail order.
5. Phase test gate passes.

## Stop if

- LangChain changes middleware dispatch semantics in a way that invalidates the
  safety/loop/subagent tail ordering.
- SDK users need per-call ordering overrides beyond `@Next` and `@Prev`.
- A new middleware needs to be conditionally inserted relative to provider
  implementation details rather than named middleware slots.

## Test Evidence

Validated with:

```bash
PYTHONPATH=. uv run python -m pytest tests/test_create_deerflow_agent.py tests/test_lead_agent_model_resolution.py tests/test_safety_finish_reason_middleware.py tests/test_loop_detection_middleware.py tests/test_harness_boundary.py -q
```

Result: `162 passed`.

Validated with:

```bash
PYTHONPATH=. uv run ruff check packages/harness/deerflow/agents/middleware_builder.py packages/harness/deerflow/agents/factory.py packages/harness/deerflow/agents/lead_agent/agent.py tests/test_create_deerflow_agent.py tests/test_lead_agent_model_resolution.py
```

Result: `All checks passed!`.
