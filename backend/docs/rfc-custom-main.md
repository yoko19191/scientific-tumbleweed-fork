# 多租户资源隔离实现计划

## Context

上游 PR `feat/rfc-001-auth-module` 提供了 JWT 认证 + Thread 级 owner_check 隔离，但 memory、agents、skills、user profile 等非 Thread 资源完全没有隔离——所有用户共享同一份数据。本计划在该 PR 基础上补齐 per-user 资源隔离层。

**用户决策**：
- Memory 仅按 `user_id` 隔离（去掉 per-agent memory 概念）
- Custom skills + 启用状态都按用户隔离
- 存储采用文件系统目录隔离 `users/{user_id}/`

**核心设计原则**：
- `Paths` 类是所有文件路径的唯一出口——在这里加 `user_id` 维度，下游自动获得隔离
- harness 层只接受 `user_id: str | None` 参数，不依赖 gateway auth
- `user_id=None` 时回退到全局路径，保持无 auth 场景兼容
- gateway 层负责从 request 提取 user_id 并传递给 harness

## 目标目录结构

```
{base_dir}/
├── users/{user_id}/
│   ├── memory.json                    # Per-user memory
│   ├── USER.md                        # Per-user profile
│   ├── agents/{name}/                 # Per-user custom agents
│   │   ├── config.yaml
│   │   └── SOUL.md
│   ├── skills/custom/{name}/          # Per-user installed skills
│   │   └── SKILL.md
│   └── extensions_config.json         # Per-user skill/MCP enable state
├── skills/public/                     # 全局共享 public skills（只读）
├── memory.json                        # 全局 fallback（无 auth 时）
├── USER.md                            # 全局 fallback
└── threads/{thread_id}/               # 已由 auth PR 通过 owner_check 隔离
```

---

## Phase 1: Paths 层 — 用户作用域路径解析

### 1a. 修改 `backend/packages/harness/deerflow/config/paths.py`

新增 user-scoped 方法（保留原有方法作为全局 fallback）：

```python
# 新增方法
def user_dir(self, user_id: str) -> Path:
    """用户数据根目录: {base_dir}/users/{user_id}/"""
    self._validate_user_id(user_id)
    return self.base_dir / "users" / user_id

def user_memory_file(self, user_id: str) -> Path:
    """用户记忆文件: {base_dir}/users/{user_id}/memory.json"""
    return self.user_dir(user_id) / "memory.json"

def user_md_file_for(self, user_id: str) -> Path:
    """用户 profile: {base_dir}/users/{user_id}/USER.md"""
    return self.user_dir(user_id) / "USER.md"

def user_agents_dir(self, user_id: str) -> Path:
    return self.user_dir(user_id) / "agents"

def user_agent_dir(self, user_id: str, agent_name: str) -> Path:
    return self.user_agents_dir(user_id) / agent_name

def user_skills_custom_dir(self, user_id: str) -> Path:
    return self.user_dir(user_id) / "skills" / "custom"

def user_extensions_config_file(self, user_id: str) -> Path:
    return self.user_dir(user_id) / "extensions_config.json"

def resolve_memory_file(self, user_id: str | None = None) -> Path:
    """统一入口：有 user_id 返回用户路径，否则返回全局路径"""
    if user_id:
        return self.user_memory_file(user_id)
    return self.memory_file

def resolve_user_md(self, user_id: str | None = None) -> Path:
    if user_id:
        return self.user_md_file_for(user_id)
    return self.user_md_file

def resolve_agents_dir(self, user_id: str | None = None) -> Path:
    if user_id:
        return self.user_agents_dir(user_id)
    return self.agents_dir

def resolve_agent_dir(self, name: str, user_id: str | None = None) -> Path:
    if user_id:
        return self.user_agent_dir(user_id, name)
    return self.agent_dir(name)

# 新增验证
def _validate_user_id(self, user_id: str) -> None:
    if not user_id or not re.match(r'^[A-Za-z0-9_\-]+$', user_id):
        raise ValueError(f"Invalid user_id: {user_id!r}")
```

---

## Phase 2: Memory 隔离

### 2a. 修改 `backend/packages/harness/deerflow/agents/memory/storage.py`

- `_get_memory_file_path(agent_name)` → `_get_memory_file_path(user_id: str | None = None)`
- 去掉 `agent_name` 参数，改用 `user_id`
- Cache key 从 `agent_name` 改为 `user_id`（None = 全局）
- `load(user_id=None)`, `save(data, user_id=None)`, `reload(user_id=None)`

```python
def _get_memory_file_path(self, user_id: str | None = None) -> Path:
    return get_paths().resolve_memory_file(user_id)
```

### 2b. 修改 `backend/packages/harness/deerflow/agents/memory/queue.py`

- `ConversationContext` 新增 `user_id: str | None = None` 字段
- `MemoryUpdateQueue.add()` 新增 `user_id` 参数
- 去掉 `agent_name` 参数（不再需要 per-agent memory）
- 处理函数将 `user_id` 传递给 `MemoryUpdater.update_memory()`

### 2c. 修改 `backend/packages/harness/deerflow/agents/memory/updater.py`

- `update_memory()` 签名：去掉 `agent_name`，加 `user_id: str | None = None`
- 内部 `storage.load(user_id=user_id)` / `storage.save(data, user_id=user_id)`

### 2d. 修改 `backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py`

- `after_invoke()` 中从 runtime context 提取 `user_id`：
  ```python
  user_id = None
  if runtime and runtime.context:
      user_id = runtime.context.get("user_id")
  if user_id is None:
      config_data = get_config()
      user_id = config_data.get("metadata", {}).get("user_id")
  ```
- 传递给 `queue.add(thread_id=..., messages=..., user_id=user_id, ...)`

### 2e. 修改 `backend/packages/harness/deerflow/agents/lead_agent/prompt.py`

- `_get_memory_context(agent_name)` → `_get_memory_context(user_id: str | None = None)`
- 内部调用 `get_memory_data(user_id=user_id)` 替代 `get_memory_data(agent_name)`

### 2f. 修改 `backend/app/gateway/routers/memory.py`

- 所有端点加 `@require_auth` 装饰器
- 从 `request.state.auth` 提取 `user_id = str(auth.user.id)`
- 传递 `user_id` 给所有 updater 函数调用

### 2g. 修改前端 `frontend/src/core/memory/api.ts`

- `loadMemory()` 和 `exportMemory()` 补上 `credentials: "include"`

---

## Phase 3: Agent 配置隔离

### 3a. 修改 `backend/packages/harness/deerflow/config/agents_config.py`

- `load_agent_config(name, user_id=None)` — 使用 `get_paths().resolve_agent_dir(name, user_id)`
- `load_agent_soul(name, user_id=None)` — 同上
- `list_custom_agents(user_id=None)` — 扫描 `get_paths().resolve_agents_dir(user_id)`

### 3b. 修改 `backend/app/gateway/routers/agents.py`

- 所有端点加 `@require_auth`
- 从 request 提取 `user_id`
- CRUD 操作使用 `get_paths().resolve_agent_dir(name, user_id)` 替代 `get_paths().agent_dir(name)`
- `GET/PUT /api/user-profile` 使用 `get_paths().resolve_user_md(user_id)`

### 3c. 修改 agent factory / lead_agent

- `backend/packages/harness/deerflow/agents/lead_agent/agent.py` 或 factory 函数
- 从 LangGraph configurable 中提取 `user_id`，传递给 `load_agent_config()` 和 `load_agent_soul()`
- 传递给 `_get_memory_context(user_id=user_id)`

---

## Phase 4: Skills 隔离

### 4a. 修改 `backend/packages/harness/deerflow/config/paths.py`（已在 Phase 1 完成）

### 4b. 修改 `backend/packages/harness/deerflow/skills/loader.py`

- `load_skills(user_id=None)` — 当 `user_id` 存在时：
  - public skills 仍从全局 `{skills_root}/public/` 加载
  - custom skills 从 `get_paths().user_skills_custom_dir(user_id)` 加载
  - enable/disable 状态从 `get_paths().user_extensions_config_file(user_id)` 读取

### 4c. 修改 `backend/packages/harness/deerflow/skills/installer.py`

- `install_skill(archive_path, user_id=None)` — 安装到用户目录
- 目标路径：`get_paths().user_skills_custom_dir(user_id) / skill_name`

### 4d. 修改 `backend/packages/harness/deerflow/config/extensions_config.py`

- `ExtensionsConfig.from_file()` 支持 `user_id` 参数
- 有 `user_id` 时读取 `get_paths().user_extensions_config_file(user_id)`
- `is_skill_enabled(name, category, user_id=None)` — 按用户查询
- `save()` 方法支持写入用户级配置文件

### 4e. 修改 `backend/app/gateway/routers/skills.py`

- 所有端点加 `@require_auth`
- 从 request 提取 `user_id`
- 传递给 loader/installer/config 函数

---

## Phase 5: Gateway 桥接层

### 5a. 修改 `backend/app/gateway/services.py`

- `build_run_config()` 已经注入 `config["metadata"]["user_id"]`（auth PR 已做）
- 确认 `user_id` 同时注入到 `config["configurable"]["user_id"]`，使 middleware 可通过 configurable 访问

### 5b. 确认 `backend/app/gateway/routers/threads.py`

- auth PR 的 `create_thread` 已将 `user_id` 写入 thread metadata
- 确认 `user_id` 也传入 run config 的 configurable，使 memory middleware 可提取

---

## Phase 6: 迁移与兼容

### 6a. 数据迁移脚本

创建 `backend/scripts/migrate_user_data.py`：
- 读取现有全局 `memory.json`、`USER.md`、`agents/` 目录
- 如果只有一个用户（首个 admin），将数据复制到 `users/{admin_id}/` 下
- 如果有多个用户，将全局数据复制给 admin 用户，其他用户从空白开始
- 幂等执行（检查目标是否已存在）

### 6b. 匿名/无 auth 回退

所有 `user_id=None` 的调用自动使用全局路径，行为与当前完全一致。这保证：
- 开发环境不开 auth 时正常工作
- 单用户部署不受影响

---

## 实现顺序（依赖关系）

```
Phase 1 (Paths)
  └→ Phase 2 (Memory)     ← 依赖 Paths 的 resolve_memory_file
  └→ Phase 3 (Agents)     ← 依赖 Paths 的 resolve_agent_dir
  └→ Phase 4 (Skills)     ← 依赖 Paths 的 user_skills_custom_dir
Phase 5 (Gateway bridge)  ← 依赖 Phase 2-4 的新签名
Phase 6 (Migration)       ← 最后执行
```

Phase 2/3/4 之间无依赖，可并行实施。

---

## 关键文件清单

| 文件 | 改动类型 | Phase |
|------|---------|-------|
| `backend/packages/harness/deerflow/config/paths.py` | 新增 user-scoped 方法 | 1 |
| `backend/packages/harness/deerflow/agents/memory/storage.py` | agent_name → user_id | 2a |
| `backend/packages/harness/deerflow/agents/memory/queue.py` | 新增 user_id 字段 | 2b |
| `backend/packages/harness/deerflow/agents/memory/updater.py` | agent_name → user_id | 2c |
| `backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py` | 提取 user_id | 2d |
| `backend/packages/harness/deerflow/agents/lead_agent/prompt.py` | agent_name → user_id | 2e |
| `backend/app/gateway/routers/memory.py` | 加 auth + user_id | 2f |
| `frontend/src/core/memory/api.ts` | 补 credentials | 2g |
| `backend/packages/harness/deerflow/config/agents_config.py` | 加 user_id 参数 | 3a |
| `backend/app/gateway/routers/agents.py` | 加 auth + user_id | 3b |
| `backend/packages/harness/deerflow/agents/lead_agent/agent.py` | 传递 user_id | 3c |
| `backend/packages/harness/deerflow/skills/loader.py` | 加 user_id 参数 | 4b |
| `backend/packages/harness/deerflow/skills/installer.py` | 安装到用户目录 | 4c |
| `backend/packages/harness/deerflow/config/extensions_config.py` | per-user config | 4d |
| `backend/app/gateway/routers/skills.py` | 加 auth + user_id | 4e |
| `backend/app/gateway/services.py` | 确认 user_id 注入 | 5a |
| `backend/scripts/migrate_user_data.py` | 新建迁移脚本 | 6a |

---

## 验证策略

1. **单元测试**：每个 Phase 完成后运行现有测试，确认 `user_id=None` 回退不破坏现有行为
2. **隔离测试**：
   - 用户 A 创建 memory fact → 用户 B 的 `/api/memory` 不可见
   - 用户 A 创建 agent → 用户 B 的 `/api/agents` 列表不包含
   - 用户 A 安装 skill → 用户 B 的 `/api/skills` 不包含该 custom skill
   - 用户 A 启用 public skill → 用户 B 的该 skill 状态不受影响
3. **端到端**：启动服务，注册两个用户，分别操作 memory/agents/skills，验证完全隔离
4. **回退测试**：关闭 auth（`AUTH_ENABLED=false`），验证所有功能使用全局路径正常工作

## 团队/项目隔离预留

目录结构预留扩展点：
```
{base_dir}/
├── users/{user_id}/          # ← 本次实现
├── teams/{team_id}/          # ← 未来：团队共享 skills
│   └── skills/custom/
├── projects/{project_id}/    # ← 未来：项目共享上下文
│   └── context/
```

Paths 类的 `resolve_*` 方法未来可扩展为接受 `team_id` / `project_id` 参数，合并多层级数据源。
