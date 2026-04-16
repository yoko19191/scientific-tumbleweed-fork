# User Isolation Audit Findings

Findings will be recorded here as code paths are inspected.

## Initial Map
- Auth-related gateway code exists under `backend/app/gateway/auth*` and frontend has an auth provider/guard.
- `backend/docs/rfc-custom-main.md` describes the desired user isolation plan: thread owner checks from an auth PR, plus planned per-user isolation for memory, agents, skills, profile, and extension config.
- Need to verify actual implementation rather than relying on the RFC.

## Auth Reality
- `AuthMiddleware` is a coarse gate only: it checks that an `access_token` cookie exists on non-public paths, but does not decode it or populate `request.state.auth`.
- Real user resolution happens through `@require_auth` / `get_current_user_from_request()`.
- Therefore any route that only calls `get_optional_user_id(request)` without `@require_auth` sees `None` and falls back to global storage.

## Resource Scoping Findings
- Memory router routes call `get_optional_user_id()`, but are not decorated with `@require_auth`; memory reads/writes therefore use global memory in normal requests.
- Agents/profile router routes call `get_optional_user_id()`, but are not decorated with `@require_auth`; custom agents and USER.md therefore use global paths in normal requests.
- Skills router partly has user-aware loader/install/update code, but most routes are not `@require_auth`; many paths fall back to global config. The `/skills/custom/*` management endpoints also use global manager helpers directly.
- Thread router has `bindUser`, `listByUser`, and `delete` with `@require_auth`; create/search/get/state/history do not enforce owner checks.
- Run routes create/use runs by arbitrary thread_id and rely on `get_optional_user_id()` inside `start_run`; without `@require_auth`, user_id metadata is usually not injected.

## Additional Implementation Gaps
- Default nginx standard mode routes `/api/langgraph/*` directly to LangGraph Server, and `backend/langgraph.json` has no auth configuration. Main chat traffic can bypass Gateway auth entirely.
- `list_custom_agents(user_id=...)` scans the user-scoped directory but calls `load_agent_config(entry.name)` without passing `user_id`, so even the lower-level per-user listing implementation is inconsistent.
- Lead-agent prompt skill injection uses global enabled skill cache (`load_skills(enabled_only=True)`) and does not take user_id, so user-scoped skills/config are not reflected in agent prompts.
- MCP config is global via `get_extensions_config()` and `ExtensionsConfig.from_file()`; no per-user MCP server config isolation is implemented.
- Uploads and artifacts are thread-id scoped on disk, but do not verify that the current user owns the thread.

