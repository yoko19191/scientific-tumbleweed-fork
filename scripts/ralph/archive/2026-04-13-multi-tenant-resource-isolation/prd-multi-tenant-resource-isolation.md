# PRD: 多租户资源隔离（Phase 1.5）

## 1. 概述

在已完成的 Phase 1（Memory / Agents / Skills 文件系统隔离）基础上，补全剩余资源的多租户隔离：

- **Uploads & Artifacts**：按 `users/{user_id}/threads/{thread_id}/` 路径隔离
- **MCP 配置**：全局只读 + per-user 启用状态隔离（类比 Skills）
- **Memory status 端点**：修复漏传 `user_id` 的小 bug
- **assistants_compat**：修复 `list_custom_agents()` 未传 `user_id`

不涉及 PostgreSQL / MinIO 迁移，不涉及 threads owner_check 补全。

---

## 2. 目标

- 不同用户的上传文件和 agent 产出物在文件系统层面完全隔离
- 用户可以独立管理自己的 MCP 启用状态，不影响其他用户
- 消除已知的 `user_id` 漏传 bug，避免数据串台

---

## 3. User Stories

### US-001: Uploads 路径按用户隔离

**Description:** As a 登录用户, I want 我上传的文件存储在我自己的目录下, so that 其他用户无法访问我的上传文件。

**Acceptance Criteria:**
- [ ] 上传文件存储路径变为 `{base_dir}/users/{user_id}/threads/{thread_id}/uploads/`
- [ ] 未登录时（`user_id=None`）回退到原路径 `{base_dir}/threads/{thread_id}/user-data/uploads/`（兼容无 auth 模式）
- [ ] `POST /api/threads/{thread_id}/uploads` 使用新路径
- [ ] `GET /api/threads/{thread_id}/uploads/list` 使用新路径
- [ ] `DELETE /api/threads/{thread_id}/uploads/{filename}` 使用新路径
- [ ] sandbox 虚拟路径 `/mnt/user-data/uploads/` 仍然正确映射到新的物理路径
- [ ] `UploadsMiddleware` 读取上传文件列表时使用正确的 user-scoped 路径

### US-002: Artifacts 路径按用户隔离

**Description:** As a 登录用户, I want agent 生成的产出物存储在我自己的目录下, so that 其他用户无法访问我的 artifacts。

**Acceptance Criteria:**
- [ ] Artifacts 存储路径变为 `{base_dir}/users/{user_id}/threads/{thread_id}/outputs/`
- [ ] 未登录时回退到原路径 `{base_dir}/threads/{thread_id}/user-data/outputs/`
- [ ] `GET /api/threads/{thread_id}/artifacts/{path}` 能正确解析新路径
- [ ] sandbox 虚拟路径 `/mnt/user-data/outputs/` 仍然正确映射
- [ ] `.skill` 归档文件的内部路径解析不受影响

### US-003: Thread 目录初始化按用户隔离

**Description:** As a 系统, I want 在 thread 启动时按用户创建隔离目录, so that workspace / uploads / outputs 都在用户命名空间下。

**Acceptance Criteria:**
- [ ] `Paths.ensure_thread_dirs(thread_id, user_id=None)` 支持 `user_id` 参数
- [ ] 有 `user_id` 时创建 `users/{user_id}/threads/{thread_id}/` 下的子目录
- [ ] 无 `user_id` 时行为与现在完全一致（向后兼容）
- [ ] `ThreadDataMiddleware` 调用 `ensure_thread_dirs` 时传入 `user_id`
- [ ] `user_id` 从 run metadata 中提取（与 memory middleware 一致）

### US-004: MCP 配置全局只读 + per-user 启用状态

**Description:** As a 登录用户, I want 能看到所有 MCP 工具并控制哪些对我启用, so that 我的 MCP 偏好不影响其他用户。

**Acceptance Criteria:**
- [ ] `GET /api/mcp/config` 返回全局 MCP 服务器列表（不变）
- [ ] `PUT /api/mcp/config` 被移除或返回 403（普通用户不能修改全局配置）
- [ ] 新增 `PUT /api/mcp/servers/{name}/enabled` 端点，写入 per-user `extensions_config.json` 中的 `mcpServers.{name}.enabled` 字段
- [ ] per-user MCP 启用状态存储在 `{base_dir}/users/{user_id}/extensions_config.json`（与 skills 共用同一文件）
- [ ] 未登录时 `GET /api/mcp/config` 返回全局配置（不变）
- [ ] MCP 工具加载时合并全局配置 + per-user 启用状态覆盖

### US-005: 修复 memory/status 端点漏传 user_id

**Description:** As a 登录用户, I want `GET /api/memory/status` 返回我自己的记忆数据, so that 不会看到全局 fallback 数据。

**Acceptance Criteria:**
- [ ] `get_memory_status()` 接受 `request: Request` 参数
- [ ] 调用 `get_memory_data(user_id)` 而非 `get_memory_data()`
- [ ] 未登录时行为不变（`user_id=None` → 全局 fallback）

### US-006: 修复 assistants_compat 漏传 user_id

**Description:** As a 登录用户, I want assistants 列表只显示我自己创建的 custom agents, so that 不会看到其他用户的 agents。

**Acceptance Criteria:**
- [ ] `_list_assistants()` 改为接受 `user_id: str | None` 参数
- [ ] `list_custom_agents(user_id=user_id)` 传入 user_id
- [ ] `search_assistants` 和 `get_assistant_compat` 端点从 request 提取 user_id 并传入
- [ ] 未登录时行为不变（显示全局 agents）

---

## 4. 功能需求

### Paths 层扩展

**FR-1:** `Paths` 新增以下方法：
```python
def user_thread_dir(self, user_id: str, thread_id: str) -> Path
    # → {base_dir}/users/{user_id}/threads/{thread_id}/

def user_thread_uploads_dir(self, user_id: str, thread_id: str) -> Path
    # → {base_dir}/users/{user_id}/threads/{thread_id}/uploads/

def user_thread_outputs_dir(self, user_id: str, thread_id: str) -> Path
    # → {base_dir}/users/{user_id}/threads/{thread_id}/outputs/

def user_thread_workspace_dir(self, user_id: str, thread_id: str) -> Path
    # → {base_dir}/users/{user_id}/threads/{thread_id}/workspace/
```

**FR-2:** `Paths` 新增 resolve helpers（`user_id=None` 回退全局）：
```python
def resolve_uploads_dir(self, thread_id: str, user_id: str | None = None) -> Path
def resolve_outputs_dir(self, thread_id: str, user_id: str | None = None) -> Path
def resolve_workspace_dir(self, thread_id: str, user_id: str | None = None) -> Path
def resolve_thread_user_data_dir(self, thread_id: str, user_id: str | None = None) -> Path
```

**FR-3:** `ensure_thread_dirs(thread_id, user_id=None)` 支持 user_id，有 user_id 时在用户命名空间下创建目录。

**FR-4:** `resolve_virtual_path(thread_id, virtual_path, user_id=None)` 支持 user_id，解析到正确的物理路径。

**FR-5:** `delete_thread_dir(thread_id, user_id=None)` 支持 user_id，删除正确的目录。

### Uploads 路由

**FR-6:** `uploads.py` 所有端点加 `request: Request`，调用 `get_optional_user_id(request)` 获取 user_id，传入 `resolve_uploads_dir(thread_id, user_id)`。

**FR-7:** `uploads.py` 中 `sandbox_uploads` 路径（用于返回给前端的 path 字段）也使用新的 resolve 方法。

### Artifacts 路由

**FR-8:** `artifacts.py` 的 `get_artifact` 端点加 `request: Request`，调用 `get_optional_user_id(request)`。

**FR-9:** `path_utils.py` 的 `resolve_thread_virtual_path` 接受可选 `user_id` 参数，传入 `Paths.resolve_virtual_path`。

### ThreadDataMiddleware

**FR-10:** `ThreadDataMiddleware` 从 run config metadata 提取 `user_id`（与 `MemoryMiddleware` 一致），调用 `ensure_thread_dirs(thread_id, user_id)`。

### MCP 路由

**FR-11:** `GET /api/mcp/config` 合并全局 MCP 配置与 per-user 启用状态覆盖：
- 读取全局 `extensions_config.json` 的 `mcpServers`
- 读取 `users/{user_id}/extensions_config.json` 的 `mcpServers`（仅 `enabled` 字段）
- per-user 的 `enabled` 覆盖全局值

**FR-12:** `PUT /api/mcp/config` 返回 `403 Forbidden`，body: `{"detail": "Global MCP configuration is read-only. Use PUT /api/mcp/servers/{name}/enabled to manage per-user settings."}`

**FR-13:** 新增端点 `PUT /api/mcp/servers/{name}/enabled`：
- Request body: `{"enabled": bool}`
- 写入 `users/{user_id}/extensions_config.json` 的 `mcpServers.{name}.enabled`
- 未登录时返回 401
- server name 不存在于全局配置时返回 404

### Memory status

**FR-14:** `get_memory_status()` 加 `request: Request` 参数，调用 `get_optional_user_id(request)` 并传入 `get_memory_data(user_id)`。

### assistants_compat

**FR-15:** `_list_assistants(user_id=None)` 传入 user_id 给 `list_custom_agents()`。`search_assistants` 和 `get_assistant_compat` 从 request 提取 user_id。

---

## 5. Non-Goals（不在本次范围内）

- **不做** threads.py 的 owner_check 补全
- **不做** PostgreSQL / MinIO 迁移
- **不做** 存量数据迁移脚本（开发环境，手动清理）
- **不做** MCP 服务器的新增/删除（全局配置由管理员维护）
- **不做** RBAC / admin 权限区分（所有登录用户权限相同）
- **不做** ACP workspace 的 user 隔离（暂不涉及）

---

## 6. 技术考量

### 路径结构变更

新路径：
```
{base_dir}/
├── users/{user_id}/
│   ├── memory.json
│   ├── USER.md
│   ├── agents/{name}/
│   ├── skills/custom/{name}/
│   ├── extensions_config.json      ← 同时存 skills 和 mcp 启用状态
│   └── threads/{thread_id}/        ← 新增
│       ├── uploads/
│       ├── outputs/
│       └── workspace/
└── threads/{thread_id}/            ← 保留，无 auth 时 fallback
    └── user-data/
        ├── uploads/
        ├── outputs/
        └── workspace/
```

### sandbox 虚拟路径映射

sandbox 内部路径 `/mnt/user-data/uploads/` 不变，只有物理路径映射改变。`resolve_virtual_path` 需要知道 `user_id` 才能映射到正确的物理路径。

`user_id` 在 run 执行时通过 `config["metadata"]["user_id"]` 传递（已有机制），middleware 从这里读取。

### MCP per-user 启用状态

`extensions_config.json` 已经同时存储 `skills` 和 `mcpServers` 的启用状态。per-user 文件只需存储 `enabled` 覆盖，其他字段（command、args、env 等）始终从全局读取。

示例 per-user `extensions_config.json`：
```json
{
  "mcpServers": {
    "github": { "enabled": false }
  },
  "skills": {
    "my-skill": { "enabled": true }
  }
}
```

### 影响范围

| 文件 | 改动类型 |
|------|---------|
| `deerflow/config/paths.py` | 新增方法 |
| `deerflow/agents/middlewares/thread_data_middleware.py` | 传入 user_id |
| `app/gateway/routers/uploads.py` | 使用新 resolve 方法 |
| `app/gateway/routers/artifacts.py` | 加 request 参数 |
| `app/gateway/path_utils.py` | 加 user_id 参数 |
| `app/gateway/routers/mcp.py` | 重写 PUT，新增 per-user 端点 |
| `app/gateway/routers/memory.py` | 修复 status 端点 |
| `app/gateway/routers/assistants_compat.py` | 传入 user_id |

---

## 7. 成功标准

- 两个不同登录用户上传同名文件，互不覆盖，互不可见
- 用户 A 关闭某个 MCP server，用户 B 的 MCP 列表不受影响
- `GET /api/memory/status` 返回当前用户的记忆，不返回全局数据
- 无 auth 模式（`user_id=None`）下所有功能行为与改动前完全一致

---

## 8. Open Questions

- **sandbox 虚拟路径传递**：`resolve_virtual_path` 目前只接受 `thread_id`，需要在 artifacts 端点中同时传入 `user_id`。artifacts 端点的 `request` 对象可以提取 `user_id`，但需要确认 `path_utils.py` 的接口变更不影响其他调用方（目前只有 `artifacts.py` 调用）。
- **`host_sandbox_*` 方法**：`Paths` 中有一组 `host_sandbox_*` 方法用于 Docker volume mount，这些方法也需要对应的 user-scoped 版本，否则 AIO sandbox 模式下路径会错误。本次是否一并处理？（建议：一并处理，否则 AIO sandbox 模式会 broken）
