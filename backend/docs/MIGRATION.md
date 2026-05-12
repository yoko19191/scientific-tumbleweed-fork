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

- `backend/packages/harness/deerflow/db/` — new module: async `asyncpg`
  pool singleton + `ensure_schema()`.
- `backend/app/gateway/auth/repositories/postgres.py` — new
  `PostgresUserRepository`. SQLite kept as an opt-in fallback
  (`AUTH_REPOSITORY_BACKEND=sqlite`).
- `backend/packages/harness/deerflow/agents/memory/postgres_storage.py` —
  new `PostgresMemoryStorage`. Uses `psycopg_pool.ConnectionPool` because
  the `MemoryStorage` interface is sync.
- `backend/packages/harness/deerflow/community/semantic_scholar/postgres_cache.py` —
  new `PostgresTTLCache`. `get_sqlite_ttl_cache()` now auto-selects
  Postgres when the DSN is resolvable and keeps the old name so existing
  call sites compile unchanged.
- `backend/app/channels/store.py` — split into `FileChannelStore` (legacy
  JSON) and `PostgresChannelStore`. Public `ChannelStore(path=None)`
  became a factory that defaults to Postgres.

### Config

- `config.yaml`: `checkpointer.type: postgres` + `connection_string: $POSTGRES_DSN`.
- `backend/packages/harness/deerflow/config/memory_config.py`:
  `storage_class` default flipped to `PostgresMemoryStorage`.
- `backend/packages/harness/deerflow/config/auth/config.py`: added
  `repository_backend: "postgres" | "sqlite"`, default `postgres`, readable
  from `AUTH_REPOSITORY_BACKEND` env var.

### Docker / env

- `docker/docker-compose.yaml` and `docker-compose-dev.yaml` gained a
  `paradedb` service with a healthcheck and a named volume (`paradedb_data`).
- `docker/postgres/init.sql` creates extensions on first run.
- `.env.example` documents `POSTGRES_DB / _USER / _PASSWORD / _HOST_PORT /
  _DSN`; `gateway` and `langgraph` `depends_on: paradedb: service_healthy`.

### Dependencies

- Added: `langgraph-checkpoint-postgres >= 3.0.3`,
  `psycopg[binary,pool] >= 3.2.0`, `asyncpg >= 0.30.0`.
- `langgraph-checkpoint-sqlite` moved out of core `dependencies` into
  `[project.optional-dependencies].sqlite` (kept for tests and the
  opt-in sqlite fallback).

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

Every migrated subsystem keeps its sqlite/file implementation as a
non-default fallback:

- `AUTH_REPOSITORY_BACKEND=sqlite` — route auth back to `users.db`.
- `config.memory.storage_class = deerflow.agents.memory.storage.FileMemoryStorage`
  — route memory back to JSON files.
- `DEERFLOW_TOOL_CACHE_BACKEND=sqlite` — force SQLite TTL cache (also
  auto-selected if DSN can't be resolved).
- `DEERFLOW_CHANNEL_STORE_BACKEND=file` — force JSON channel store.
- `checkpointer.type: sqlite` — reverts LangGraph's own persistence.

Rolling back does NOT re-import the archived data; rename
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
```
