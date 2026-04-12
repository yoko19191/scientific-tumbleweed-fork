# 合并说明

## 来源与目标

本次合并源自 `upstream/main`（bytedance/deer-flow，commit `092bf13f`）分支与 `main`（scientific-tumbleweed-fork）分支，整合了以下功能模块代码：

- **Skill 自进化模块**：`skills/manager.py`、`skills/security_scanner.py`，支持技能的动态创建、编辑与版本回滚
- **Sandbox 搜索工具模块**：`sandbox/search.py`、`sandbox/file_operation_lock.py`，新增 grep/glob 工具及文件操作并发锁
- **Memory 增强模块**：`agents/memory/updater.py`、`agents/memory/queue.py`，新增正向强化检测与 UTC 时间修复
- **模型工厂模块**：`models/factory.py`，新增 `when_thinking_disabled` 配置及 Ollama 原生 provider 支持
- **Checkpoint 回滚模块**：`runtime/runs/worker.py`，实现用户取消时的完整状态回滚
- **频道集成模块**：`app/channels/wechat.py`、`app/channels/wecom.py`，新增微信与企业微信接入
- **前端设置存储模块**：`frontend/src/core/settings/store.ts`，基于 `useSyncExternalStore` 重构，消除 hydration 闪烁
- **前端文件校验模块**：`frontend/src/core/uploads/file-validation.ts`，拦截 macOS `.app` bundle 误上传

## 代码结构

**主要类**：

| 类 | 文件 | 说明 |
|---|---|---|
| `SkillManager` | `skills/manager.py` | 技能文件原子写入、历史版本管理 |
| `SecurityScanner` | `skills/security_scanner.py` | 技能内容安全扫描 |
| `AioSandboxProvider` | `community/aio_sandbox/aio_sandbox_provider.py` | 新增孤儿容器启动回收逻辑 |
| `MemoryUpdater` | `agents/memory/updater.py` | 记忆更新，新增 `reinforcement_detected` 参数 |
| `ConversationContext` | `agents/memory/queue.py` | 新增 `agent_name` 字段，修复 UTC 时间戳 |
| `AppConfig` | `config/app_config.py` | 新增 `SkillEvolutionConfig`、`GuardrailsConfig`、`MemoryConfig` 类型导入 |

**主要方法**：

| 方法 | 所在类/模块 | 说明 |
|---|---|---|
| `get_skills_prompt_section()` | `lead_agent/prompt.py` | 重构为 `lru_cache` + 后台刷新线程，提升缓存命中率 |
| `refresh_skills_system_prompt_cache_async()` | `lead_agent/prompt.py` | 技能变更后异步刷新 prompt 缓存 |
| `_reconcile_orphans()` | `AioSandboxProvider` | 启动时回收上次进程遗留的孤儿容器 |
| `detect_reinforcement()` | `memory_middleware.py` | 检测用户正向反馈信号，触发记忆强化 |
| `apply_prompt_template()` | `lead_agent/prompt.py` | 新增 `available_skills` 参数，支持 per-agent 技能过滤 |
| `parseSidebarOpenCookie()` | `workspace/layout.tsx` | 从 cookie 读取侧边栏初始状态，替代客户端 localStorage 方案 |
| `splitUnsupportedUploadFiles()` | `uploads/file-validation.ts` | 过滤不支持上传的文件类型 |

## 冲突处理

合并过程中存在以下冲突，均通过手动比对逻辑、保留双方关键变更并新增适配层解决：

1. **`workspace/layout.tsx`**：上游改为 Server Component + cookie 读取侧边栏状态，本分支有 `AuthProvider`/`AuthGuard` 包裹层。通过在 async Server Component 外层保留认证包裹、内层采用上游 `defaultOpen` 方案解决，两侧逻辑均完整保留。

2. **`core/threads/hooks.ts`**：上游在 `onCreated` 回调中新增 `agent_name` metadata 写入，本分支有 `bindUser` 租户绑定调用。新增适配层，在同一回调中顺序执行两个异步操作，互不干扰。

3. **`lead_agent/prompt.py`**：上游将 `get_skills_prompt_section` 重构为带 `lru_cache` 的缓存版本，本分支保留了 `get_agent_soul(user_id=)` 多租户签名。采用上游完整缓存实现，同时在函数签名中保留 `user_id` 可选参数作为适配层。

4. **`skills/loader.py`**：上游引入 `skills_by_name` dict 去重，本分支有基于 `user_id` 的用户隔离目录扫描逻辑。将 dict 初始化提前，在保留用户隔离扫描分支的同时采用上游去重策略。

5. **`agents/memory/queue.py`**：上游将 `user_id` 替换为 `agent_name`，本分支依赖 `user_id` 实现租户隔离。保留 `user_id` 字段，同时新增 `agent_name` 字段，两者共存，同步修复 `datetime.utcnow()` 为 `datetime.now(UTC)`。

6. **`app/gateway/routers/skills.py`**：上游删除了 `install_skill` endpoint，本分支保留该接口用于技能文件安装。移除上游引入的无 `user_id` 重复定义，保留本分支带用户隔离的完整实现。

## 总结

本次合并完成跨分支功能集成，将上游 103 个提交（涉及约 302 个文件）选择性同步至产品分支。通过手动比对六处核心冲突，在保留本分支多租户隔离、JWT 认证、品牌定制等关键逻辑的前提下，完整引入上游的技能自进化、Sandbox 搜索、Memory 增强、模型扩展等新能力。解决了上游无状态设计与本分支有状态多租户架构之间的兼容性问题，提升了技能管理、Prompt 缓存、文件上传等模块的复用性与健壮性。
