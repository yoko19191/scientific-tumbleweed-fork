# RFC 多租户实现路径追踪

## 概述

本文档追踪多租户隔离功能的完整实现路径，从认证模块到资源隔离再到存储层迁移。

---

## Phase 0: 认证模块（登录注册）

> **状态：TODO**
> **来源：上游 PR `feat/rfc-001-auth-module`**

### 后端

- [ ] JWT 认证模块（`app/gateway/auth/`）
  - `config.py` — JWT 配置管理（缺少密钥时自动生成 ephemeral secret）
  - `models.py` — User / UserResponse Pydantic 模型
  - `password.py` — bcrypt 密码哈希（async wrapper）
  - `jwt.py` — Token 编解码
  - `errors.py` — AuthErrorCode / TokenError 枚举
  - `repositories/base.py` — UserRepository 抽象接口
  - `repositories/sqlite.py` — SQLite 实现（init-once DDL）
  - `local_provider.py` — 本地认证 Provider
  - `providers.py` — AuthProvider ABC
- [ ] 认证路由（`app/gateway/routers/auth.py`）
  - `POST /api/v1/auth/register` — 用户注册（首个用户自动 admin）
  - `POST /api/v1/auth/login/local` — 用户登录（JWT HttpOnly cookie）
  - `POST /api/v1/auth/logout` — 用户登出
  - `POST /api/v1/auth/change-password` — 修改密码
  - `GET /api/v1/auth/me` — 获取当前用户
  - `GET /api/v1/auth/setup-status` — 初始化状态检查
- [ ] CSRF 防护（`app/gateway/csrf_middleware.py`）
  - Double Submit Cookie 模式
  - 所有 state-changing API 自动校验 `X-CSRF-Token`
- [ ] 权限系统（`app/gateway/authz.py`）
  - `AuthContext` — 认证上下文
  - `@require_auth` / `@require_permission` — 装饰器
  - Thread owner_check 隔离

### 前端

- [ ] `AuthProvider.tsx` — React Context（session check + 401 redirect）
- [ ] `fetcher.ts` — fetchWithAuth / getCsrfHeaders
- [ ] Login 页面（`/app/(auth)/login`）
- [ ] Account Settings 页面
- [ ] 所有 `core/*/api.ts` 的 state-changing fetch 携带 CSRF header

### 已知问题（上游 PR 中的）

- `loadMemory()` 和 `exportMemory()` 缺少 `credentials: "include"`
- 登出不清理 React Query 缓存和 localStorage
- localStorage key 没有按用户命名空间隔离
- Token 登出后不失效（不 bump `token_version`）
- 权限模型是扁平的——所有用户拥有全部权限，RBAC 标记为 Future Work

---

## Phase 1: 文件系统级资源隔离

> **状态：已完成 ✅**

在 `Paths` 类中新增 `user_id` 维度，所有资源路径通过 `resolve_*` 方法按用户隔离，`user_id=None` 时回退全局路径。

### 目录结构

```
{base_dir}/
├── users/{user_id}/
│   ├── memory.json                    # Per-user 记忆
│   ├── USER.md                        # Per-user 画像
│   ├── agents/{name}/                 # Per-user 自定义 Agent
│   │   ├── config.yaml
│   │   └── SOUL.md
│   ├── skills/custom/{name}/          # Per-user 安装的 Skill
│   │   └── SKILL.md
│   └── extensions_config.json         # Per-user Skill 启用状态
├── skills/public/                     # 全局共享 public skills（只读）
├── memory.json                        # 全局 fallback（无 auth 时）
├── USER.md                            # 全局 fallback
└── threads/{thread_id}/               # 已由 auth PR 通过 owner_check 隔离
```

### 已隔离资源

| 资源 | 隔离键 | 改动文件 |
|------|--------|----------|
| Memory | `user_id` | `storage.py`, `queue.py`, `updater.py`, `memory_middleware.py`, `memory.py`(router) |
| USER.md | `user_id` | `agents.py`(router) |
| Custom Agents | `user_id` | `agents_config.py`, `agents.py`(router), `agent.py`(factory) |
| Custom Skills | `user_id` | `loader.py`, `installer.py`, `skills.py`(router) |
| Skill 启用状态 | `user_id` | `loader.py`, `skills.py`(router) |
| Prompt 注入 | `user_id` | `prompt.py`, `client.py` |

### 桥接层

- `deps.py` — `get_optional_user_id(request)` 从 `request.state.auth` 提取 user_id
- `services.py` — `start_run()` 将 user_id 注入 run metadata，供 middleware 和 agent factory 读取

### 具体改动清单

#### 1a. Paths 层 ✅

`backend/packages/harness/deerflow/config/paths.py`：
- [x] 新增 `_SAFE_USER_ID_RE` 和 `_validate_user_id()` 校验函数
- [x] 新增 `user_dir(user_id)` → `{base_dir}/users/{user_id}/`
- [x] 新增 `user_memory_file(user_id)` → `{base_dir}/users/{user_id}/memory.json`
- [x] 新增 `user_md_file_for(user_id)` → `{base_dir}/users/{user_id}/USER.md`
- [x] 新增 `user_agents_dir(user_id)` / `user_agent_dir(user_id, name)`
- [x] 新增 `user_skills_custom_dir(user_id)` / `user_extensions_config_file(user_id)`
- [x] 新增 `resolve_memory_file(user_id=None)` / `resolve_user_md(user_id=None)` / `resolve_agents_dir(user_id=None)` / `resolve_agent_dir(name, user_id=None)` — 统一入口，`None` 回退全局
- [x] 更新类文档字符串中的目录结构说明

#### 1b. Memory 隔离 ✅

`backend/packages/harness/deerflow/agents/memory/storage.py`：
- [x] `MemoryStorage` 抽象类：`agent_name` 参数全部改为 `user_id: str | None = None`
- [x] `FileMemoryStorage`：去掉 `_validate_agent_name()`，`_get_memory_file_path(user_id)` 调用 `get_paths().resolve_memory_file(user_id)`
- [x] 缓存键从 `agent_name` 改为 `user_id`
- [x] 移除 `AGENT_NAME_PATTERN` 导入

`backend/packages/harness/deerflow/agents/memory/queue.py`：
- [x] `ConversationContext` dataclass：`agent_name` 字段改为 `user_id: str | None = None`
- [x] `MemoryUpdateQueue.add()`：`agent_name` 参数改为 `user_id`
- [x] `_process_queue()`：传递 `user_id` 给 `updater.update_memory()`

`backend/packages/harness/deerflow/agents/memory/updater.py`：
- [x] `_save_memory_to_file(data, user_id=None)` — 参数从 `agent_name` 改为 `user_id`
- [x] `get_memory_data(user_id=None)` / `reload_memory_data(user_id=None)` / `import_memory_data(data, user_id=None)` / `clear_memory_data(user_id=None)`
- [x] `create_memory_fact(..., user_id=None)` / `delete_memory_fact(fact_id, user_id=None)` / `update_memory_fact(..., user_id=None)`
- [x] `MemoryUpdater.update_memory(messages, thread_id, user_id=None, correction_detected)`

`backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py`：
- [x] `after_agent()` 中新增 user_id 提取逻辑：先从 `runtime.context.get("user_id")`，再从 `get_config().get("metadata", {}).get("user_id")`
- [x] `queue.add()` 调用传递 `user_id` 替代 `agent_name`
- [x] 更新 `__init__` 文档说明 `agent_name` 不再用于 memory scoping

`backend/packages/harness/deerflow/agents/lead_agent/prompt.py`：
- [x] `_get_memory_context(user_id=None)` — 参数从 `agent_name` 改为 `user_id`
- [x] `get_agent_soul(agent_name, user_id=None)` — 新增 `user_id` 参数
- [x] `_apply_prompt_via_builder(...)` / `apply_prompt_template(...)` / `_apply_legacy_prompt_template(...)` — 新增 `user_id` 关键字参数
- [x] 所有内部调用 `_get_memory_context` 和 `get_agent_soul` 传递 `user_id`

`backend/app/gateway/routers/memory.py`：
- [x] 导入 `Request` 和 `get_optional_user_id`
- [x] 所有端点（`get_memory`, `reload_memory`, `clear_memory`, `create_memory_fact_endpoint`, `delete_memory_fact_endpoint`, `update_memory_fact_endpoint`, `export_memory`, `import_memory`）加 `request: Request` 参数
- [x] 每个端点调用 `get_optional_user_id(request)` 并传递给 updater 函数

#### 1c. Agent 配置隔离 ✅

`backend/packages/harness/deerflow/config/agents_config.py`：
- [x] `load_agent_config(name, user_id=None)` — 使用 `get_paths().resolve_agent_dir(name, user_id)`
- [x] `load_agent_soul(agent_name, user_id=None)` — 使用 `get_paths().resolve_agent_dir(agent_name, user_id)`
- [x] `list_custom_agents(user_id=None)` — 扫描 `get_paths().resolve_agents_dir(user_id)`

`backend/packages/harness/deerflow/agents/lead_agent/agent.py`：
- [x] `make_lead_agent()` 从 `config["metadata"]` 提取 `user_id`
- [x] `load_agent_config(agent_name, user_id=user_id)` 传递 user_id
- [x] `apply_prompt_template(..., user_id=user_id)` 传递 user_id

`backend/packages/harness/deerflow/client.py`：
- [x] `apply_prompt_template(..., user_id=config.get("metadata", {}).get("user_id"))` 传递 user_id

`backend/app/gateway/routers/agents.py`：
- [x] 导入 `Request` 和 `get_optional_user_id`
- [x] `_agent_config_to_response(cfg, include_soul, user_id=None)` — 传递 user_id 给 `load_agent_soul`
- [x] 所有端点（`list_agents`, `check_agent_name`, `get_agent`, `create_agent_endpoint`, `update_agent`, `delete_agent`, `get_user_profile`, `update_user_profile`）加 `request: Request`
- [x] 每个端点调用 `get_optional_user_id(request)` 并使用 `get_paths().resolve_*` 方法

#### 1d. Skills 隔离 ✅

`backend/packages/harness/deerflow/skills/loader.py`：
- [x] `load_skills(..., user_id=None)` — 新增 `user_id` 参数
- [x] 有 `user_id` 时：public skills 从全局路径加载，custom skills 从 `get_paths().user_skills_custom_dir(user_id)` 加载
- [x] 有 `user_id` 时：enable/disable 状态从 `get_paths().user_extensions_config_file(user_id)` 读取

`backend/packages/harness/deerflow/skills/installer.py`：
- [x] `install_skill_from_archive(zip_path, *, skills_root=None, user_id=None)` — 新增 `user_id` 参数
- [x] 有 `user_id` 时安装到 `get_paths().user_skills_custom_dir(user_id)`

`backend/app/gateway/routers/skills.py`：
- [x] 导入 `Request` 和 `get_optional_user_id`
- [x] 所有端点（`list_skills`, `get_skill`, `update_skill`, `install_skill`）加 `request: Request`
- [x] `update_skill` 有 `user_id` 时写入用户级 `extensions_config.json`，无 `user_id` 时写入全局配置

#### 1e. Gateway 桥接层 ✅

`backend/app/gateway/deps.py`：
- [x] 新增 `get_optional_user_id(request: Request) -> str | None`
- [x] 从 `request.state.auth.user.id` 提取，auth 未启用时返回 `None`

`backend/app/gateway/services.py`：
- [x] `start_run()` 中调用 `get_optional_user_id(request)` 将 user_id 注入 run metadata
- [x] 确保 `build_run_config()` 将 metadata 中的 user_id 传递到 LangGraph 运行时

#### 1f. 测试更新 ✅

- [x] `tests/test_memory_storage.py` — `test_get_memory_file_path_agent` → `test_get_memory_file_path_user`，移除 `_validate_agent_name` 测试
- [x] `tests/test_memory_queue.py` — `ConversationContext` 和 `update_memory` 调用从 `agent_name` 改为 `user_id`
- [x] `tests/test_memory_router.py` — `update_memory_fact` 断言新增 `user_id=None`
- [x] `tests/test_custom_agent.py` — memory path 测试从 per-agent 改为 per-user
- [x] `tests/test_lead_agent_prompt.py` — mock lambda 签名新增 `user_id=None`
- [x] 167 个测试全部通过（2 个 pre-existing failure 与本次改动无关）

---

## Phase 2: PostgreSQL + MinIO 存储层迁移

> **状态：TODO**

将 Phase 1 的文件系统隔离替换为数据库 + 对象存储，支持水平扩展和多实例部署。

### 2a. PostgreSQL 替代文件存储

- [ ] Memory 存储迁移
  - 新建 `memory` 表：`(user_id, version, user_context, history, last_updated)`
  - 新建 `memory_facts` 表：`(id, user_id, content, category, confidence, created_at, source, source_error)`
  - 实现 `PostgresMemoryStorage(MemoryStorage)` 替代 `FileMemoryStorage`
  - 通过配置切换存储后端（`MEMORY_STORAGE=postgres` / `file`）

- [ ] Agent 配置迁移
  - 新建 `custom_agents` 表：`(user_id, name, description, model, tool_groups, soul_md, created_at, updated_at)`
  - 修改 `agents_config.py` 支持 DB 后端

- [ ] User Profile 迁移
  - 新建 `user_profiles` 表：`(user_id, content_md, updated_at)`
  - 或直接在 `users` 表中加 `profile_md` 列

- [ ] Skill 启用状态迁移
  - 新建 `user_skill_states` 表：`(user_id, skill_name, enabled)`
  - 替代 per-user `extensions_config.json`

- [ ] 用户认证表迁移
  - 将上游 PR 的 SQLite `users` 表迁移到 PostgreSQL
  - 复用同一个 PostgreSQL 实例

### 2b. MinIO 替代文件存储

- [ ] Custom Skills 文件存储
  - Bucket: `skills`，Key: `users/{user_id}/custom/{skill_name}/SKILL.md`
  - Public skills 保持本地文件系统（只读，随代码部署）

- [ ] Thread 用户数据
  - Bucket: `thread-data`，Key: `{thread_id}/user-data/{workspace|uploads|outputs}/...`
  - 替代当前的 `{base_dir}/threads/{thread_id}/user-data/`

- [ ] Agent SOUL.md 文件
  - 可选：小文件可直接存 PostgreSQL `text` 列
  - 大文件或需要版本管理时存 MinIO

### 2c. 迁移策略

- [ ] 编写数据迁移脚本 `scripts/migrate_to_postgres.py`
  - 读取 `users/*/memory.json` → 写入 `memory` + `memory_facts` 表
  - 读取 `users/*/agents/*/config.yaml` → 写入 `custom_agents` 表
  - 读取 `users/*/USER.md` → 写入 `user_profiles` 表
- [ ] 支持双写模式过渡期（同时写文件和 DB，读优先 DB）
- [ ] 环境变量控制存储后端：`STORAGE_BACKEND=file|postgres+minio`

---

## Phase 3: 团队/项目隔离（后续扩展）

> **状态：设计预留**

### 目标

- 团队内共享 Skills
- 项目内共享统一上下文

### 预留扩展点

```
{base_dir}/
├── users/{user_id}/          # ← Phase 1 已实现
├── teams/{team_id}/          # ← 未来：团队共享 skills
│   └── skills/custom/
├── projects/{project_id}/    # ← 未来：项目共享上下文
│   └── context/
```

PostgreSQL 表设计预留：

```sql
-- 团队
CREATE TABLE teams (id, name, created_by, created_at);
CREATE TABLE team_members (team_id, user_id, role, joined_at);

-- 项目
CREATE TABLE projects (id, team_id, name, created_by, created_at);
CREATE TABLE project_members (project_id, user_id, role);

-- 团队共享 skills
CREATE TABLE team_skills (team_id, skill_name, installed_by, created_at);

-- 项目共享上下文
CREATE TABLE project_context (project_id, context_md, updated_at);
```

`Paths.resolve_*` 方法未来可扩展为接受 `team_id` / `project_id` 参数，合并多层级数据源。
