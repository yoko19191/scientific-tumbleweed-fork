# Phase 1 - User Scoped Thread Resource

## Scope

This phase introduces a Gateway-owned module for authenticated access to thread resources:
`app.gateway.thread_resources`.

Covered call sites:

- Thread local-data deletion.
- Upload create/list/delete routing.
- Artifact and skill-archive preview routing.
- `.skill` archive installation from a thread output path.

## Constraints

- HTTP paths and response schemas stay unchanged.
- Client-supplied `user_id` is never trusted for thread resource access.
- Thread file access must first resolve an authenticated thread resource.
- Routes must not call user namespace helpers directly.
- Routes must not resolve a thread virtual path without the authenticated `user_id`.

## Interface

`get_authenticated_thread_resource(request, thread_id)` verifies ownership through
`require_thread_owner()` and returns `AuthenticatedThreadResource`.

`AuthenticatedThreadResource` exposes:

- `thread_id`
- `user_id`
- `resolve_virtual_path(virtual_path)`
- `uploads_dir()`
- `delete_local_data()`

Routes use this object as the stable interface for thread-local filesystem work.

## Adapter

`AuthenticatedThreadResource` adapts the Gateway auth/ownership layer to the lower-level
`deerflow.config.paths.Paths` helpers. It always passes `user_id` into path resolution,
so `/mnt/user-data/...` maps to `users/{user_id}/threads/{thread_id}/...` for
authenticated Gateway requests.

Store namespace helpers in the same module centralize:

- user thread record namespace resolution
- user thread ownership namespace resolution
- user thread record lookup with optional legacy fallback
- ownership and thread-record deletion

## Migration Rules

- Thread-scoped routes call `get_authenticated_thread_resource()` before accessing
  uploads, artifacts, skill archives, or local thread data.
- Route modules import namespace helpers only from `app.gateway.thread_resources`.
- Legacy global thread namespaces remain available only through compatibility helpers.
- `.skill` installation uses the authenticated resource path and installs into the
  authenticated user's custom skill directory.

## Done when

1. `app.gateway.thread_resources` is the Gateway interface for authenticated thread
   filesystem resources.
2. Thread delete removes only the authenticated user's local thread directory.
3. Uploads and artifacts resolve paths through the authenticated thread resource.
4. Skill install denies unowned threads and resolves the archive path with `user_id`.

## Stop if

- Anonymous threads are required for production thread-resource routes.
- A route must accept a thread virtual path before the authenticated owner is known.
- Existing clients require a different HTTP path or response schema.

## Test Evidence

Validated with:

```bash
PYTHONPATH=. uv run python -m pytest tests/test_thread_ownership.py tests/test_threads_router.py tests/test_uploads_router.py tests/test_artifacts_router.py tests/test_skills_custom_router.py -q
```

Result: `79 passed`.
