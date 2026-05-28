# Phase 5 - Custom Agent Store

## Scope

This phase centralizes custom-agent storage lifecycle behavior:

- `packages/harness/deerflow/config/agents_config.py`
- `app/gateway/routers/agents.py`
- `packages/harness/deerflow/tools/builtins/setup_agent_tool.py`
- `packages/harness/deerflow/tools/builtins/update_agent_tool.py`

## Constraints

- Custom-agent object keys stay under
  `custom-agents/{user_id|__global__}/{name}/`.
- `/api/agents` response schemas stay unchanged.
- `config.yaml` and `SOUL.md` remain the persisted object names.
- Agent names use one validation and normalization implementation.

## Interface

Custom-agent storage is exposed through `CustomAgentStore`:

- `exists(name, user_id=None)`
- `load_config(name, user_id=None)`
- `load_soul(name, user_id=None)`
- `list_agents(user_id=None)`
- `write_config(config, user_id=None)`
- `write_soul(name, soul, user_id=None)`
- `create_agent(config, soul, user_id=None)`
- `delete_agent(name, user_id=None)`

Name handling is exposed through:

- `validate_agent_name(name)`
- `normalize_agent_name(name)`

Legacy loader functions (`load_agent_config`, `load_agent_soul`,
`list_custom_agents`) now delegate to `CustomAgentStore`.

## Adapter

`CustomAgentStore` adapts the OpenDAL operator and object-key helpers into a
small lifecycle interface. It owns:

- config YAML serialization
- unknown-field stripping during config reads
- object existence checks
- SOUL.md read/write
- prefix listing and deletion
- best-effort cleanup when create partially succeeds

## Migration Rules

- Gateway agent routes must use `CustomAgentStore`; they must not hand-write
  YAML or delete per-key prefixes themselves.
- `setup_agent` and `update_agent` tools must use `CustomAgentStore`.
- Channel assistant-id normalization must call `normalize_agent_name()` after
  legacy underscore-to-hyphen conversion.
- Tests should seed and assert OpenDAL object keys, not the old local path
  helpers.

## Done when

1. Router/tool call sites use `CustomAgentStore`.
2. Agent name normalization has one implementation.
3. OpenDAL-key user-isolation tests replace stale path-based tests.
4. Phase test gate passes.

## Stop if

- Existing custom-agent object keys need migration.
- Gateway routes and agent tools require intentionally different YAML shapes.
- Delete semantics must become atomic across object-store backends.

## Test Evidence

Validated with:

```bash
PYTHONPATH=. uv run python -m pytest tests/test_agents_user_prefixed.py tests/test_custom_agent.py tests/test_setup_agent_tool.py tests/test_update_agent_tool.py -q
```

Result: `64 passed`.

Validated with:

```bash
PYTHONPATH=. uv run ruff check app/channels/manager.py app/gateway/routers/agents.py packages/harness/deerflow/config/agents_config.py packages/harness/deerflow/tools/builtins/setup_agent_tool.py packages/harness/deerflow/tools/builtins/update_agent_tool.py tests/test_agents_user_prefixed.py tests/test_custom_agent.py tests/test_setup_agent_tool.py tests/test_update_agent_tool.py
```

Result: `All checks passed!`.
