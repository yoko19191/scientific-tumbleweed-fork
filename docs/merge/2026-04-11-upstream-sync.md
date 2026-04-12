# 合并记录: upstream/main → main

## 基本信息

| 项目 | 内容 |
|---|---|
| 日期 | 2026-04-11 |
| 合并来源 | `upstream/main` (bytedance/deer-flow) |
| 合并目标 | `main` (scientific-tumbleweed-fork) |
| 上游 tip | `092bf13f` fix(makefile): route Windows shell-script targets through Git Bash |
| 合并提交 | `dc2b543d` |
| 涉及上游 commit 数 | 103 个 |
| 变更文件数 | ~302 个 |

## 跳过内容

| 内容 | 原因 |
|---|---|
| Blog 结构 (`7dc0c7d0`) | 用户要求跳过 |
| 文档站内容 (`c1366cf5`, `frontend/src/content/`) | 用户要求跳过 |
| `frontend/src/components/landing/header.tsx` | 永不修改 Landing Page |
| `frontend/src/components/landing/hero.tsx` | 永不修改 Landing Page |
| `frontend/src/components/landing/sections/case-study-section.tsx` | 永不修改 Landing Page |
| `frontend/src/components/landing/sections/community-section.tsx` | 永不修改 Landing Page |

## 冲突决策记录

### frontend/src/app/workspace/layout.tsx
- **策略**: 采用上游 cookie-based sidebar (Server Component + `defaultOpen`)，保留 custom `<AuthProvider>` + `<AuthGuard>` 包裹
- **移除**: 旧的 `queryClient` 实例、`useLocalSettings`、`useLayoutEffect`、`handleOpenChange` 客户端逻辑

### frontend/src/core/threads/hooks.ts
- **冲突**: `onCreated` 回调中 bindUser vs agent_name metadata
- **策略**: 两者都保留 — `fetchWithAuth bindUser`（租户隔离）+ `threads.update agent_name`（上游新功能）
- **冲突2**: `useThreads` 签名 — 保留 custom 的 `listByUser` 实现，丢弃上游 params 参数（custom 用自己的 API）

### frontend/src/app/workspace/chats/[thread_id]/page.tsx
- **策略**: 采用上游 `mounted` guard + `onFollowupsVisibilityChange`，保留 custom `aiDisclaimer` 段落

### backend/packages/harness/deerflow/agents/lead_agent/prompt.py
- **冲突1** (`get_skills_prompt_section`): 采用上游完整实现（`lru_cache` + 后台刷新线程 + skill evolution 支持）
- **冲突2** (`get_agent_soul` 签名): 保留 HEAD 的 `user_id` 参数（多租户功能）

### backend/packages/harness/deerflow/agents/lead_agent/agent.py
- **冲突1** (`load_agent_config`): 保留 `user_id=user_id`（多租户）
- **冲突2** (`apply_prompt_template`): 两者都传 — `user_id` + `available_skills`

### backend/app/gateway/routers/skills.py
- **冲突1**: 在 `if not user_id` 块之前先调用 `reload_extensions_config()` + `refresh_skills_system_prompt_cache_async()`（上游改进），保留 `if not user_id` 块
- **冲突2**: 保留 custom `install_skill` endpoint（上游删除了，但 custom 需要）

### backend/app/gateway/routers/agents.py
- **策略**: 保留 `list_custom_agents(user_id=user_id)` + `_agent_config_to_response(a, user_id=user_id)`（多租户）

### backend/packages/harness/deerflow/config/app_config.py
- **策略**: 合并 imports — 保留 `load_hooks_config_from_dict`（custom hooks 系统），加入上游新增的 `GuardrailsConfig`、`MemoryConfig` 类型导入

### backend/packages/harness/deerflow/agents/memory/queue.py
- **策略**: 修复 `datetime.utcnow()` → `datetime.now(UTC)`（上游正确做法），同时保留 `user_id` 字段，新增 `agent_name` 字段

### backend/packages/harness/deerflow/agents/memory/updater.py
- **策略**: 保留 `get_memory_data(user_id)`（多租户），采用 `utc_now_iso_z()`（上游 UTC 修复）

### backend/packages/harness/deerflow/skills/loader.py
- **策略**: 保留 `user_id` 分支目录扫描逻辑，同时采用上游 `skills_by_name` dict 去重

### backend/app/channels/feishu.py
- **策略**: 采用上游 imports（新增 `KNOWN_CHANNEL_COMMANDS`、`InboundMessage`、sandbox 路径支持，用于文件上传功能）

### backend/packages/harness/deerflow/client.py
- **策略**: 保留 `user_id` + 新增 `available_skills`（两者都传）

## 主要新功能

### 后端
- Skill 自进化系统 (`skills/manager.py`, `security_scanner.py`, `lru_cache` prompt 缓存)
- Sandbox grep/glob 搜索工具 + 文件操作锁
- Checkpoint 完整回滚（用户取消时）
- Memory 正向强化检测 + UTC datetime 修复
- `when_thinking_disabled` 模型配置支持
- Ollama 原生 provider (`langchain-ollama`)
- WeChat/WeCom 频道集成
- Feishu 文件上传支持
- Setup Wizard + doctor 命令
- SSE stream resume (Last-Event-ID)
- Sandbox 孤儿容器启动时回收
- `ls_output_max_chars` 截断配置

### 前端
- Cookie-based sidebar 状态（Server Component，无闪烁）
- `mounted` guard + followups 可见性控制（InputBox）
- `pathOfThread` 支持 agent_name 路由
- `useSyncExternalStore` settings store（无 hydration 闪烁）
- 文件上传验证（macOS .app bundle 拦截）
- `rel="noopener noreferrer"` 安全修复（多处）
- `useThreads` 新 params 支持（上游版本，custom 保留自己的 listByUser）
- Agent 新建页面 Save 功能

## source/deerflow 更新

`source/deerflow` 已 fast-forward 至 `upstream/main` tip (`092bf13f`)。
