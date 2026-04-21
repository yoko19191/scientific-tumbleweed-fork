# DeerFlow 全面 Bug 审计报告

> 审计日期: 2026-04-21
> 审计范围: 前端 (Next.js 16)、后端网关 (FastAPI)、Agent Harness (LangGraph)、基础设施 (Docker/Nginx/K8s)
> 发现总数: ~90 个问题，其中 20 个直接影响用户体验的 bug 已修复

---

## 一、已修复的用户体验 Bug（20 个）

### P0 — 功能性阻断

#### B01. `listByUser` 从全局命名空间读取，用户看不到 thread 元数据
- **文件**: `backend/app/gateway/routers/threads.py:283`
- **现象**: `create_thread` 写入用户命名空间 `user_threads_namespace(user_id)`，但 `listByUser` 用 `_store_get(store, thread_id)` 默认从全局 `THREADS_NS` 读取。用户的 thread 列表缺少 metadata（标题、时间等）。
- **修复**: 改为从 `user_threads_namespace(user_id)` 读取，回退到全局命名空间以兼容旧数据。

#### B02. `authz.py` owner_check 找不到 record 时直接放行
- **文件**: `backend/app/gateway/authz.py:245-252`
- **现象**: `_store_get` 从全局命名空间读取，用户命名空间的 thread 找不到 → `record` 为 `None` → 跳过所有权检查 → 任何用户可访问任何 thread。
- **修复**: 从用户命名空间读取（回退全局），`record is None` 时返回 404 拒绝访问。

#### B03. `normalize_input` 把所有非 human 消息都转成 `HumanMessage`
- **文件**: `backend/app/gateway/services.py:82-93`
- **现象**: system、ai、tool 类型的消息全被错误转为 `HumanMessage`，导致 agent 误解消息历史，多轮对话中 agent 行为异常。
- **修复**: 正确映射 `system` → `SystemMessage`，`ai`/`assistant` → `AIMessage`，`tool` → `ToolMessage`。

#### B04. `FileMemoryStorage` 非线程安全，memory 数据可能损坏
- **文件**: `backend/packages/harness/deerflow/agents/memory/storage.py:60-156`
- **现象**: 后台 timer 线程执行 `save()` 时，主线程同时调用 `load()`，并发读写 `_memory_cache` 和文件 I/O 无锁保护。
- **修复**: 添加 `threading.Lock` 保护所有 cache 读写和文件操作。

#### B05. `WeakValueDictionary` 存储文件操作锁，GC 可回收导致互斥失效
- **文件**: `backend/packages/harness/deerflow/sandbox/file_operation_lock.py:9-27`
- **现象**: 并发 `str_replace` 或 `write_file` 操作同一文件时，锁可能被 GC 回收，导致文件内容损坏。
- **修复**: 改用普通 `dict` 存储锁。

### P1 — 体验降级

#### B06. 前端 401 响应无处理，session 过期后静默失败
- **文件**: `frontend/src/core/auth/fetcher.ts:24-44`
- **现象**: session 过期后所有 API 调用返回 401，但前端不处理，用户看到空白或加载中状态。
- **修复**: 在 `fetchWithAuth` 中检测 401 响应，非 auth 端点自动跳转到登录页。

#### B07. `parseInt` 配合 `??` 运算符无法正确处理 NaN
- **文件**: `frontend/src/core/messages/utils.ts:386`
- **现象**: `parseInt(fileMatch[2].trim(), 10) ?? 0` — `parseInt` 返回 `NaN` 而非 `null`，`??` 不会触发，文件大小显示为 `NaN`。
- **修复**: 使用 `Number.isNaN()` 检查，NaN 时回退为 0。

#### B08. `MemoryUpdateQueue.flush()` 期间新入队的项可能丢失
- **文件**: `backend/packages/harness/deerflow/agents/memory/queue.py:156-166`
- **现象**: `flush()` 取消 timer 后调用 `_process_queue()`，处理期间新 `add()` 的项不会被处理。graceful shutdown 时用户最后的 memory 更新可能丢失。
- **修复**: `flush()` 后检查队列是否有新项，有则再次处理。

#### B09. `update_memory_from_conversation` 把 `agent_name` 当 `user_id` 传入
- **文件**: `backend/packages/harness/deerflow/agents/memory/updater.py:449-469`
- **现象**: 便捷函数的第三个位置参数是 `user_id`，但参数名为 `agent_name`，传入 `updater.update_memory()` 的 `user_id` 位置。memory 会存到错误路径。
- **修复**: 将参数名从 `agent_name` 改为 `user_id`，更新文档。

#### B10. `_background_tasks` 字典无限增长
- **文件**: `backend/packages/harness/deerflow/subagents/executor.py:69`
- **现象**: 父 agent crash 或用户断开后，已完成的 subagent 任务永不清理。长时间运行的服务器内存持续增长。
- **修复**: 添加 TTL 清理机制（15 分钟），在 `get_background_task_result` 时自动清扫终态任务。

#### B11. `SandboxMiddleware.after_agent` 每次都释放沙箱
- **文件**: `backend/packages/harness/deerflow/sandbox/middleware.py:70-86`
- **现象**: 文档说"不在每次 agent 调用后释放沙箱"，但代码无条件调用 `release()`。Docker 沙箱每轮对话都销毁重建容器，延迟增加且临时数据丢失。
- **修复**: 移除 `after_agent` 中的 `release()` 调用，依赖 shutdown 清理。

#### B12. 前端 subtask 状态直接 mutation
- **文件**: `frontend/src/core/tasks/context.tsx:41-53`
- **现象**: `tasks[task.id] = { ...tasks[task.id], ...task }` 直接修改对象，违反 React 不可变原则，subtask 状态更新可能不触发重渲染。
- **修复**: 每次更新都通过 `setTasks` 创建新对象。

#### B13. `get_app_config` 非线程安全
- **文件**: `backend/packages/harness/deerflow/config/app_config.py:294-323`
- **现象**: 多线程并发 reload 配置时可能读到不一致的状态。
- **修复**: 添加 `threading.Lock` 保护 reload 逻辑。

#### B14. Provisioner 用阻塞 `time.sleep()` 在 async 端点中
- **文件**: `docker/provisioner/app.py:490-494`
- **现象**: `create_sandbox` 端点用 `time.sleep(0.5)` 循环等待最多 10 秒，阻塞整个事件循环，其他用户请求全部挂起。
- **修复**: 改用 `await asyncio.sleep(0.5)`。

#### B15. `stateless_stream` / `stateless_wait` 自动创建的 thread 不绑定用户
- **文件**: `backend/app/gateway/routers/runs.py:56,96`
- **现象**: 这些端点用 `get_optional_user_id(request)` 但 `request.state.auth` 未被填充，导致自动创建的 thread 成为孤儿，用户在 thread 列表中看不到。
- **修复**: 在获取 user_id 前调用 `_authenticate(request)` 填充 auth 状态。

### 前端流式 & 状态管理修复

#### F01. `normalizeStoredRunId` 解析无效 run ID 导致流重连失败
- **文件**: `frontend/src/core/threads/hooks.ts:41-90`
- **现象**: 函数对提取的 run ID 不做格式验证，空字符串或非 UUID 字符串被当作有效 ID 返回，导致 `useStream` 的 `reconnectOnMount` 用无效 ID 尝试重连，触发 404/422 错误。
- **修复**: 添加 `isValidRunId()` 验证函数，所有提取路径都必须通过 UUID 格式校验才返回。

#### F02. `useThreadStream` 中 `updateSubtask` 闭包持有旧组件引用（内存泄漏）
- **文件**: `frontend/src/core/threads/hooks.ts:217`
- **现象**: `updateSubtask` 来自 `useUpdateSubtask()` hook，每次 `tasks` 状态变化都会生成新引用。但它被直接用在 `onUpdateEvent` 回调中，旧闭包持有旧的 `tasks` 对象引用，阻止 GC 回收已卸载组件的状态。
- **修复**: 改用 `useRef` 存储 `updateSubtask`，回调中通过 `updateSubtaskRef.current` 调用，避免闭包捕获。

#### F03. 文件上传竞态条件（快速连续发消息时上传可能重叠）
- **文件**: `frontend/src/core/threads/hooks.ts:420-480`
- **现象**: `sendInFlightRef` 只防止完全并发的 `sendMessage` 调用，但如果用户在上传进行中快速点击发送，第一次上传的 `await uploadFiles()` 还在进行时，第二次调用可能在 `sendInFlightRef` 被 `finally` 重置后立即进入。
- **修复**: 添加 `AbortController`，在上传流程的关键点检查 `abortController.signal.aborted`，防止已取消的上传继续执行。

#### F04. `sendMessage` 中 `context` 对象引用不稳定导致不必要的重渲染
- **文件**: `frontend/src/core/threads/hooks.ts:563`
- **现象**: `context` 对象每次父组件渲染都是新引用（即使内容相同），导致 `useCallback` 的 `sendMessage` 每次都重新创建，进而触发依赖它的子组件不必要的重渲染。
- **修复**: 添加 `useMemo` 对 `context` 做浅稳定化（基于关键字段），`useCallback` 依赖 `stableContext` 而非 `context`。

#### F05. `useThreadChat` 对非 UUID thread ID 无验证
- **文件**: `frontend/src/components/workspace/chats/use-thread-chat.ts:13-36`
- **现象**: URL 中的 `thread_id` 参数如果不是 "new" 也不是有效 UUID（例如用户手动输入乱码），会被直接传给 `useStream`，导致 LangGraph Server 返回 422 错误。
- **修复**: 添加 `isValidUUID()` 验证，非法 ID 自动生成新 UUID 并标记为新 thread。

---

## 二、未修复的安全漏洞（建议后续处理）

### CRITICAL

| # | 问题 | 文件 | 说明 |
|---|------|------|------|
| S01 | `.env` 包含真实 API key 且被 git 追踪 | `.env` | 所有 key（OpenAI、Anthropic、Tavily、LangSmith 等）已泄露到仓库历史。需立即轮换并用 `bfg` 清理 git 历史。 |
| S02 | 本地沙箱 bash 用 `subprocess.run(shell=True)` | `sandbox/local/local_sandbox.py:254` | 路径校验是 regex "best-effort"，可通过 `$()` 子 shell 绕过。`allow_host_bash` 默认关闭，但启用时有风险。 |
| S03 | ~~Markdown 渲染 XSS~~ **已修复** | `markdown-content.tsx:38` | 链接 href 现在过滤 `javascript:` / `data:` 等危险协议。 |

### HIGH

| # | 问题 | 文件 |
|---|------|------|
| S04 | CSRF 保护豁免所有 `/api/threads`、`/api/runs` 路径 | `csrf_middleware.py:30-34` |
| S05 | `AuthMiddleware` 只检查 cookie 存在，不验证 JWT 有效性 | `auth_middleware.py:55-71` |
| S06 | 注册端点无速率限制 | `auth.py:185-215` |
| S07 | 登出不在服务端失效 JWT（7 天有效期） | `auth.py:218-222` |
| S08 | Nginx CORS 设置 `Access-Control-Allow-Origin: *` | `nginx.conf:40` |
| S09 | K8s 沙箱 Pod `allow_privilege_escalation=True` | `provisioner/app.py:369` |
| S10 | K8s API 连接 SSL 验证被禁用 | `provisioner/app.py:150` |
| S11 | 所有 Docker 容器以 root 运行 + 挂载 Docker socket | `docker-compose.yaml` |
| S12 | 路径校验 regex 可通过 shell 元字符绕过 | `sandbox/tools.py:23` |
| S13 | `PROMPT` 权限模式对未知工具反而更宽松 | `permissions/policy.py:63` |

### MEDIUM

| # | 问题 | 文件 |
|---|------|------|
| S14 | 匿名用户可创建 thread 但无法被搜索或删除（孤儿 thread） | `threads.py:382-465` |
| S15 | SQLite 初始化存在竞态条件 | `auth/repositories/sqlite.py:75-83` |
| S16 | Provisioner `sandbox_id` 未校验格式（K8s 资源名注入） | `provisioner/app.py:223` |
| S17 | Provisioner API 无认证 | `provisioner/app.py` |
| S18 | Nginx 缺少安全响应头（X-Frame-Options、CSP、HSTS） | `nginx.conf` |
| S19 | artifacts 读取文件无大小限制 | `artifacts.py:179` |
| S20 | 改密码端点无速率限制 | `auth.py:226-268` |
| S21 | 速率限制仅进程内，多 worker 可绕过 | `auth.py:76-77` |
| S22 | `_resolve_skills_path` 未做 symlink 解析后的路径包含检查 | `sandbox/tools.py:93-114` |
| S23 | `LocalSandbox._resolve_path` 无遍历保护 | `sandbox/local/local_sandbox.py:91-114` |

---

## 三、修改文件清单

```
backend/app/gateway/routers/threads.py        # B01: 用户命名空间读取
backend/app/gateway/authz.py                  # B02: owner_check 拒绝 None record
backend/app/gateway/services.py               # B03: 消息类型正确映射
backend/app/gateway/routers/runs.py           # B15: stateless runs 用户绑定
backend/packages/harness/deerflow/agents/memory/storage.py   # B04: 线程安全
backend/packages/harness/deerflow/agents/memory/queue.py     # B08: flush 丢失修复
backend/packages/harness/deerflow/agents/memory/updater.py   # B09: 参数名修正
backend/packages/harness/deerflow/sandbox/file_operation_lock.py  # B05: dict 替换 WeakValueDict
backend/packages/harness/deerflow/sandbox/middleware.py       # B11: 移除 after_agent release
backend/packages/harness/deerflow/subagents/executor.py       # B10: TTL 清理
backend/packages/harness/deerflow/config/app_config.py        # B13: 线程安全
docker/provisioner/app.py                     # B14: asyncio.sleep
frontend/src/core/auth/fetcher.ts             # B06: 401 处理
frontend/src/core/messages/utils.ts           # B07: parseInt NaN
frontend/src/core/tasks/context.tsx           # B12: 不可变更新
frontend/src/core/threads/hooks.ts            # F01-F04: run ID 验证、内存泄漏、上传竞态、context 稳定化
frontend/src/components/workspace/chats/use-thread-chat.ts  # F05: UUID 验证
frontend/src/components/workspace/messages/markdown-content.tsx  # S03: XSS 修复
```
