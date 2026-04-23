# Tenant Isolation Audit Findings

Findings will be recorded here as code paths are inspected.

## Initial Map
- Auth-related gateway code exists under `backend/app/gateway/auth*` and frontend has an auth provider/guard.
- `backend/docs/rfc-custom-main.md` describes the desired user isolation plan: thread owner checks from an auth PR, plus planned per-user isolation for memory, agents, skills, profile, and extension config.
- Need to verify actual implementation rather than relying on the RFC.

## Auth Reality
- `AuthMiddleware` is a coarse gate only: it checks that an `access_token` cookie exists on non-public paths, but does not decode it or populate `request.state.auth`.
- Real user resolution happens through `@require_auth` / `get_current_user_from_request()`.
- Therefore any route that only calls `get_optional_user_id(request)` without `@require_auth` sees `None` and falls back to global storage.

## Current Recheck Notes
- Thread endpoints now call `require_thread_owner()` for delete, patch, get, state, state update, history, and all thread-scoped run operations. `listByUser` uses user-scoped ownership namespaces. This is stronger than the earlier partial state.
- Stateless `/api/runs/stream` and `/api/runs/wait` verify owner when caller supplies a thread_id and bind auto-created thread IDs when a user ID is available.
- Memory routes now use `Depends(get_current_user_id)`, so API memory reads/writes are per authenticated user.
- Uploads and artifacts call `require_thread_owner()` and resolve paths with the returned `user_id`, so the Gateway path is both ownership-gated and user-prefixed.
- Default nginx `/api/langgraph/*` routes through Gateway (`LANGGRAPH_UPSTREAM=gateway:8001`, `LANGGRAPH_REWRITE=/api/`). Overriding it to `langgraph:2024` bypasses owner checks.
- Agent, skill, and MCP routers still rely on `get_optional_user_id(request)` without `@require_auth`; because `AuthMiddleware` does not populate `request.state.auth`, these routes cannot see the authenticated user from a normal request.
- Sandbox runtime passes `metadata.user_id` to memory/thread-data/prompt code, but sandbox acquisition still calls `provider.acquire(thread_id)` rather than `provider.acquire(thread_id, user_id)` in `sandbox/tools.py` and `sandbox/middleware.py`; AIO sandbox mounts may therefore use legacy thread paths rather than user-prefixed mounts.
- Thread deletion calls `_delete_thread_data(thread_id)` without `user_id`, so it deletes legacy thread data rather than `users/{user_id}/threads/{thread_id}`.
- Channel integrations maintain their own channel/chat/user mapping and often call LangGraph directly; they are isolated by channel session, not by the web JWT tenant model.
- Frontend `AuthGuard` blocks unauthenticated workspace views, `useThreads()` lists `/api/threads/listByUser`, stream sessionStorage is user-prefixed, and AuthProvider clears caches on user switch/logout. These are view/cache isolation, not authorization.

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
