# Phase 4 - User Extensions Config

## Scope

This phase centralizes effective extensions configuration for MCP servers and
skills.

Covered modules:

- `packages/harness/deerflow/config/extensions_config.py`
- `packages/harness/deerflow/skills/loader.py`
- `app/gateway/routers/mcp.py`
- `app/gateway/routers/skills.py`

## Constraints

- The repo-level `extensions_config.json` remains the developer-level global
  config loaded from disk.
- Per-user overrides live only in object storage under
  `user-extensions/{user_id}/extensions_config.json`.
- Callers must use the OpenDAL key helper `user_extensions_override_key()`;
  no route or loader reads the old per-user disk path directly.
- The existing config file format is unchanged.

## Interface

Effective config is exposed through:

- `get_effective_extensions_config(user_id=None, global_config=None)`
- `aget_effective_extensions_config(user_id=None, global_config=None)`
- `load_user_extensions_override(user_id)`
- `aload_user_extensions_override(user_id)`
- `asave_user_extensions_override(user_id, data)`
- `aset_user_skill_enabled(user_id, skill_name, enabled)`
- `aset_user_mcp_server_enabled(user_id, server_name, enabled)`

`get_effective_extensions_config()` and its async variant are the common read
interface for skills and MCP.

## Adapter

The adapter reads the developer-level global `ExtensionsConfig`, then merges a
per-user override on top:

1. Global MCP server definitions are preserved.
2. User MCP overrides may change `enabled` for known global servers.
3. Unknown user MCP server names are ignored.
4. Global skill states are preserved.
5. User skill overrides may change or add per-skill `enabled` state.

Invalid, missing, or unreadable per-user override objects are treated as empty
overrides and logged when useful.

## Migration Rules

- `load_skills(..., user_id=...)` must call
  `get_effective_extensions_config(user_id)`.
- MCP configuration reads must call
  `aget_effective_extensions_config(user_id)`.
- Skills and MCP toggle routes must call the shared async setters, not
  hand-edit JSON.
- Per-user override writes must preserve unrelated sections.

## Done when

1. Skills loader and MCP router read through the same effective config
   interface.
2. Skills router and MCP router write through shared per-user override setters.
3. Tests seed overrides through `user_extensions_override_key()`.
4. Phase test gate passes.

## Stop if

- A user override must add or mutate full MCP server definitions instead of
  only toggling known global servers.
- The `extensions_config.json` schema must change.
- Global developer config needs to move from disk to object storage.

## Test Evidence

Validated with:

```bash
PYTHONPATH=. uv run python -m pytest tests/test_skill_enablement_user_prefixed.py tests/test_mcp_config_secrets.py tests/test_mcp_client_config.py tests/test_skills_loader.py tests/test_skills_custom_router.py -q
```

Result: `51 passed`.

Validated with:

```bash
PYTHONPATH=. uv run ruff check packages/harness/deerflow/config/extensions_config.py packages/harness/deerflow/skills/loader.py app/gateway/routers/mcp.py app/gateway/routers/skills.py tests/test_skill_enablement_user_prefixed.py tests/test_mcp_config_secrets.py tests/test_mcp_client_config.py tests/test_skills_loader.py tests/test_skills_custom_router.py
```

Result: `All checks passed!`.
