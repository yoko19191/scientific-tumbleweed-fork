# Storage Guidelines

> Where persistent files live, how code should read/write them, and
> what's still on the path to migrate.

Last updated: Phase I (Round 2.1) of the Postgres + object-storage work
(`feature/postgres-migration`).

---

## TL;DR

- **Database-backed state** (users, memory, tool cache, channel threads,
  LangGraph checkpoints, LangGraph store) lives in PostgreSQL. Access
  it through SQLModel / SQLAlchemy (`deerflow.db.get_session_factory()`
  for async, `deerflow.db.sync_session_scope()` for sync).
- **Object-style persistent files** (future: uploads, outputs,
  workspace, memory archives) flow through OpenDAL via
  `deerflow.storage.get_operator()` / `get_async_operator()`. The
  default backend is the local filesystem at `.deer-flow/storage`; a
  MinIO/S3 backend is enabled by switching one stanza in
  `config.yaml`.
- **System configuration** (`config.yaml`, `.env`, `langgraph.json`,
  `skills/` source tree) stays on `Path` + `open()`. These files are
  read at startup or mounted read-only into the sandbox; they are not
  user data.
- **Legacy disk state** is under `backend/.deer-flow-legacy/` and
  is safe to delete once an operator no longer wants it.

---

## OpenDAL: today's scope

`deerflow.storage` wraps a single OpenDAL `Operator` (sync) and
`AsyncOperator` (async). Both share the same resolved backend config
from `storage:` in `config.yaml`.

```python
from deerflow.storage import get_operator, uploads_key

op = get_operator()
key = uploads_key(user_id, thread_id, "report.pdf")
op.write(key, pdf_bytes)
blob = op.read(key)
```

Object keys are built by `deerflow.storage.paths` so that renames
(future tenant prefixes, alternative namespaces) stay local to one
module. **Never hand-build object keys from user input** — the helpers
validate segments and reject path-traversal.

Supported backends today (`storage.backend` in config):

| Backend | Intended use |
|---------|--------------|
| `fs`    | Local development, tests, single-node deployments |
| `s3`    | MinIO, AWS S3, Aliyun OSS, Cloudflare R2 — any S3-compatible service |

Switching from `fs` to `s3` does not require code changes.

### What Phase F already migrated

- Nothing yet beyond the baseline. The factory + key helpers are wired
  up and smoke-verified end-to-end through `storage_smoke.py`.
- `StorageConfig` flows in from `config.yaml` through `AppConfig`; tests
  can rebind via `set_storage_config` + `reset_operators`.

### What Round 2.1 migrated to OpenDAL

The first three call sites moved off `Path` and onto `deerflow.storage`:

| Data | Old path | New OpenDAL key | Helpers |
|------|----------|-----------------|---------|
| User profile | `.deer-flow/users/{uid}/USER.md` | `user-profile/{uid|__global__}/USER.md` | `user_profile_key` |
| Custom agents | `.deer-flow/users/{uid}/agents/{name}/{config.yaml,SOUL.md}` | `custom-agents/{uid|__global__}/{name}/...` | `user_agent_prefix` / `user_agent_config_key` / `user_agent_soul_key` / `user_agents_prefix` |
| Per-user extensions override | `.deer-flow/users/{uid}/extensions_config.json` | `user-extensions/{uid}/extensions_config.json` | `user_extensions_override_key` |

The matching `Paths` helpers (`user_md_file_for`, `user_agents_dir`,
`user_agent_dir`, `user_extensions_config_file`, `resolve_user_md`,
`resolve_agents_dir`, `resolve_agent_dir`) carry `.. deprecated::
Round 2.1` notices and point at the new keys; they are kept only for
tests that still construct fixture trees with raw `Path` objects.

The repo-level `<repo>/extensions_config.json` (the **public** MCP
configuration) is intentionally left on disk — it is read once at
startup, every user shares it, and editing it is a developer task,
not a per-user UI flow.

### What is explicitly deferred

These sites **stay on `Path` / direct filesystem access** in Round 2:

1. **Uploads, outputs, workspace, acp-workspace** under
   `backend/.deer-flow/users/{user_id}/threads/{thread_id}/…`.

   *Why*: the sandbox runtime bind-mounts these directories into the
   container (`/mnt/user-data/{uploads,outputs,workspace}`). Moving
   them to OpenDAL without first redesigning the sandbox lifecycle
   (pull-execute-push against MinIO) would break the agent's view of
   its own data. This migration is tracked for the MinIO round.

2. **`skills/` source tree**. The sandbox bind-mounts this directory
   read-only so agents can import skills by path. Only the
   `extensions_config.json` metadata (enable/disable flags) belongs
   in object storage, and even that is debatable — it is per-user
   configuration, not user data.

3. **`config.yaml`, `.env`, `langgraph.json`, `extensions_config.json`
   (global)**. Read once at process start. Keeping them on the
   filesystem means `make doctor`, editors, and diff tools all work
   without an OpenDAL-aware shell.

4. **`FileMemoryStorage` and `FileChannelStore`**. These are fallback
   backends selected only when Postgres is unavailable (tests,
   offline tooling). The production path is PostgreSQL; migrating
   the file fallback buys little and costs a maintenance burden.

---

## Decision: where does my feature's data go?

| Data shape | Put it in… | Example |
|------------|-----------|---------|
| Structured row(s) with queries / updates | PostgreSQL via SQLModel | Users, memory, channel mappings, tool cache |
| Opaque blobs (PDF, CSV, PNG, tar) users upload or agents produce | OpenDAL via `get_operator()` **and** the sandbox mount contract (see deferred section) | Agent-generated charts, user uploads, artifact downloads |
| Configuration read once at startup | Filesystem + `open()` | `config.yaml`, `.env` |
| Source code an agent imports | Filesystem (read-only mount) | `skills/` |
| Ephemeral per-request data | In-memory (`BytesIO`) or `tempfile.NamedTemporaryFile` | File conversion intermediates |

If in doubt, ask on the `feature/postgres-migration` PR — we would
rather consolidate on one of the patterns above than grow a fifth.

---

## Rules for new code

1. **Never concatenate object keys by hand.** Use
   `deerflow.storage.paths.uploads_key` / `outputs_key` / `workspace_key`.
   If you need a new namespace, add a helper there.

2. **Do not leak `Path` objects returned by `deerflow.config.paths.Paths`
   into request handlers** when the underlying data is covered by
   OpenDAL or PostgreSQL. The `Paths` helpers are still legitimate for
   sandbox-facing / system-config paths, but they should not be the
   authoritative location for user data.

3. **Prefer the async operator in async routes** — the sync operator
   exists for repositories whose public interface is synchronous
   (memory storage, tool cache, channel store). Mixing them is fine;
   both share the backend.

4. **Write a focused test that rebinds the backend** when you add a
   new migration. `opendal.AsyncOperator("memory")` is the fastest
   possible fixture:

   ```python
   from deerflow.config.storage_config import StorageConfig, set_storage_config
   from deerflow.storage import reset_operators
   set_storage_config(StorageConfig(backend="fs", fs={"root": tmp_path}))
   reset_operators()
   ```

5. **Document the decision.** Every MR that moves a file path to
   OpenDAL (or consciously keeps it on `Path`) should add a one-line
   rationale to this doc.

---

## Operational notes

### Local development

`docker/docker-compose-dev.yaml` mounts the host repository into the
gateway container, so the `fs(root=.deer-flow/storage)` backend lives
alongside the rest of the state directory. No extra volumes required.

### Tests

Tests should use `StorageConfig(backend="fs", fs={"root": tmp_path})`
and call `reset_operators()` so each test gets a fresh directory.
Avoid relying on the shared `.deer-flow/storage/` tree from the
running dev container.

### MinIO / S3 migration (future round)

When the MinIO round lands:

1. Add the MinIO compose service.
2. Flip `storage.backend` to `s3` and fill in `storage.s3`.
3. Redesign sandbox lifecycle to pull uploaded inputs from MinIO into
   the sandbox on acquire, and push produced outputs back on release.
4. Update this document's "deferred" list.

The OpenDAL layer itself requires no code changes for step 1 and 2;
the entire migration surface is the sandbox boundary.
