# PostgreSQL Schema Reconnaissance

> 本文档记录 LangGraph 切到 PostgreSQL 后，由 `langgraph-checkpoint-postgres` / `langgraph.store.postgres` 自动创建的 schema，作为阶段 2+ 设计应用自建表时的对照参考。
>
> 生成时间：2026-05-11
> 环境：`paradedb/paradedb:0.23.4-pg18` + `langgraph-checkpoint-postgres>=3.0.3`
> LangGraph 版本：`1.0.x`（`langgraph>=1.0.6,<1.0.10`）

---

## 1. 容器与连接

| 项 | 值 |
|----|-----|
| 镜像 | `paradedb/paradedb:0.23.4-pg18`（PostgreSQL 16.13 + pgvector 0.8.1 + pg_search 0.23.2 + PostGIS 3.6.3） |
| DSN | `postgresql://scientifictumbleweed:scientifictumbleweed@paradedb:5432/scientifictumbleweed` |
| 容器名 | `scientific-tumbleweed-paradedb` |
| 初始化脚本 | `docker/postgres/init.sql`（幂等创建 `vector` / `pg_search` / `pg_stat_statements` 扩展） |

连通性验证：

```bash
docker exec scientific-tumbleweed-paradedb psql -U scientifictumbleweed -d scientifictumbleweed -c "\dx"
```

ParadeDB 镜像 bootstrap 完成后，以下扩展已预装可用：

| extname | version | 说明 |
|---------|---------|------|
| `vector` | 0.8.1 | pgvector，未来 embeddings / ANN 用 |
| `pg_search` | 0.23.2 | ParadeDB BM25 全文检索 |
| `pg_stat_statements` | 1.10 | 查询级可观测性 |
| `fuzzystrmatch` | 1.2 | 模糊匹配 |
| `pg_ivm` | 1.13 | 增量物化视图 |
| `postgis` / `postgis_topology` / `postgis_tiger_geocoder` | 3.6.3 | 空间扩展（暂未用） |

---

## 2. LangGraph 自动创建的表

切换 `checkpointer.type: postgres` 后，gateway 和 langgraph server 启动时会自动调用 `AsyncPostgresSaver.setup()` 与 `AsyncPostgresStore.setup()`，在默认的 `public` schema 幂等创建以下对象：

```text
public.checkpoints
public.checkpoint_blobs
public.checkpoint_writes
public.checkpoint_migrations
public.store
public.store_migrations
```

### 2.1 `checkpoints` — 主状态快照

```sql
CREATE TABLE public.checkpoints (
    thread_id           text NOT NULL,
    checkpoint_ns       text NOT NULL DEFAULT '',
    checkpoint_id       text NOT NULL,
    parent_checkpoint_id text,
    type                text,
    checkpoint          jsonb NOT NULL,
    metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT checkpoints_pkey
        PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
CREATE INDEX checkpoints_thread_id_idx ON public.checkpoints (thread_id);
```

- 每次 graph 节点完成、interrupt、resume 都会插入一行
- `checkpoint_ns` 用于 subgraph 命名空间（顶层 graph 为 `''`）
- `parent_checkpoint_id` 形成时间旅行链路
- `checkpoint` JSONB 是整个 channel_values 快照（消息列表、状态 dict 等）
- `metadata` JSONB 存 run 信息（source、step、writes）

**规模参考**：旧 SQLite 单库 4.1GB，主要就在这张表。Postgres + JSONB 的 TOAST 压缩后通常会小 30-60%。

### 2.2 `checkpoint_blobs` — 大对象拆分存储

```sql
CREATE TABLE public.checkpoint_blobs (
    thread_id      text NOT NULL,
    checkpoint_ns  text NOT NULL DEFAULT '',
    channel        text NOT NULL,
    version        text NOT NULL,
    type           text NOT NULL,
    blob           bytea,
    CONSTRAINT checkpoint_blobs_pkey
        PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);
CREATE INDEX checkpoint_blobs_thread_id_idx ON public.checkpoint_blobs (thread_id);
```

- 按 `channel`（LangGraph 中的状态字段）+ `version` 去重存储二进制负载
- `type` 标记序列化方式（`json` / `msgpack` / `pickle`）
- 命名"blobs"但存的是经过 `MSGPACK`/`pickle` 序列化后的 channel value

### 2.3 `checkpoint_writes` — 未提交写入

```sql
CREATE TABLE public.checkpoint_writes (
    thread_id      text NOT NULL,
    checkpoint_ns  text NOT NULL DEFAULT '',
    checkpoint_id  text NOT NULL,
    task_id        text NOT NULL,
    idx            integer NOT NULL,
    channel        text NOT NULL,
    type           text,
    blob           bytea NOT NULL,
    task_path      text NOT NULL DEFAULT '',
    CONSTRAINT checkpoint_writes_pkey
        PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
CREATE INDEX checkpoint_writes_thread_id_idx ON public.checkpoint_writes (thread_id);
```

- 在 checkpoint 被提交前，pending 的 state update 先入此表
- `task_id` + `idx` 保证同一节点多次写入的顺序
- 崩溃恢复时可根据这里重放尚未合并到 `checkpoints` 的写入

### 2.4 `checkpoint_migrations` — schema 版本

```sql
CREATE TABLE public.checkpoint_migrations (v integer PRIMARY KEY);
```

当前版本序列：`v = 0..9`（共 10 个已应用的迁移）。由 `AsyncPostgresSaver.setup()` 管理，**我们不要写入这张表**。

### 2.5 `store` — 长期记忆 / 命名空间 KV

```sql
CREATE TABLE public.store (
    prefix        text NOT NULL,
    key           text NOT NULL,
    value         jsonb NOT NULL,
    created_at    timestamptz DEFAULT CURRENT_TIMESTAMP,
    updated_at    timestamptz DEFAULT CURRENT_TIMESTAMP,
    expires_at    timestamptz,
    ttl_minutes   integer,
    CONSTRAINT store_pkey PRIMARY KEY (prefix, key)
);
CREATE INDEX store_prefix_idx    ON public.store (prefix text_pattern_ops);
CREATE INDEX idx_store_expires_at ON public.store (expires_at) WHERE (expires_at IS NOT NULL);
```

- 对应 `BaseStore` 接口：用 `prefix` 做命名空间（例：`("user", user_id, "memories")`）
- 支持 TTL：`expires_at` + 部分索引
- `store_prefix_idx` 用 `text_pattern_ops`，支持 `prefix LIKE 'user/%'` 形式的前缀扫描
- `CURRENT_TIMESTAMP` 默认值是**未带时区**字面量但列类型是 `timestamptz`，PG 会自动注入 session timezone

### 2.6 `store_migrations`

```sql
CREATE TABLE public.store_migrations (v integer PRIMARY KEY);
```

当前版本序列：`v = 0..3`（4 个已应用的迁移）。

### 2.7 表大小快照（刚 setup，空库）

```text
spatial_ref_sys        7144 kB   -- PostGIS 参考数据
store                    32 kB
store_migrations         24 kB
checkpoints              24 kB
checkpoint_blobs         24 kB
checkpoint_writes        24 kB
checkpoint_migrations    24 kB
```

`spatial_ref_sys` 是 PostGIS 自带的参考表，与 LangGraph 无关。本项目未使用空间功能，可忽略。

---

## 3. 关键设计观察（影响我们自建表的风格）

### 3.1 建表风格：`CREATE TABLE` 直接上，不带 IF NOT EXISTS
看 LangGraph 的 migration 文件会发现他们用**顺序编号的 DDL patch**（v0..v9），由 `setup()` 在启动时幂等跑。应用自建表我们**不模仿 v0..v9**，用 `CREATE TABLE IF NOT EXISTS` 足够：不需要多版本迁移链路。

### 3.2 主键策略：复合主键 + thread_id 单列索引
- 主键总是 `(thread_id, checkpoint_ns, checkpoint_id[, ...])` 复合
- 额外给 `thread_id` 单独建 btree 索引，支持"列出某 thread 所有 checkpoint"的查询
- **启发**：我们自建表如果有 `(user_id, key)` 这种业务复合键，可以考虑给 `user_id` 单独建索引

### 3.3 JSONB + bytea 混用
- 结构化字段（metadata、channel value snapshot）用 `jsonb`
- 大对象 / 序列化结果用 `bytea`
- **启发**：`user_memory.data` 用 JSONB 是对的；如果未来要放 embedding 向量，用 `vector(1536)`；如果要放序列化产物，才用 `bytea`

### 3.4 timestamptz + CURRENT_TIMESTAMP 默认值
- store 表统一用 `timestamptz`（带时区），默认值 `CURRENT_TIMESTAMP`
- **启发**：我们自建表所有时间列都用 `timestamptz`，默认 `NOW()` 或 `CURRENT_TIMESTAMP`，保持一致

### 3.5 部分索引（partial index）
- `idx_store_expires_at ON store (expires_at) WHERE (expires_at IS NOT NULL)` 只索引非空行
- **启发**：`tool_cache(expires_at)` 可以直接照抄这个模式，因为绝大多数缓存条目都会有 TTL

### 3.6 text_pattern_ops 索引
- `store_prefix_idx ON store (prefix text_pattern_ops)` 专门优化 `LIKE 'prefix%'` 查询
- **启发**：我们如果有前缀匹配场景（例：按 thread_id 前缀分页）可以用；否则默认 btree 已足够

### 3.7 扩展默认不启用
- LangGraph 自动创建的表里没有任何 extension 的使用
- pgvector / pg_search 得我们在自建表里显式 `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)` 或 `CREATE INDEX ... USING bm25` 来激活
- **启发**：阶段 2-5 暂不碰；未来做语义记忆搜索或文献全文搜索时再加

---

## 4. 我们自建表的设计建议（基于上述观察）

| 表 | 主键 | 关键列 | 索引 | 备注 |
|----|------|--------|------|------|
| `users` | `id text` | `email` / `username` / `oauth_provider` / `oauth_id` | `UNIQUE (email)` / `UNIQUE (username)` / `UNIQUE (oauth_provider, oauth_id) WHERE NOT NULL` | 迁移 `users.db`；保留同名字段 |
| `user_memory` | `user_id text` | `data jsonb` / `version int` / `updated_at timestamptz` | GIN on data | 乐观锁靠 version 列；`user_id='__global__'` 占位替代以前的 `.deer-flow/memory.json` |
| `tool_cache` | `cache_key text` | `tool_name` / `value_json jsonb` / `expires_at timestamptz` | 照抄 `idx_store_expires_at` 模式：`(expires_at) WHERE expires_at IS NOT NULL` + `(tool_name)` | 后台任务每小时清理过期行 |
| `channel_threads` | `key text` | `thread_id` / `user_id` / `updated_at timestamptz` | `(thread_id)` | 原 `app/channels/store.py` 的 JSON 文件平替 |

所有表都遵循：
- 时间列统一 `timestamptz DEFAULT NOW()`（或 `CURRENT_TIMESTAMP`）
- `updated_at` 列在应用层手动更新，不用 trigger，保持与 LangGraph 风格一致
- 幂等 DDL：`CREATE TABLE IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS`
- 建表逻辑集中到 `backend/packages/harness/deerflow/db/setup.py::ensure_schema()`，gateway lifespan 启动时调一次

---

## 5. 运维注意事项

### 5.1 collation version warning
第一次 `psql` 连进去会看到：

```
WARNING: database "scientifictumbleweed" has a collation version mismatch
DETAIL: The database was created using collation version 2.41,
        but the operating system provides version 2.36.
```

原因：paradedb 镜像的 glibc 与某些 psql client 不一致。无需处理；若报警恼人可运行 `ALTER DATABASE scientifictumbleweed REFRESH COLLATION VERSION;`。

### 5.2 Docker compose 网络一致性
ParadeDB 服务必须加入和 gateway/langgraph 相同的 project（`scientific-tumbleweed-dev`）。否则 compose 会尝试建新网络，与已有子网冲突并报 `Pool overlaps with other one on this address space`。

### 5.3 `LANGGRAPH_ALLOW_BLOCKING=1` / `BG_JOB_ISOLATED_LOOPS=true`
LangGraph 1.0.x 引入的 `blockbuster` 在 dev 模式下会拒绝 agent 代码中的同步 IO。目前应用里的 skills 扫描用了 `os.walk`（`ScandirIterator.__next__`），导致 run 启动就抛 `BlockingError`。

**这是应用层问题，不是 PG 迁移引入的**，但为了不阻塞验证侦察，临时在 `.env` 里打开了：

```env
LANGGRAPH_ALLOW_BLOCKING=1
BG_JOB_ISOLATED_LOOPS=true
```

**TODO**：识别并修复 `os.walk` / `os.scandir` 等同步调用（`asyncio.to_thread` 包一层），然后回滚这两个开关。此项与本阶段工作无关，另立 issue 跟踪。

### 5.4 查询侦察常用命令

```bash
# 列出所有表
docker exec scientific-tumbleweed-paradedb psql -U scientifictumbleweed -d scientifictumbleweed -c "\dt"

# 查看表 DDL
docker exec scientific-tumbleweed-paradedb pg_dump -U scientifictumbleweed -d scientifictumbleweed --schema-only -t public.checkpoints

# 查看索引
docker exec scientific-tumbleweed-paradedb psql -U scientifictumbleweed -d scientifictumbleweed -c "\di public.*"

# 查看迁移版本
docker exec scientific-tumbleweed-paradedb psql -U scientifictumbleweed -d scientifictumbleweed -c "SELECT v FROM checkpoint_migrations ORDER BY v; SELECT v FROM store_migrations ORDER BY v;"

# 表大小
docker exec scientific-tumbleweed-paradedb psql -U scientifictumbleweed -d scientifictumbleweed -c "SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class WHERE relkind='r' AND relnamespace=(SELECT oid FROM pg_namespace WHERE nspname='public') ORDER BY pg_total_relation_size(oid) DESC;"
```

---

## 6. 阶段 1 交付物清单

- [x] `docker/postgres/init.sql` — 幂等创建扩展
- [x] `docker-compose*.yaml` — 加 `paradedb` 服务（Round 2 pin 版本 `0.23.4-pg18`）
- [x] `.env.example` + `.env` — `POSTGRES_DSN` 等变量（Round 2 统一命名到 `scientifictumbleweed`）
- [x] `backend/packages/harness/pyproject.toml` — `langgraph-checkpoint-postgres` + `psycopg[binary,pool]` + `asyncpg`
- [x] `config.yaml` — `checkpointer.type: postgres` + `connection_string: $POSTGRES_DSN`
- [x] gateway + langgraph 正常启动并建 schema（10 个 checkpoint migration + 4 个 store migration 已应用）
- [x] 本文档（侦察报告）

下一步：阶段 2 — 迁移 `users.db` 到 `public.users` 表，参考本报告的风格（`CREATE TABLE IF NOT EXISTS` + `timestamptz` + 幂等）。
