# PRD: 多租户 Thread 隔离 + 用户信息/登出 UI

## 1. Introduction / Overview

当前系统登录注册功能正常，但 **thread 数据没有按用户隔离**——所有用户共享同一个 thread 列表。此外，登录后 UI 缺少用户身份展示和登出功能。

本 PRD 采用**最小侵入的映射层方案**：在 Gateway 和 LangGraph API 之间维护一张 `user_id ↔ thread_id` 映射表，不改动 LangGraph Server 的任何配置和行为。

### 核心设计原则

- **LangGraph Server 保持 `auth=noop`**，继续作为底层执行引擎（checkpointer、runs、streaming 原生能力不受影响）
- **不修改全局 fetch**，不切换 apiUrl，前端大部分操作继续直连 LangGraph API
- **Gateway 只负责三件事**：注册映射（thread 创建时）、按用户过滤列表、删除映射（thread 删除时）
- **已有历史数据清空重来**

---

## 2. Goals

- Thread 列表仅展示当前登录用户创建的 thread
- 新 thread 创建时自动注册到当前用户名下
- Thread 删除时同步清理映射记录
- 侧边栏底部显示当前用户邮箱 + 登出按钮
- 改动范围最小化

---

## 3. User Stories

### US-001: Thread 列表按用户隔离

**Description:** 作为已登录用户，侧边栏历史记录只显示我自己创建的 thread。

**Acceptance Criteria:**
- [ ] 用户 A 创建的 thread 不出现在用户 B 的侧边栏
- [ ] 新注册用户登录后，侧边栏历史记录为空
- [ ] **[UI]** 两个隐私窗口分别登录不同用户，验证 thread 互不可见

### US-002: Thread 创建时自动注册归属

**Description:** 作为已登录用户，发起新对话时系统自动将 thread 关联到我的账户。

**Acceptance Criteria:**
- [ ] 新 thread 在 `useStream.onCreated` 回调中向 Gateway 注册 `user_id ↔ thread_id` 映射
- [ ] 映射注册失败不阻塞对话流程（静默失败 + console.error）
- [ ] 映射数据持久化在 Gateway 的 SQLite Store 中

### US-003: Thread 删除时清理映射

**Description:** 作为已登录用户，删除 thread 时同步清理映射记录。

**Acceptance Criteria:**
- [ ] 现有的 `useDeleteThread` 中调用 Gateway `DELETE /api/threads/{thread_id}` 时，同步删除映射记录
- [ ] 映射删除是幂等的（重复删除不报错）

### US-004: 侧边栏显示当前用户信息

**Description:** 作为已登录用户，在侧边栏底部看到我的邮箱。

**Acceptance Criteria:**
- [ ] 侧边栏底部显示当前用户邮箱
- [ ] 侧边栏折叠时显示邮箱首字母圆形头像
- [ ] **[UI]** 浏览器中验证登录后能看到正确邮箱

### US-005: 登出功能

**Description:** 作为已登录用户，有登出按钮可以退出会话。

**Acceptance Criteria:**
- [ ] 侧边栏底部 DropdownMenu 中有"退出登录"菜单项
- [ ] 点击后调用 `POST /api/v1/auth/logout`，清除 cookie，跳转到 `/login`
- [ ] **[UI]** 浏览器中验证登出流程完整可用

---

## 4. Functional Requirements

### 4.1 后端：Gateway 映射层 API

**FR-1:** 新增 Gateway 端点 `POST /api/threads/bindUser`，用于注册 `user_id ↔ thread_id` 映射。

```
POST /api/threads/bindUser
Content-Type: application/json
Cookie: access_token=...
X-CSRF-Token: ...

{ "thread_id": "xxx-xxx-xxx" }
```

- 使用 `@require_auth` 装饰器从 JWT cookie 提取 `user_id`
- 将映射写入 Store（namespace `("thread_owners",)`），key 为 `thread_id`，value 为 `{"user_id": "...", "created_at": ...}`
- 幂等：如果映射已存在且 `user_id` 相同，直接返回成功
- 返回 `{"success": true}`

**FR-2:** 新增 Gateway 端点 `GET /api/threads/listByUser`，返回当前用户拥有的 thread 列表。

```
GET /api/threads/listByUser
Cookie: access_token=...
```

- 使用 `@require_auth` 装饰器提取 `user_id`
- 从 Store 中查询 namespace `("thread_owners",)` 下所有 `user_id` 匹配的记录，获取 `thread_id` 列表
- 对每个 `thread_id`，从 checkpointer 读取最新 checkpoint 获取 thread 元数据（`title`、`updated_at`、`status`）
- 返回格式与 LangGraph `threads.search` 兼容的 `Thread[]` 数组，使前端可以直接使用
- 按 `updated_at` 降序排列

**FR-3:** 修改现有 `DELETE /api/threads/{thread_id}` 端点，在删除本地 thread 数据的同时删除映射记录。

- 在现有的 `delete_thread_data()` 函数中增加：`await store.adelete(("thread_owners",), thread_id)`
- 不需要额外鉴权（该端点已通过 `fetchWithAuth` 调用，带有 cookie）
- 但需要添加 `@require_auth` 并校验映射中的 `user_id` 与当前用户一致（防止用户删除他人 thread 的本地数据）

### 4.2 前端：Thread 列表改为调用 Gateway API

**FR-4:** 修改 `useThreads()` hook（`frontend/src/core/threads/hooks.ts`），将 thread 列表查询从 `apiClient.threads.search()` 改为调用 Gateway 的 `GET /api/threads/listByUser`。

```typescript
// 改前：直连 LangGraph API
const response = await apiClient.threads.search<AgentThreadState>(params);

// 改后：调用 Gateway（带 cookie 鉴权）
const response = await fetchWithAuth(`${getBackendBaseURL()}/api/threads/listByUser`);
const threads = await response.json();
```

- 使用 `fetchWithAuth`（已有，自动携带 cookie + CSRF）
- 返回数据格式需与现有 `AgentThread[]` 类型兼容
- 保留 TanStack Query 的 `queryKey: ["threads", "search"]` 不变，确保 `invalidateQueries` 正常工作

**FR-5:** 修改 `useThreadStream` 中的 `onCreated` 回调，在 thread 创建后向 Gateway 注册映射。

```typescript
onCreated(meta) {
  handleStreamStart(meta.thread_id);
  setOnStreamThreadId(meta.thread_id);
  // 新增：注册 thread 归属
  fetchWithAuth(`${getBackendBaseURL()}/api/threads/bindUser`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: meta.thread_id }),
  }).catch(console.error); // 静默失败，不阻塞对话
},
```

**FR-6:** `useDeleteThread` 无需修改。它已经调用 `fetchWithAuth(DELETE /api/threads/{threadId})`，FR-3 会在该端点中同步清理映射。但需要确认：当前 `useDeleteThread` 先调用 `apiClient.threads.delete(threadId)`（LangGraph），再调用 Gateway DELETE。这个顺序保持不变即可。

### 4.3 前端：侧边栏用户信息 + 登出

**FR-7:** 修改 `WorkspaceNavMenu`（`frontend/src/components/workspace/workspace-nav-menu.tsx`）。

在 DropdownMenu 触发按钮区域显示用户信息：
- 侧边栏展开时：显示用户邮箱（截断过长邮箱）+ 原有的"设置和更多"
- 侧边栏折叠时：显示邮箱首字母的圆形头像
- 通过 `useAuth()` hook 获取 `user?.email`

在 DropdownMenu 中添加"退出登录"菜单项：
- 位于菜单最底部，与"关于"之间有分隔线
- 使用 `LogOut` icon（lucide-react）
- 点击后：`await logout()` → `router.push("/login")`

### 4.4 数据清理

**FR-8:** 部署前清除历史数据。

```bash
rm -rf backend/.deer-flow/checkpoints.db*
rm -rf backend/.deer-flow/memory.json
rm -rf backend/.langgraph_api/
```

---

## 5. Non-Goals (Out of Scope)

- Memory / Artifacts / Skills 的 per-user 隔离
- LangGraph Server auth 配置变更
- Thread 访问权限校验（用户通过直接构造 URL 仍可访问其他用户的 thread 内容——本次只做列表隔离，不做访问控制）
- 用户管理 UI、Thread 分享、历史数据迁移
- 修改全局 fetch 或切换 LangGraph apiUrl

---

## 6. Design Considerations

### 数据流架构

```
┌─────────────────────────────────────────────────────────┐
│                        Frontend                          │
│                                                          │
│  Thread 列表 ──fetchWithAuth──▶ Gateway /listByUser     │
│  Thread 创建 ──onCreated──────▶ Gateway /bindUser       │
│  Thread 删除 ──fetchWithAuth──▶ Gateway DELETE (已有)    │
│                                                          │
│  对话/流式/状态 ──LangGraph SDK──▶ LangGraph API (不变) │
└─────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────────┐
│   Gateway    │         │  LangGraph API   │
│              │         │  (auth=noop)     │
│ thread_owners│         │                  │
│ (映射表)     │────────▶│  checkpointer    │
│              │ 读取元数据│  (thread state)  │
└──────────────┘         └──────────────────┘
```

### 映射表存储

复用 Gateway 已有的 `AsyncSqliteStore`（`app.state.store`），使用独立 namespace `("thread_owners",)`：
- Key: `thread_id`
- Value: `{"user_id": "...", "created_at": timestamp}`

这样不需要新建数据库或表，直接复用现有基础设施。

### 侧边栏底部布局

```
改造前：
┌─────────────────────────┐
│ ⚙️  设置和更多      ▾▴  │
└─────────────────────────┘

改造后（展开态）：
┌─────────────────────────┐
│ 🔵 admin@mikubest.com   │
│ ⚙️  设置和更多      ▾▴  │
└─────────────────────────┘

改造后（折叠态）：
┌───┐
│ A │
└───┘

DropdownMenu 新增：
┌─────────────────────────┐
│ ⚙️  设置              │
│ 🌐  官方网站           │
│ ...                     │
│ ℹ️  关于              │
│ ───────────────────── │
│ 🚪  退出登录           │  ← 新增
└─────────────────────────┘
```

### 复用现有组件

- `fetchWithAuth()` — 已处理 cookie + CSRF header
- `useAuth()` — 已提供 `user` 对象和 `logout()` 方法
- `@require_auth` — 已实现 JWT 解码 + AuthContext
- `app.state.store` — 已初始化的 AsyncSqliteStore
- `get_checkpointer()` — 用于读取 thread 元数据

---

## 7. Technical Considerations

### 7.1 `listByUser` 的性能

`listByUser` 需要：
1. 从 Store 查询当前用户的所有 `thread_id`
2. 对每个 `thread_id` 从 checkpointer 读取最新 checkpoint 获取 title/updated_at

如果用户 thread 数量较多（>100），逐个读取 checkpoint 可能较慢。优化方案：
- 在映射记录中冗余存储 `title` 和 `updated_at`（在 `bindUser` 时写入初始值）
- thread 完成时通过 `onFinish` 回调更新映射中的 title
- 这样 `listByUser` 只需查 Store，不需要读 checkpointer

但作为 MVP，先用逐个读取 checkpointer 的方式，后续按需优化。

### 7.2 CSRF Token 传递

Gateway 的 `CSRFMiddleware` 对所有 POST/PUT/PATCH/DELETE 请求要求 CSRF token（auth 端点除外）。`fetchWithAuth` 已经处理了 CSRF header 的附加，所以：
- `POST /api/threads/bindUser` — 通过 `fetchWithAuth` 调用，CSRF 自动处理 ✅
- `DELETE /api/threads/{thread_id}` — 已通过 `fetchWithAuth` 调用 ✅
- `GET /api/threads/listByUser` — GET 请求不需要 CSRF ✅

### 7.3 映射一致性

存在一个边界情况：如果 `onCreated` 中的 `bindUser` 调用失败（网络问题等），thread 会在 LangGraph 中创建但不在映射表中。这意味着：
- 该 thread 不会出现在用户的列表中
- 但用户当前会话中仍然可以正常使用该 thread（因为 `threadId` 已经在前端状态中）
- 刷新页面后该 thread 会"消失"

这是可接受的 trade-off。如果需要更强一致性，可以在 `listByUser` 中增加一个"补偿扫描"：检查 checkpointer 中是否有未注册的 thread 属于当前用户（但这需要额外的标识机制，增加复杂度）。

### 7.4 与现有 thread 路由的关系

Gateway 已有 `POST /api/threads`（create）和 `POST /api/threads/search`（search）端点。本方案**不修改这些端点**，而是新增独立的 `/bindUser` 和 `/listByUser`。原因：
- 现有端点被其他功能使用（如 IM channels 的 thread 管理）
- 新增端点职责单一，只管映射，不影响现有逻辑

---

## 8. Success Metrics

- 两个不同用户在各自隐私窗口中登录后，thread 列表完全独立
- 对话创建、消息发送、流式响应等功能不受影响（继续直连 LangGraph API）
- 登录后侧边栏底部正确显示用户邮箱，登出功能正常
- Thread 删除后映射同步清理

---

## 9. Open Questions

（已全部解决，无遗留问题）

---

## 10. Implementation Summary

| 改动位置 | 改动内容 | 复杂度 |
|---------|---------|--------|
| `backend/app/gateway/routers/threads.py` | 新增 `bindUser`、`listByUser` 端点；`delete` 端点增加映射清理 | 中 |
| `frontend/src/core/threads/hooks.ts` | `useThreads` 改为调 Gateway；`onCreated` 增加 `bindUser` 调用 | 低 |
| `frontend/src/components/workspace/workspace-nav-menu.tsx` | 显示用户邮箱 + 登出按钮 | 低 |
| 数据清理 | 删除 `.deer-flow/checkpoints.db*`、`.langgraph_api/` | 一次性 |
