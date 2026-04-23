# Tenant Isolation Audit Plan

## Goal
Analyze current tenant/user isolation and view isolation behavior, and identify what is isolated versus not yet isolated.

## Phases
- [complete] Map auth and user-context entry points.
- [complete] Inspect persistence models and repositories for user ownership fields and filters.
- [complete] Inspect API routes and service paths for tenant scoping.
- [complete] Inspect LangGraph/thread state and runtime isolation behavior.
- [complete] Inspect frontend view guards and browser-side cache scoping.
- [complete] Summarize completed isolation, gaps, and risk level.

## Notes
- This is an analysis-only pass. Do not change production code.
- Preserve unrelated existing working tree changes.

## Summary
- Authentication exists through JWT cookies; `AuthMiddleware` only checks cookie presence, while `get_current_user_id` / `require_thread_owner` perform real user verification.
- Thread list/get/state/history/runs/uploads/artifacts are owner-checked on the Gateway path.
- Memory API is per-user via `Depends(get_current_user_id)`.
- Per-user path helpers exist for profile/agents/skills/MCP toggles, but several HTTP routers still call `get_optional_user_id(request)` without `@require_auth`, so they do not populate `request.state.auth` and often fall back to global state or return 401.
- Frontend view isolation is mostly guard/list filtering/cache clearing; it is useful UX but not a security boundary.
