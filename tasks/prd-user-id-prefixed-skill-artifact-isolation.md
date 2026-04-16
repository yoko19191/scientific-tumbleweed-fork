# PRD: 基于用户 ID 前缀的视图与 Skill Artifact 隔离

## 1. Introduction / Overview

当前系统已有登录认证、部分 per-user 路径能力，以及 thread 列表层面的 owner mapping，但隔离没有贯穿主交互链路。Memory、uploads、outputs、workspace、Skill 生成物、thread state 等资源仍可能通过全局 fallback、裸 `thread_id`、或直连 LangGraph 路径被跨用户访问或混显。

本需求要求实现更严格的用户隔离：**所有 thread 视图和交互必须绑定当前登录用户；所有 memory JSON 与 Skill Artifact 存储路径或键名必须以当前用户 ID 为前缀；不允许跨用户共享，也不允许默认 fallback 到全局资源。**

本 PRD 使用“用户 ID 前缀隔离”作为统一规则：

```text
{userID}: {resource-key-or-path}
```

其中 `userID` 必须来自后端认证上下文，不允许由客户端请求体、query 参数或 runtime config 自行声明。

## 2. Goals

- 当前用户只能看到、打开、更新、运行、上传、下载自己的 thread 和 artifact。
- Memory JSON、uploads、workspace、outputs、Skill artifact 等资源均以认证用户 ID 为前缀隔离。
- 移除用户资源访问中的全局 fallback 行为；认证用户缺失或资源未绑定时必须失败。
- Thread 渲染与交互不跨用户混显，包括侧边栏列表、聊天页、state/history、runs、uploads、artifacts。
- 提供清晰的迁移/清理策略，避免历史全局数据继续被新用户访问。

## 3. User Stories

### US-001: Thread 视图只显示当前用户数据

**Description:** 作为已登录用户，我只想看到自己的 thread 列表和当前对话内容，避免看到其他用户的历史记录或消息。

**Acceptance Criteria:**
- [ ] 用户 A 创建的 thread 不出现在用户 B 的 thread 列表中。
- [ ] 用户 B 直接访问用户 A 的 thread URL 时返回 404 或 403，不渲染任何 A 的消息。
- [ ] 前端切换账号后，当前 thread 视图被清空或重定向到当前用户可访问的 thread。
- [ ] React Query / LangGraph SDK 缓存 key 包含当前用户 ID 或在登出/切换用户时被清空。
- [ ] Verify in browser using dev-browser skill：两个隐私窗口分别登录不同用户，验证列表、详情、刷新页面后均不混显。

### US-002: Thread 交互绑定当前用户

**Description:** 作为已登录用户，我发起消息、继续运行、取消运行或恢复 state 时，系统只允许操作属于我的 thread。

**Acceptance Criteria:**
- [ ] 创建 thread 时，后端从认证上下文写入 owner，不接受客户端传入 owner。
- [ ] run create / stream / wait / join / cancel 都校验 `thread_id` 属于当前用户。
- [ ] get state / update state / history 都校验 `thread_id` 属于当前用户。
- [ ] 未绑定 owner 的 thread 在多用户模式下不可被任何普通用户访问。
- [ ] 跨用户访问统一返回 404 或 403，并且响应体不泄露 thread 是否存在。

### US-003: Memory JSON 按用户 ID 前缀隔离

**Description:** 作为已登录用户，我的长期记忆只应从我的用户前缀下读取和写入。

**Acceptance Criteria:**
- [ ] Memory API 必须使用 `@require_auth` 或等价依赖解析当前用户。
- [ ] Memory 文件路径或 key 使用认证用户 ID 前缀，例如 `{userID}: memory.json` 或 `{userID}: memory/{scope}.json`。
- [ ] `get_memory_data()`、`save()`、`reload()`、`clear()` 等路径在认证用户缺失时失败，不回退到全局 memory。
- [ ] Memory middleware 在 run 完成后写入当前用户前缀下的 memory。
- [ ] 用户 A 的 memory 内容不会注入到用户 B 的系统提示词中。

### US-004: Upload 与文件型 Skill Artifact 按用户 ID 前缀隔离

**Description:** 作为已登录用户，我上传的文件和 Skill 生成的文件只能被我的 thread 和我的账号访问。

**Acceptance Criteria:**
- [ ] Upload 保存路径包含用户 ID 前缀，不能仅依赖裸 `thread_id`。
- [ ] Artifact 下载接口在解析路径前先校验当前用户拥有该 thread。
- [ ] `/mnt/user-data/uploads`、`/mnt/user-data/workspace`、`/mnt/user-data/outputs` 对应的宿主机路径均落在用户前缀命名空间下。
- [ ] Skill 生成的 `.skill` 包、报告、图片、代码文件、转换后的 markdown 文件都继承同一用户前缀。
- [ ] 用户 B 知道用户 A 的 artifact URL 时，也无法下载 A 的文件。

### US-005: Custom Skill 与 Skill 配置按用户 ID 前缀隔离

**Description:** 作为已登录用户，我安装、编辑、启用或禁用的 Skill 不影响其他用户。

**Acceptance Criteria:**
- [ ] Installed custom skills 写入用户 ID 前缀命名空间。
- [ ] Skill enable/disable 状态读取和写入用户 ID 前缀命名空间。
- [ ] Custom skill history 按用户 ID 前缀隔离。
- [ ] Agent prompt 中注入的 available skills 只包含当前用户可见和启用的 Skill。
- [ ] 不再使用全局 custom skill helper 处理认证用户的 custom skill CRUD。

### US-006: 无全局 fallback

**Description:** 作为系统维护者，我希望所有认证用户资源访问都显式失败或显式迁移，不再静默落到全局目录。

**Acceptance Criteria:**
- [ ] 认证用户访问 memory / agents / profile / skills / uploads / artifacts 时，缺失 user ID 必须返回错误。
- [ ] 代码中不再存在认证用户路径的 `user_id=None -> global` 静默 fallback。
- [ ] 旧全局数据不会被新用户自动读取。
- [ ] 开发或单用户模式如需全局资源，必须通过显式配置开关启用，默认关闭。

## 4. Functional Requirements

### 4.1 认证与用户上下文

**FR-1:** 所有用户资源相关 Gateway 路由必须强制解析认证用户。

- 包括 threads、runs、memory、agents、user-profile、skills、mcp config、uploads、artifacts、suggestions。
- 可使用 `@require_auth`、FastAPI dependency、或中间件统一设置 `request.state.auth`。
- `AuthMiddleware` 只检查 cookie 存在是不够的；资源路由必须拿到已验证 user object。

**FR-2:** `user_id` 只能来自服务端认证上下文。

- 不接受客户端请求体中的 `user_id`。
- 不信任 `metadata.user_id`、`config.metadata.user_id`、`configurable.user_id` 等客户端可控字段。
- 后端构造 run config 时必须覆盖任何客户端提供的 user_id。

**FR-3:** 系统必须定义统一的用户资源前缀函数。

```python
def user_prefix(user_id: str) -> str:
    return f"{validate_user_id(user_id)}: "
```

- 所有资源 key 和逻辑路径必须复用该函数。
- `validate_user_id()` 必须防止路径穿越、空值和非法字符。
- 文件系统实现如需避免冒号或尾随空格兼容问题，必须保留逻辑前缀，并在物理路径层提供可逆或稳定映射；该映射不得改变隔离语义。

### 4.2 Thread 视图与交互隔离

**FR-4:** Thread 创建必须写入用户前缀 owner key。

- Store key 示例：`{userID}: thread:{thread_id}`。
- Thread metadata 中也应写入服务端认证用户 ID，便于审计和迁移。
- 已存在同名 thread 且 owner 不同，必须拒绝。

**FR-5:** Thread 列表查询必须只搜索当前用户前缀。

- 不允许扫描所有 thread 后在应用层弱过滤，除非底层 Store 不支持前缀查询且有明确性能保护。
- 返回给前端的数据结构必须保持与现有 `AgentThread[]` 兼容。

**FR-6:** Thread 详情、state、history、patch、delete 必须先做 owner check。

- owner check 必须发生在读取 checkpoint values 或 artifact 内容之前。
- 跨用户访问返回 404 或 403。
- 错误响应不得包含目标用户 ID、thread title、metadata、文件名等敏感信息。

**FR-7:** Runs API 必须校验当前用户拥有目标 thread。

- 覆盖 create、stream、wait、list、get、join、cancel、stream existing。
- `start_run()` 必须从认证上下文注入 `metadata.user_id`。
- 客户端传入的 user_id 必须被忽略或覆盖。

**FR-8:** 前端 thread 视图缓存必须按用户隔离。

- React Query keys 应包含当前 user id，或在 logout/login 切换时清空 thread/state/history/run 缓存。
- `useStream` 的 `reconnectOnMount` / sessionStorage key 必须避免跨用户复用 run id。
- 当前路由 thread_id 不属于当前用户时，应重定向到 `/workspace/chats` 或显示不可访问状态。

### 4.3 Memory JSON 隔离

**FR-9:** Memory storage 必须以用户 ID 前缀定位文件或 key。

- 逻辑 key 示例：`{userID}: memory.json`。
- 物理路径示例：`.deer-flow/users/{userID}: /memory.json` 或等价安全映射。
- 不允许认证用户读取 `.deer-flow/memory.json` 全局文件。

**FR-10:** Memory API 必须强制用户隔离。

- `GET /api/memory`
- `POST /api/memory/reload`
- `DELETE /api/memory`
- `POST /api/memory/facts`
- `PATCH /api/memory/facts/{fact_id}`
- `DELETE /api/memory/facts/{fact_id}`
- `GET /api/memory/export`
- `POST /api/memory/import`
- `GET /api/memory/status`

以上接口均必须读取当前用户前缀下的 memory。

**FR-11:** Memory prompt injection 必须使用 run owner 的 memory。

- Agent factory / middleware 必须接收服务端注入 user_id。
- 如果 run 没有有效 owner，memory injection 必须禁用并记录错误，不得读取全局 memory。

### 4.4 Skill Artifact 与 Upload 隔离

**FR-12:** 所有 thread-local filesystem 路径必须包含用户前缀。

覆盖：

- workspace
- uploads
- outputs
- acp-workspace
- converted markdown files
- generated skill archives
- generated reports/images/code/data files

逻辑路径示例：

```text
{userID}: threads/{thread_id}/user-data/uploads/{filename}
{userID}: threads/{thread_id}/user-data/outputs/{filename}
{userID}: threads/{thread_id}/acp-workspace/{filename}
```

**FR-13:** Sandbox mount 路径必须按用户前缀解析。

- 同一个 `thread_id` 在不同用户下不得映射到同一个宿主机目录。
- Sandbox 内仍可暴露 `/mnt/user-data/*`，但宿主机源路径必须包含用户前缀。
- Sandbox provider acquire/get/reconcile 必须使用用户前缀后的 thread identity，不能只用裸 `thread_id`。

**FR-14:** Artifact URL 解析必须校验用户所有权。

- `GET /api/threads/{thread_id}/artifacts/{path}` 必须先确认当前用户拥有 thread。
- `.skill/SKILL.md` 内部文件读取同样需要 owner check。
- Path traversal 防护继续保留。

**FR-15:** Upload API 必须校验用户所有权并写入用户前缀路径。

- `POST /api/threads/{thread_id}/uploads`
- `GET /api/threads/{thread_id}/uploads/list`
- `DELETE /api/threads/{thread_id}/uploads/{filename}`

以上接口必须拒绝跨用户访问。

### 4.5 Custom Skills 与 Skill 状态隔离

**FR-16:** Skill loader 必须接收当前 user_id。

- `load_skills(enabled_only=True, user_id=current_user_id)` 应成为认证路径默认行为。
- Agent prompt 中的 available skills 必须按当前用户加载，不得使用全局 enabled skills cache。

**FR-17:** Custom skill CRUD 必须使用用户前缀目录。

覆盖：

- list custom skills
- get custom skill content
- update custom skill
- delete custom skill
- history
- rollback
- install from `.skill`

**FR-18:** Skill enable/disable 状态必须写入用户前缀 config。

- 逻辑 key 示例：`{userID}: extensions_config.json`。
- 用户 A 禁用某个 Skill 不影响用户 B。

### 4.6 MCP 与其他配置型 Artifact

**FR-19:** MCP config 必须明确处理隔离策略。

- 默认：MCP server config 按用户前缀隔离。
- 若存在管理员级全局 MCP，必须区分 global read-only config 与 user-owned config。
- 普通用户不能读取其他用户 MCP headers、env、OAuth token、client secret。

**FR-20:** Agent config / USER.md 必须按用户前缀隔离。

- `/api/agents/*` 只读写当前用户前缀下的 agents。
- `/api/user-profile` 只读写当前用户前缀下的 USER.md。
- Agent factory 加载 SOUL.md 时必须使用 run owner user_id。

### 4.7 迁移与历史数据

**FR-21:** 禁止静默读取历史全局数据。

- `.deer-flow/memory.json`
- `.deer-flow/agents`
- `skills/custom`
- `extensions_config.json`
- `.deer-flow/threads/{thread_id}`

这些旧位置不得被认证用户自动读取。

**FR-22:** 提供明确迁移或清理策略。

- MVP 可选择清空历史全局数据并从零开始。
- 若需要迁移，必须要求管理员显式指定目标 user_id。
- 迁移工具必须输出迁移清单和跳过原因。

## 5. Non-Goals (Out of Scope)

- 不实现用户之间的 thread 分享或协作编辑。
- 不实现组织/团队级命名空间。
- 不实现细粒度 RBAC；本需求只要求用户级 owner 隔离。
- 不要求把 sandbox 内部显示路径从 `/mnt/user-data` 改为包含 userID；隔离重点在宿主机路径和 API 访问控制。
- 不要求保留旧全局 fallback 的兼容行为。
- 不要求迁移所有历史数据；可通过清理策略完成上线。

## 6. Design Considerations

### 6.1 前端体验

- 切换用户后，thread 列表、当前聊天、artifact 面板、uploads 状态必须刷新。
- 如果当前 URL 指向不可访问 thread，应显示“该对话不存在或无权访问”，并提供返回 workspace 的操作。
- 不应在 UI 中暴露其他用户的 thread title、metadata、文件名或运行状态。

### 6.2 错误语义

- 跨用户访问建议返回 404，避免泄露资源存在性。
- 认证缺失返回 401。
- 当前用户已认证但权限不足或资源不归属时，可返回 404 或 403，但同类接口必须保持一致。

### 6.3 Prefix 规范

用户给定的目标前缀为：

```text
userID: 
```

实施时必须明确区分：

- **逻辑 key 前缀**：用于 Store key、日志、审计、资源标识。
- **物理文件路径前缀**：用于本地 filesystem。若直接使用冒号和空格，需验证目标部署系统支持；否则必须定义稳定的转义策略，但不能改变“所有资源归入用户前缀命名空间”的语义。

## 7. Technical Considerations

### 7.1 需要重点改造的代码区域

- `backend/app/gateway/auth_middleware.py`
- `backend/app/gateway/authz.py`
- `backend/app/gateway/deps.py`
- `backend/app/gateway/routers/threads.py`
- `backend/app/gateway/routers/thread_runs.py`
- `backend/app/gateway/routers/runs.py`
- `backend/app/gateway/routers/uploads.py`
- `backend/app/gateway/routers/artifacts.py`
- `backend/app/gateway/routers/memory.py`
- `backend/app/gateway/routers/agents.py`
- `backend/app/gateway/routers/skills.py`
- `backend/app/gateway/routers/mcp.py`
- `backend/app/gateway/services.py`
- `backend/packages/harness/deerflow/config/paths.py`
- `backend/packages/harness/deerflow/agents/memory/*`
- `backend/packages/harness/deerflow/agents/lead_agent/*`
- `backend/packages/harness/deerflow/skills/*`
- `backend/packages/harness/deerflow/uploads/*`
- Sandbox providers and thread data middleware
- Frontend thread hooks and artifact/upload consumers

### 7.2 LangGraph routing requirement

如果主聊天仍默认直连 LangGraph Server，则 Gateway owner check 无法保护主路径。实现方必须选择一种策略：

- 将 `/api/langgraph/*` 切到 Gateway-compatible runs/thread endpoints，并在 Gateway 做 auth/owner check。
- 或为 LangGraph Server 配置等价认证和 owner check，确保所有 state/runs/history 都使用当前用户上下文。

不得保留“前端主聊天直连无认证 LangGraph，但旁路 Gateway 做列表过滤”的状态。

### 7.3 Cache 与并发

- Skill prompt cache 不能再是单一全局 enabled skills cache；必须按 user_id 分桶。
- Memory cache 必须按 user_id 前缀分桶。
- Sandbox acquire/release 的 key 必须包含用户前缀，避免不同用户同 thread_id 复用 sandbox。
- RunManager list/get/cancel 必须验证 run 对应 thread owner。

### 7.4 测试要求

必须新增跨用户隔离测试：

- 用户 A/B 各创建 thread，互不可见。
- 用户 B 访问 A 的 state/history/artifact/upload/run，返回 404/403。
- 用户 A/B memory 写入互不影响。
- 用户 A/B 安装同名 custom skill，内容互不覆盖。
- 用户 A/B 启用/禁用同一 public skill，状态互不影响。
- 用户 A/B 上传同名文件到不同 thread 或同 thread_id 命名空间，路径互不覆盖。
- 无 user_id 时不 fallback 到全局资源。

## 8. Success Metrics

- 100% 用户资源 API 均有认证用户解析或明确 public 标记。
- 100% thread state/history/runs/artifact/upload 访问均执行 owner check。
- 0 个认证用户资源路径使用全局 fallback。
- 跨用户 E2E 测试全部通过。
- 代码搜索中不存在认证主路径调用 `get_memory_data()`、`load_skills()`、`resolve_agent_dir()` 等函数但未传当前 user_id 的情况。

## 9. Open Questions

- `userID: ` 前缀是否必须作为真实文件名片段保留冒号和尾随空格，还是允许 filesystem-safe 编码但保持逻辑 key 为该格式？
- 跨用户访问统一返回 404 还是 403？
- 历史全局数据是直接清空，还是需要管理员显式迁移到某个用户？
- MCP 配置是否全部用户隔离，还是允许管理员维护只读全局 MCP 模板？
- IM channel 用户 ID 是否也纳入同一隔离体系，还是仅覆盖网页登录用户？

