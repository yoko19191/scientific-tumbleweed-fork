# User Isolation Audit Plan

## Goal
Analyze how far user isolation is implemented in the current codebase, and identify what is isolated versus not yet isolated.

## Phases
- [complete] Map auth and user-context entry points.
- [complete] Inspect persistence models and repositories for user ownership fields and filters.
- [complete] Inspect API routes and service paths for tenant scoping.
- [complete] Inspect LangGraph/thread state and runtime isolation behavior.
- [complete] Summarize completed isolation, gaps, and risk level.

## Notes
- This is an analysis-only pass. Do not change production code.
- Preserve unrelated existing working tree changes.

## Summary
- Authentication exists, but many routes only check cookie presence or bypass gateway entirely.
- Per-user path helpers exist for memory/profile/agents/skills, but most HTTP callers do not populate `request.state.auth`, so they fall back to global storage.
- Thread list/delete have partial owner enforcement; direct thread state/history/run/artifact/upload paths are not owner checked.
