# SQLite → PostgreSQL Migration

This document records how Scientific Tumbleweed moved off SQLite + local JSON
files to **PostgreSQL (ParadeDB)** as the single persistence backend.

- Branch: `feature/postgres-migration`
- Target image: `paradedb/paradedb:0.23.4-pg18` (Postgres 18 + pgvector +
  pg_search/BM25 + pg_stat_statements)
- Strategy: **archive-then-restart**. No row-level migration. All legacy
  SQLite/JSON files are moved under `backend/.deer-flow-legacy/` and kept
  as a read-only snapshot.

## Why we did it

- `checkpoints.db` grew to 4.1GB and SQLite's single-writer lock was
  choking concurrent runs from gateway + langgraph + workers.
- We need multi-instance / Kubernetes deployments.
- Ops wants normal tooling: `pg_dump` / WAL-G / PITR / audit.
- Future cloud move (RDS / Cloud SQL) is a DSN swap instead of a migration.
- Project standardization.

## What changed

### Schema

LangGraph auto-creates its own tables on first boot. Our migration only
adds four application-owned tables on top.

| Table | Owner | Phase | Purpose |
|-------|-------|-------|---------|
| `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations` | LangGraph | 1 | graph state & pending writes |
| `store`, `store_migrations` | LangGraph | 1 | long-term namespaced KV |
| `users` | app | 2 | replaces `.deer-flow/users.db` |
| `user_memory` | app | 3 | JSONB memory, replaces `.deer-flow/memory.json` |
| `tool_cache` | app | 4 | TTL cache, replaces `.deer-flow/cache/academic_search.db` |
| `channel_threads` | app | 5 | IM chat → thread map, replaces `.deer-flow/channels/store.json` |

Extensions enabled: `vector`, `pg_search`, `pg_stat_statements`
(`docker/postgres/init.sql`).

Application schema is created idempotently at gateway startup by
`deerflow.db.setup.ensure_schema()`, guarded by a Postgres advisory lock
so concurrent pods can race safely.

See `backend/docs/POSTGRES_SCHEMA.md` for the LangGraph-owned DDL (captured
live via `pg_dump` after the first boot against Postgres).

### Code

Round 1 landed handwritten asyncpg / psycopg repositories; Round 2
rebuilt the access layer on SQLAlchemy 2.0 + SQLModel so every table
has a single source of truth.

- `backend/packages/harness/deerflow/db/` — SQLAlchemy + SQLModel
  plumbing. `engine.py` owns an async engine + sync engine
  (psycopg3 driver) sharing one DSN resolver in `dsn.py`; `pool.py`
  keeps a thin asyncpg pool around for the `pg_advisory_xact_lock`
  transaction in `setup.ensure_schema()`; `models/` holds the four
  SQLModel table classes.
- `backend/alembic/` — Alembic workspace. `env.py` pulls the DSN from
  `deerflow.db.dsn`, filters autogenerate to SQLModel-owned tables,
  and stamps the empty baseline at `e35828dc111e`.
- `scripts/emit_init_sql.py` + `make emit-init-sql` / `make
  check-init-sql` — regenerates `docker/postgres/init.sql` from the
  SQLModel metadata so `init.sql` stays the authoritative bootstrap
  with CI drift detection.
- `backend/app/gateway/auth/repositories/postgres.py` —
  `PostgresUserRepository` uses SQLModel `AsyncSession`. Handles
  `UniqueViolation` by matching the offending index name
  (`users_email_key`, `users_username_key`,
  `idx_users_oauth_identity`). SQLite repository is still importable
  for tests but no longer reachable from runtime config.
- `backend/packages/harness/deerflow/agents/memory/postgres_storage.py`
  — `PostgresMemoryStorage` wraps `sync_session_scope` and uses
  `INSERT … ON CONFLICT DO UPDATE … RETURNING version` for the
  optimistic-locking upsert.
- `backend/packages/harness/deerflow/community/semantic_scholar/postgres_cache.py`
  — `PostgresTTLCache` uses SQLModel selects + `DELETE ... WHERE
  expires_at <= NOW()` for the vacuum sweep.
- `backend/app/channels/store.py` — `PostgresChannelStore` uses
  SQLModel / SQLAlchemy core expressions; `ChannelStore(path=None)`
  is a factory that defaults to Postgres and falls back to
  `FileChannelStore` only when the sync engine isn't initialised
  (tests / offline tooling).
- `backend/packages/harness/deerflow/storage/` — OpenDAL operator
  factory + object-key helpers. `StorageConfig` in `config.yaml`
  drives the backend (`fs` for development, `s3` for MinIO / AWS /
  Aliyun later). See `backend/docs/STORAGE_GUIDELINES.md` for the
  decision tree on when to use Postgres vs OpenDAL vs plain `Path`.

### Config

- `config.yaml` / `config.example.yaml`:
  - `checkpointer.type: postgres` + `connection_string: $POSTGRES_DSN`
  - `memory.storage_class: deerflow.agents.memory.postgres_storage.PostgresMemoryStorage`
  - new `storage:` block driving the OpenDAL backend (default `fs`)
- `backend/packages/harness/deerflow/config/`:
  - `memory_config.py`: default `storage_class` flipped to
    `PostgresMemoryStorage`
  - `storage_config.py`: new, describes the OpenDAL backend
  - `app_config.py`: wires both loaders into `AppConfig`
- `backend/app/gateway/auth/config.py`: runtime backend switch
  removed. `AUTH_REPOSITORY_BACKEND`,
  `DEERFLOW_TOOL_CACHE_BACKEND`, and `DEERFLOW_CHANNEL_STORE_BACKEND`
  are gone; rollback now goes through `git revert`.

### Docker / env

- `docker/docker-compose.yaml` and `docker-compose-dev.yaml` pin the
  paradedb image at `paradedb/paradedb:0.23.4-pg18` and mount the
  data volume at `/var/lib/postgresql` (PG 18 layout requirement).
- Service credentials are uniformly `scientifictumbleweed`
  (DB / user / password) across `.env`, `.env.example`,
  `config.yaml`, MCP config, and docs.
- `docker/postgres/init.sql` is now a **full** schema bootstrap
  regenerated from SQLModel; running a new volume boots the complete
  application schema before gateway starts.
- `.mcp.json` at the repo root registers the `postgres` MCP server
  for Claude Code so contributors get SQL query access on clone.

### Dependencies

- SQLAlchemy + SQLModel + Alembic added:
  `sqlalchemy[asyncio] >= 2.0.35`, `sqlmodel >= 0.0.22`,
  `alembic >= 1.13`.
- OpenDAL added: `opendal >= 0.45`.
- Legacy asyncpg + psycopg + langgraph-checkpoint-postgres stay on
  the dependency list; `langgraph-checkpoint-sqlite` is in
  `optional-dependencies.sqlite` (tests / explicit sqlite path only).

## Round 2.1: user-editable small configs on OpenDAL

Round 2 only put the OpenDAL plumbing in place. Round 2.1 used it to
move the three "user edits this in the UI" file types off the local
filesystem so multi-instance deployments stop relying on the gateway
container's local volume:

| Data | Was at | Now at | Wired by |
|------|--------|--------|----------|
| `USER.md` (per-user profile) | `.deer-flow/users/{uid}/USER.md` | `user-profile/{uid|__global__}/USER.md` | `routers/agents.py:GET/PUT /api/agents/user-profile` |
| Custom agents | `.deer-flow/users/{uid}/agents/{name}/...` | `custom-agents/{uid|__global__}/{name}/{config.yaml,SOUL.md}` | `agents_config.{load_agent_config,load_agent_soul,list_custom_agents}` + `routers/agents.py` (POST/PUT/DELETE/check) |
| Per-user extensions override | `.deer-flow/users/{uid}/extensions_config.json` | `user-extensions/{uid}/extensions_config.json` | `routers/mcp.py` (`GET/PUT /api/mcp/...`), `routers/skills.py` (`PUT /api/skills/{name}`), `skills/loader.py` |

Key helpers landed in `deerflow.storage`:

```python
user_profile_key(user_id)
user_agents_prefix(user_id)
user_agent_prefix(user_id, agent_name)
user_agent_config_key(user_id, agent_name)
user_agent_soul_key(user_id, agent_name)
user_extensions_override_key(user_id)
GLOBAL_SCOPE  # "__global__" sentinel for None user_id
```

Two specific deltas worth calling out for future readers:

- The repo-level **public** `extensions_config.json` (`<repo>/extensions_config.json`)
  was deliberately left untouched. It is read at startup and shared
  by every user — moving it into per-user object storage would lose
  that semantic.
- `routers/agents.py` exposes the user-profile endpoints under
  `/api/agents/user-profile` (not `/api/user-profile`) so nginx's
  existing `/api/agents` location block proxies them to the gateway
  without an extra rule. The handlers must be declared before the
  catch-all `GET/PUT/DELETE /api/agents/{name}`; an inline comment in
  the file documents the ordering invariant.

Things explicitly deferred to the MinIO round:

- `uploads`, `outputs`, `workspace`, `acp-workspace` under
  `.deer-flow/users/{uid}/threads/{tid}/...` — these are bind-mounted
  into the sandbox container as `/mnt/user-data/...`. They cannot move
  to OpenDAL until the sandbox lifecycle is redesigned around
  pull-execute-push.
- `skills/custom/` — bind-mounted read-only into the sandbox so agents
  can `import` skill code by path.
- `FileMemoryStorage` and `FileChannelStore` fallback classes — kept
  importable for tests, never reached from the production
  configuration after Round 2.

Legacy `Paths` helpers carrying the per-user filesystem layout
(`user_md_file_for`, `user_agents_dir`, `user_agent_dir`,
`user_extensions_config_file`, plus the `resolve_*` siblings) gained
`.. deprecated:: Round 2.1` docstrings and are kept only for tests
that still construct fixture trees with raw `Path` objects. A future
PR will rewrite those fixtures against the OpenDAL operator and drop
the helpers outright.

## Legacy files (archived, NOT migrated)

Round 1 introduced per-subsystem one-shot archival blocks in the gateway
lifespan. Round 2 retires those blocks and consolidates everything into
a single sibling tree outside `backend/.deer-flow/`:

```text
backend/.deer-flow-legacy/
├── checkpoints.db.legacy          (4.1GB, ex-LangGraph sqlite)
├── checkpoints.db-wal.legacy
├── checkpoints.db-shm.legacy
├── users.db.legacy                (24KB)
├── cache/
│   └── academic_search.db.legacy  (816MB of S2/OpenAlex responses)
└── users/<uuid>/
    └── memory.json.legacy         (per-user memory snapshots)
```

`backend/.deer-flow/` now only holds live runtime data (sandbox
`threads/` workspaces, a per-user `users/<uuid>/threads/` tree, etc.).

Need to read the old data? `sqlite3 backend/.deer-flow-legacy/checkpoints.db.legacy`
still opens it read-only. Once you no longer need it,
`rm -rf backend/.deer-flow-legacy/` is the complete cleanup.

Reasoning behind the archive-and-forget choice:

- `checkpoints.db` rows would have to be replayed through the LangGraph
  Postgres saver's own version chain — not safe to bulk-copy.
- `users.db` is tiny; users re-register once.
- Memory and cache rebuild organically as agents run.
- Channel mappings rebuild the next time an IM message arrives.

Need to read the old data? `sqlite3 backend/.deer-flow-legacy/checkpoints.db.legacy`
still opens it read-only.

## Verification

Integration smoke (run inside the gateway container):

```bash
# Auth
curl -sS -X POST http://localhost:2026/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"x@example.com","username":"x1","password":"Abcdef123","display_name":"X"}'
psql "$POSTGRES_DSN" -c 'SELECT count(*) FROM users;'

# Memory
PYTHONPATH=/app/backend /app/backend/.venv/bin/python - <<'PY'
from deerflow.agents.memory.postgres_storage import PostgresMemoryStorage
s = PostgresMemoryStorage()
d = s.load("u1")
d["facts"].append({"id":"f1","content":"hi","category":"personal","confidence":1})
s.save(d, "u1")
assert s.reload("u1")["facts"][0]["content"] == "hi"
PY

# Tool cache
PYTHONPATH=/app/backend /app/backend/.venv/bin/python - <<'PY'
from deerflow.community.semantic_scholar.cache import get_sqlite_ttl_cache
c = get_sqlite_ttl_cache("ignored.db")
c.set("k", "tool", {"a":1}, ttl_seconds=60)
assert c.get("k") == {"a":1}
PY

# Channel store
PYTHONPATH=/app/backend /app/backend/.venv/bin/python - <<'PY'
from app.channels.store import ChannelStore, PostgresChannelStore
s = ChannelStore()
assert isinstance(s, PostgresChannelStore)
s.set_thread_id("slack","C","t",user_id="u")
assert s.get_thread_id("slack","C") == "t"
s.remove("slack","C")
PY
```

## Rolling back

Round 2 removed the runtime backend switches that Round 1 introduced
(`AUTH_REPOSITORY_BACKEND`, `DEERFLOW_TOOL_CACHE_BACKEND`,
`DEERFLOW_CHANNEL_STORE_BACKEND`, `repository_backend`). Rollback now
goes through `git revert` rather than configuration:

- Reverting commit `2a947827` brings the env-var switches back, in
  case you need to flip a single subsystem to its file/sqlite
  fallback temporarily.
- Reverting commit `b59af1a9` (the Round 1 baseline) restores the
  pre-migration SQLite + JSON setup. Combine with renaming
  `backend/.deer-flow-legacy/<file>.legacy` back to its original
  path under `backend/.deer-flow/` to recover the data.
- The `FileMemoryStorage` / `FileChannelStore` / `SQLiteTTLCache`
  classes are still importable for tests and local-only flows;
  setting `config.memory.storage_class =
  deerflow.agents.memory.storage.FileMemoryStorage` is enough to
  make memory fall back without a revert.
- LangGraph itself can be reverted by setting `checkpointer.type:
  sqlite` in `config.yaml` and reinstalling
  `langgraph-checkpoint-sqlite` from the optional dependency group.

Rolling back does NOT re-import archived data; rename
`<file>.legacy` back to the original name first.

## Operator cheatsheet

```bash
# Full dump (schema + data) — backup target for Phase 2+.
docker exec scientific-tumbleweed-paradedb \
  pg_dump -U scientifictumbleweed -d scientifictumbleweed > backup-$(date +%Y%m%d).sql

# Per-table row counts.
docker exec scientific-tumbleweed-paradedb psql -U scientifictumbleweed -d scientifictumbleweed -c "
  SELECT relname, n_live_tup AS live_rows
    FROM pg_stat_user_tables
   WHERE schemaname = 'public'
ORDER BY relname;"

# tool_cache manual vacuum (normally runs hourly from gateway).
psql "$POSTGRES_DSN" -c "DELETE FROM tool_cache WHERE expires_at <= NOW();"

# Regenerate docker/postgres/init.sql from SQLModel metadata
# after editing a model.
make emit-init-sql
make check-init-sql      # CI drift check

# Stamp Alembic at HEAD on a fresh database (init.sql already
# created the tables).
docker exec scientific-tumbleweed-gateway \
  /app/backend/.venv/bin/alembic -c /app/backend/alembic.ini stamp head
```
