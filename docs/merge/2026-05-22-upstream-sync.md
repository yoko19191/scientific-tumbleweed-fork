# upstream/main -> main 合并 TODO 与执行计划 (2026-05-22)

> 合并自 `2026-05-22-upstream-sync-todo.md` 与 `2026-05-22-upstream-sync-plan.md`。
> 本文档保留 TODO List 作为主结构，并把原 Plan 中的批次策略、cherry-pick 命令、冲突预警、验证项、耗时估算、里程碑与已确认决策并入同一份执行清单。

## 基本信息

| 项目 | 内容 |
|---|---|
| 日期 | 2026-05-22 |
| 合并来源 | `upstream/main` (bytedance/deer-flow) |
| 合并目标 | `main` (scientific-tumbleweed-monorepo) |
| 上次合并点 | `189b8240` fix(sandbox): pass no_change_timeout to exec_command to prevent 120s premature termination (#2685) |
| 文档基准上游 tip | `f0bae286` fix(middleware): handle repeated tool call ids (#3143) |
| 2026-05-24 实际 upstream/main | `e7967a7f` fix(frontend): hide copy for streaming assistant turn (#3176) |
| 待处理上游 commit 数 | 121 个 (不含 merge) |
| 上游里程碑 | v2.0-m0, v2.0-m1-rc0, v2.0-m1-rc1 |
| 预计工作量 | 约 27-32 小时，建议分 5-6 个工作日完成 |

## 执行记录

- 2026-05-24: 已刷新 `upstream/main`，发现实际 tip 已前进到 `e7967a7f`；本轮先严格执行本文档基准 `f0bae286` 及其以前列出的低歧义批次，不混入新增上游提交。
- 2026-05-24: 已创建并切换到 `merge/2026-05-22-upstream-sync` 工作分支。

## 前置准备

- [x] 确保 upstream 最新

```bash
git fetch upstream
```

- [x] 创建合并工作分支

```bash
git checkout main
git checkout -b merge/2026-05-22-upstream-sync
```

- [x] 确认起始点

```bash
git log --oneline upstream/main | head -5
# 文档基准 tip 为 f0bae286；2026-05-24 实际 upstream/main 为 e7967a7f
```

## 批次总览

| 批次 | 对应 Phase | 内容 | Commits | 策略 | 预计冲突 | 预计耗时 |
|------|------------|------|---------|------|----------|----------|
| A | Phase 1 | 安全修复 | 3 | 直接 cherry-pick | 低 | 30min |
| B | Phase 2 | Middleware 修复 | 5 | 按依赖顺序 cherry-pick | 中 | 1h |
| C | Phase 5 + 6 | MCP + Runtime 修复 | 7 | 直接 cherry-pick | 低 | 45min |
| D | Phase 9 + 10 | Subagent + Memory 修复 | 3 | 逐个 cherry-pick | 中 | 45min |
| E | Phase 11 | 前端修复 | 9 | 批量 cherry-pick | 低 | 1h |
| F | Phase 12 + 13 | Sandbox + 通用修复 | 批量 | 按文件分组 cherry-pick | 低~中 | 2h |
| G | Phase 3 | DynamicContextMiddleware | 4 | 单独分支验证 | 高 | 3-4h |
| H | Phase 4 | Loop Detection 增强 | 3 | 单独分支验证 | 高 | 2h |
| I | Phase 7 | Safety Termination | 1 | 单独分支验证 | 中 | 1.5h |
| J | Phase 8 | Stability P0 选择性提取 | 1 | 手动适配 | 高 | 2h |
| K | Phase 14 | 新功能直接 cherry-pick | 6 | 直接 cherry-pick | 低 | 30min |
| L | Phase 15 | 新功能手动适配 | 多系列 | 手动适配 + 验证 | 高 | 10-14h |
| M | Phase 16 | Auth 独立修复 | 2 | 直接 cherry-pick | 低 | 15min |

## 推荐执行顺序

- [x] A: Phase 1 安全修复
- [x] B: Phase 2 Middleware 修复
- [x] C: Phase 5 MCP 修复 + Phase 6 Runtime 修复（适用项）
- [ ] D: Phase 9 Subagent 修复 + Phase 10 Memory 修复
- [ ] E: Phase 11 前端修复
- [ ] F: Phase 12 Sandbox 修复 + Phase 13 其他通用修复
- [ ] G: Phase 3 DynamicContextMiddleware，单独分支验证
- [ ] H: Phase 4 Loop Detection 增强，单独分支验证
- [ ] I: Phase 7 Safety Termination，单独分支验证
- [ ] J: Phase 8 Stability P0，选择性提取
- [ ] K: Phase 14 新功能直接 cherry-pick
- [ ] L: Phase 15 新功能手动适配，逐项讨论
- [x] M: Phase 16 Auth 独立修复

## A: 安全修复 (Phase 1)

**优先级**: 🔴 最高
**策略**: 直接 cherry-pick，逐个验证
**预计耗时**: 30min

- [x] `e543bbf5` [security] fix(upload): reject symlinked upload destinations (#2623)
- [x] `2b0e62f6` [security] fix(auth): reject cross-site auth POSTs (#2740)
- [x] `7ec8d3a6` fix(security): mask sensitive values in MCP config API responses (#2667)

```bash
git cherry-pick e543bbf5
git cherry-pick 2b0e62f6
git cherry-pick 7ec8d3a6
```

**执行备注**

- `e543bbf5` 与当前 fork 的 upload router 有结构差异：本次只移植 symlink-safe destination 写入、unsafe destination 跳过和响应 `skipped_files`，不引入上游未列入本批次的 authz/upload-limit 改造。
- `7ec8d3a6` 保留 fork 的 per-user MCP enabled override 与全局 MCP config 只读策略，仅对 GET 响应中的 `env`、`headers`、OAuth secrets 做脱敏。

**验证**

- [ ] `make lint` 通过
- [x] 安全相关单元测试通过: `uv run python -m pytest tests/test_uploads_manager.py tests/test_uploads_router.py tests/test_channel_file_attachments.py tests/test_csrf_middleware.py tests/test_mcp_config_secrets.py -q`，101 passed
- [x] 手动检查: upload 路径验证、auth POST 来源校验、MCP config 响应脱敏

## B: Middleware 修复 (Phase 2)

**优先级**: 🔴 Critical
**策略**: 按依赖顺序逐个 cherry-pick
**预计耗时**: 1h，可能需要冲突解决

> 这些修复了生产环境中的 P0/P1 级 middleware 问题，直接影响 agent 运行稳定性。涉及 middleware 链，fork 的 `middleware_builder.py` 可能需要小调整。

- [x] `5fd0e6ac` fix(middleware): sync raw tool call metadata (#2757)
- [x] `20d2d2b3` fix(middleware): Handle invalid tool calls in dangling pairing middleware (#2890) (#2891)
- [x] `0c37509b` fix(middleware): Prevent todo completion reminder IMMessage leak (#2907) — todo 中间件 IM 消息泄漏
- [x] `181d8365` fix(middleware): normalize tool result adjacency before model calls (#2939) — dangling tool call middleware 修复，防止 tool_calls 和 ToolMessage 顺序错乱
- [x] `f0bae286` fix(middleware): handle repeated tool call ids (#3143)

```bash
git cherry-pick 5fd0e6ac
git cherry-pick 20d2d2b3
git cherry-pick 0c37509b
git cherry-pick 181d8365
git cherry-pick f0bae286
```

**执行备注**

- `0c37509b` 的前端修改已适配 fork 现有拆分结构：隐藏控制消息名单放入 `frontend/src/core/messages/extraction.ts`，`grouping.ts` 继续通过 `isHiddenFromUIMessage()` 过滤，不恢复上游已删除的 `frontend/tests/unit/core/messages/utils.test.ts`。
- `181d8365` 与 `f0bae286` 均改动 `DanglingToolCallMiddleware` 同一段逻辑，本次采用最终队列式实现，支持非相邻 ToolMessage 归位与重复 tool call id 按出现顺序消费。

**验证**

- [ ] `make lint` 通过
- [x] middleware 相关测试通过: `uv run python -m pytest tests/test_dangling_tool_call_middleware.py tests/test_subagent_limit_middleware.py tests/test_summarization_middleware.py tests/test_todo_middleware.py -q`，112 passed
- [ ] 前端 typecheck: `pnpm typecheck` 当前失败于既有 test tsconfig/vitest 依赖问题（`src/core/threads/api-core.test.ts` BodyInit 类型、两个既有 vitest test 文件缺少 `vitest` 类型）；本批次未扩大该问题。
- [ ] 集成测试: agent 运行一轮完整对话，验证 tool_calls/ToolMessage 配对正确

## C: MCP + Runtime 修复 (Phase 5 + 6)

**优先级**: 🟡 Important
**策略**: 直接 cherry-pick
**预计耗时**: 45min

### C1: MCP 修复

- [x] `9afeaf66` Fix env resolution in MCP config lists (#2556)
- [x] `c881d958` fix(mcp): persist MCP sessions across tool calls for stateful servers (#3089) — 新增 MCPSessionPool，Playwright 等有状态 MCP server 不再丢失会话

```bash
git cherry-pick 9afeaf66
git cherry-pick c881d958
```

### C2: Runtime / RunManager 修复

- [x] `9b19cca9` fix(runtime): make RunManager.cancel() idempotent for already-interrupted runs (#3055) (#3058)
- [x] `1c5c5857` fix(runtime): bound write_file execution-failure observations (#3133)
- [x] `e19bec14` fix(task-tool): cancel and schedule deferred cleanup on polling safety timeout (#3097)
- [x] `2b1fcb3e` fix(task): remove max_turns parameter from task tool interface (#2783)
- [x] `45060a9f` fix(runtime): avoid postgres aggregate row lock (#2962) — 跳过，不适用于当前 fork 已删除的 `runtime/events/store/db.py` 旧事件存储路径

```bash
git cherry-pick 9b19cca9
git cherry-pick 1c5c5857
git cherry-pick e19bec14
git cherry-pick 2b1fcb3e
git cherry-pick 45060a9f
```

**执行备注**

- `c881d958` 与 fork 的 MCP sync wrapper / custom interceptor 支持有局部冲突；本次保留 fork 的 `_make_sync_tool_wrapper()`，叠加上游 `MCPSessionPool`、按 `(server_name, thread_id)` 复用 session、OAuth/custom interceptor 链路和 cache reset 时关闭 session pool。
- `e19bec14` 与当前 task tool 尚未引入 token usage L 系列逻辑有局部冲突；本次只采用 polling safety timeout 后的 cooperative cancel + deferred cleanup，不引入上游 token usage cache/reporting 依赖。
- `2b1fcb3e` 已移除 task tool model-facing `max_turns` 参数，继续使用 subagent config 中的 `max_turns`；保留 fork 当前 skills appendix 注入方式，待 D/L 相关批次再处理 subagent skill 注入架构。
- `45060a9f` 修改的 `runtime/events/store/db.py` 与 `test_run_event_store.py` 在当前 fork 中不存在；未恢复旧文件，记录为不适用，后续若重新引入 DB RunEventStore 再单独评估 Postgres advisory lock。

**验证**

- [ ] `make lint` 通过
- [ ] MCP server 连接测试，有状态 server 如 Playwright 不丢失会话
- [x] C 批次相关单元测试通过: `uv run python -m pytest tests/test_mcp_client_config.py tests/test_mcp_session_pool.py tests/test_cancel_run_idempotent.py tests/test_sandbox_tools_security.py tests/test_task_tool_core_logic.py -q`，149 passed
- [x] RunManager 取消操作幂等性测试

## D: Subagent + Memory 修复 (Phase 9 + 10)

**优先级**: 🟡 Important
**策略**: 逐个 cherry-pick，注意 `subagents/executor.py` 冲突
**预计耗时**: 45min

- [ ] `3acca126` fix(subagents): make subagent timeout terminal state atomic (#2583)
- [ ] `813d3c94` fix(subagents): consolidate system_prompt and skills into single SystemMessage (#2701)
- [ ] `722c690f` fix(memory): isolate queued memory updates by agent (#2941) — 按 agent + user 隔离 memory 队列

```bash
git cherry-pick 3acca126
git cherry-pick 813d3c94
git cherry-pick 722c690f
```

**冲突预警**

- [ ] `813d3c94` 修改 `subagents/executor.py`，fork 有定制，需手动解决

**验证**

- [ ] subagent 超时状态转换测试
- [ ] memory 隔离测试: 多 agent 并行写入不互相覆盖

## E: 前端修复 (Phase 11)

**优先级**: 🟡 Important
**策略**: 批量 cherry-pick，大部分应该无冲突
**预计耗时**: 1h

- [ ] `6c220a9a` fix(chat): prevent first user message from being swallowed in new conversations (#2731) — 修复首条消息被乐观清除
- [ ] `27559f36` fix(frontend): defer thread id to onStart to avoid 404 on new chat (#2749) — 修复新会话 404
- [ ] `7c42ab3e` fix(frontend): wait for async chat submit before clearing (#2940)
- [ ] `4538c322` Fix type check for 'thinking' in message content (#2964) — Gemini via Vertex AI 兼容修复
- [ ] `6d3cffb4` fix(frontend): deduplicate restored thread messages (#2958)
- [ ] `c0233cae` fix(frontend): resolve login page flickering and resize observer loop (#2954)
- [ ] `dfa4eb0c` [codex] fix follow-up suggestions layout (#2836)
- [ ] `222a7773` fix(frontend): avoid misleading error message when agent api is disable (#2697) (#2698)
- [ ] `aded753d` fix(frontend): restore localhost fallback for getGatewayConfig in prod mode (#2705) (#2718)

```bash
git cherry-pick 6c220a9a
git cherry-pick 27559f36
git cherry-pick 7c42ab3e
git cherry-pick 4538c322
git cherry-pick 6d3cffb4
git cherry-pick c0233cae
git cherry-pick dfa4eb0c
git cherry-pick 222a7773
git cherry-pick aded753d
```

**验证**

- [ ] `pnpm lint && pnpm typecheck` 通过
- [ ] 新会话首条消息不丢失
- [ ] 前端页面无 404/闪烁

## F: Sandbox + 通用修复 (Phase 12 + 13)

**优先级**: 🟢 Recommended
**策略**: 批量 cherry-pick，按文件分组
**预计耗时**: 2h

### F1: Sandbox 修复

- [ ] `8b697245` fix(sandbox): avoid blocking sandbox readiness polling (#2822)
- [ ] `2b5bece7` fix(harness): reset local sandbox singleton with provider lifecycle (#2834)
- [ ] `380255f7` fix(sandbox): uphold /mnt/user-data contract at Sandbox API boundary (#2873) (#2881)
- [ ] `e74e126e` fix(sandbox): scope provisioner PVC data by user (#2973)
- [ ] 跳过 `bd45cb28` fix(sandbox): disable msys path conversion (#2766) — Windows 专用

```bash
git cherry-pick 8b697245
git cherry-pick 2b5bece7
git cherry-pick 380255f7
git cherry-pick e74e126e
```

### F2: 通用修复

- [ ] `4ead2c6b` fix(config): reset config-backed singletons on hot reload (#2588)
- [ ] `ca3332f8` fix(gateway): return ISO 8601 timestamps from threads endpoints (#2599)
- [ ] `f80ac961` fix(harness): restore legacy skills path fallback (#2694) (#2696)
- [ ] `a814ab50` fix(skills): make security scanner JSON parsing robust for LLM output variations (#2987)
- [ ] `7a2670ea` fix(gateway): cap skill artifact preview size (#2963)
- [ ] `cef42243` fix(skills): enforce allowed-tools metadata (#2626) — skill 允许工具白名单
- [ ] `f1a0ab69` fix(tools): preserve tool_search promotions across re-entrant get_available_tools (#2885)
- [ ] `30a58462` fix(tools): make write_file append discoverable in model-facing schema (#2843)
- [ ] `7de9b582` fix(tools): introduce Runtime type alias to eliminate Pydantic serialization warning (#2774)
- [ ] `3599b570` fix(harness): wrap all async-only tools for sync clients (#2935)
- [ ] `bedbf229` fix(harness): wrap async-only config tools for sync client execution (#2878)
- [ ] `b6b3650e` fix(trace): memory 中文 in trace info is unicode escape sequence (#3104)
- [ ] `9c03a71a` fix(gateway): preserve message additional_kwargs in normalize_input (#3132) (#3136)
- [ ] `31513c2c` fix(persistence): emit tz-aware timestamps from SQLite-backed stores (#3130)
- [ ] `37db6893` fix(events): serialize structured db event content (#2762)
- [ ] `7a3c58a7` Fix duplicate gateway upload filenames (#2789)
- [ ] `70737af7` fix(nginx): resolve CSRF auth failure on non-standard ports (#2796)
- [ ] `c3bc6c7c` fix(nginx): defer CORS to gateway allowlist (#2861)
- [ ] `028493bf` fix(docker): force nginx to resolve upstream names at request time (#2717)
- [ ] `82e7936d` fix(docker): set UTF-8 locale to prevent ASCII encoding errors in minimal containers (#2707)
- [ ] `8cd4710b` fix(deploy): fall back to python/openssl when python3 is absent for secret generation (#3074)
- [ ] `9abe5a18` fix: clean up local nginx on stop (#3005)
- [ ] `1336872b` fix(channels): authenticate gateway command requests (#2742)
- [ ] `8e48b7e8` fix(channels): preserve clarification conversation history across follow-up turns (#2444)

```bash
git cherry-pick 4ead2c6b
git cherry-pick ca3332f8
git cherry-pick f80ac961
git cherry-pick a814ab50
git cherry-pick 7a2670ea
git cherry-pick cef42243
git cherry-pick f1a0ab69
git cherry-pick 30a58462
git cherry-pick 7de9b582
git cherry-pick 3599b570
git cherry-pick bedbf229
git cherry-pick b6b3650e
git cherry-pick 9c03a71a
git cherry-pick 31513c2c
git cherry-pick 37db6893
git cherry-pick 7a3c58a7
git cherry-pick 70737af7
git cherry-pick c3bc6c7c
git cherry-pick 028493bf
git cherry-pick 82e7936d
git cherry-pick 8cd4710b
git cherry-pick 9abe5a18
git cherry-pick 1336872b
git cherry-pick 8e48b7e8
```

**验证**

- [ ] `make lint` 通过
- [ ] sandbox 启动/停止/数据隔离测试
- [ ] gateway API 基本功能测试
- [ ] nginx 配置测试: CORS、CSRF、端口

## G: DynamicContextMiddleware (Phase 3)

**优先级**: 🔴 重要新架构
**策略**: 单独特性分支验证后合入
**预计耗时**: 3-4h
**决策状态**: ✅ 已决定采用

> 上游 v2.0 核心架构改动：将 memory + 日期从 system prompt 移至 DynamicContextMiddleware 注入的 `<system-reminder>` HumanMessage，使 system prompt 跨用户/会话字节完全一致，最大化 Anthropic/Bedrock prefix-cache 复用率。这是一个系列改动，需要一起应用。

> fork 的 `middleware_builder.py` 需要适配 DynamicContextMiddleware 的注册位置；`memory_middleware.py` 中关于注入 memory 到 system prompt 的逻辑被此系列替代。

- [ ] `c1b7f1d1` feat: static system prompt with DynamicContextMiddleware for prefix-cache optimization (#2801) — 核心 middleware + token usage 日志增强
- [ ] `881ff712` fix(harness): preserve dynamic context across summarization (#2823) — 摘要时保留 dynamic context
- [ ] `f76e4e35` fix title generation with dynamic context reminder (#2830) — title 生成兼容 dynamic context
- [ ] `08ee7ade` fix(lint): remove duplicate is_dynamic_context_reminder definition (#2837) — lint 清理

```bash
git checkout -b merge/dynamic-context merge/2026-05-22-upstream-sync

git cherry-pick c1b7f1d1
git cherry-pick 881ff712
git cherry-pick f76e4e35
git cherry-pick 08ee7ade
```

**冲突解决要点**

- [ ] `prompt.py`: 保留 fork 的 `user_id` 参数，删除 memory/date 注入逻辑
- [ ] `memory_middleware.py`: memory 注入逻辑被 DynamicContextMiddleware 替代
- [ ] `middleware_builder.py`: 添加 DynamicContextMiddleware 注册位置

**验证**

- [ ] system prompt 不再包含 memory/date 内容
- [ ] `<system-reminder>` 中正确注入 memory + 当前日期
- [ ] 摘要后 dynamic context 保留
- [ ] title 生成正常工作
- [ ] prefix-cache 命中率提升可观测，Anthropic API 响应中 `cache_read_input_tokens > 0`

```bash
git checkout merge/2026-05-22-upstream-sync
git merge merge/dynamic-context
git branch -d merge/dynamic-context
```

## H: Loop Detection 增强 (Phase 4)

**优先级**: 🟡 Important
**策略**: 单独分支验证
**预计耗时**: 2h

> 循环检测的三个独立改进：可配置化 + 延迟注入，修复 OpenAI/Moonshot 的 tool_calls 配对错误 + 注入时保持配对。

- [ ] `daa3ffc2` feat(loop-detection): make loop detection configurable with per-tool frequency overrides (#2711) — 新增 `LoopDetectionConfig`，支持 config.yaml 配置 + 每工具覆盖
- [ ] `e8675f26` fix(loop-detection): keep tool-call pairing on warn injection (#2724) (#2725)
- [ ] `dcc6f1e6` feat(loop-detection): defer warning injection (#2752) — 修复 warn 注入导致 OpenAI 拒绝的问题，将注入延迟到 wrap_model_call

```bash
git checkout -b merge/loop-detection merge/2026-05-22-upstream-sync

git cherry-pick daa3ffc2
git cherry-pick e8675f26
git cherry-pick dcc6f1e6
```

**冲突解决要点**

- [ ] `daa3ffc2` 触及 `agents/factory.py` 和 `agents/lead_agent/agent.py`，需与 fork 的 `middleware_builder.py` 协调
- [ ] fork 使用 `middleware_builder`，需在 builder 中注册 `LoopDetectionConfig.from_config()`
- [ ] 新增 `config.yaml` 中的 `loop_detection` 配置节

**验证**

- [ ] `config.yaml` 中 `loop_detection` 配置生效
- [ ] 循环检测 warn 注入不破坏 OpenAI tool_calls 配对
- [ ] 延迟注入在 `wrap_model_call` 阶段正确执行

```bash
git checkout merge/2026-05-22-upstream-sync
git merge merge/loop-detection
git branch -d merge/loop-detection
```

## I: Safety Termination (Phase 7)

**优先级**: 🟡 新功能
**策略**: 单独分支验证
**预计耗时**: 1.5h

> 当 LLM provider 因安全原因终止生成时，响应仍可能携带截断的 tool_calls。新增 `SafetyFinishReasonMiddleware` 检测并清除这些 tool_calls，避免 agent 进入重试循环。

- [ ] `be0eae98` fix(runtime): suppress tool execution when provider safety-terminates with tool_calls (#3035) — 新增 SafetyFinishReasonMiddleware + 检测器注册表

```bash
git checkout -b merge/safety-termination merge/2026-05-22-upstream-sync

git cherry-pick be0eae98
```

**冲突解决要点**

- [ ] 在 fork 的 `middleware_builder.py` 中注册 `SafetyFinishReasonMiddleware`

**验证**

- [ ] 模拟 provider safety termination，例如 `content_filter` finish_reason
- [ ] 确认截断的 tool_calls 被清除，不进入重试循环
- [ ] 正常 tool_calls 不受影响

```bash
git checkout merge/2026-05-22-upstream-sync
git merge merge/safety-termination
git branch -d merge/safety-termination
```

## J: Stability Audit P0 修复 (Phase 8)

**优先级**: 🟡 Important
**策略**: 手动适配，只提取适用的子修复
**预计耗时**: 2h

> v2.0-m1-rc1 稳定性审计修复，涉及 gateway config 热重载、task_tool callback manager 兼容、前端 subtask 状态机、导出过滤等。这是一个 mega commit。

- [ ] `e93f6584` fix(stability): resolve P0 blockers from v2.0-m1-rc1 stability audit (#3107) (#3131) — 手动适配

```bash
git checkout -b merge/stability-p0 merge/2026-05-22-upstream-sync

# 不直接 cherry-pick，而是手动提取子修复
git show e93f6584 > /tmp/stability-p0.patch
```

**提取项**

- [ ] task_tool callback manager 兼容 (BUG-002) — 直接适用
- [ ] 前端 subtask 状态机识别 `Error:` + `Task cancelled` + `Task polling timed out` (BUG-007) — 直接适用
- [ ] 前端导出过滤 hidden/reasoning/tool 消息 (BUG-006) — 直接适用
- [ ] gateway config 热重载 (BUG-001) — ✅ 已决定采用，需适配 fork 的 `gateway/app.py` 生命周期

**冲突预警**

- [ ] `gateway/app.py`、`gateway/deps.py` 的 config 生命周期变化: 去掉 `app.state.config`，改用 `get_app_config()` 热重载
- [ ] 需评估与 fork 的 gateway 层兼容性，前端部分可选择性提取

**验证**

- [ ] task_tool callback 正常工作
- [ ] subtask 错误状态正确显示
- [ ] 导出不包含 hidden/reasoning/tool 消息
- [ ] `get_app_config()` 热重载正确替代 `app.state.config`
- [ ] config 变更后无需重启 gateway
- [ ] 现有 fork 的 gateway 中间件和依赖注入不受破坏

```bash
git checkout merge/2026-05-22-upstream-sync
git merge merge/stability-p0
git branch -d merge/stability-p0
```

## K: 新功能直接 cherry-pick (Phase 14)

**优先级**: 🟢 Recommended
**策略**: 直接 cherry-pick
**预计耗时**: 30min

- [ ] `44ab21fc` feat(community): add Serper web search provider (#2630) — 新增 Serper 搜索 provider
- [ ] `e37912e2` feat(sandbox): Adds download file interface in Sandbox (#3038) — sandbox 文件下载接口
- [ ] `923f516d` feat(trace): LangGraph -> lead_agent and set custom agent_name to run_name (#3101) — trace 改进
- [ ] `eab7ae3d` feat: stream subagent token usage to header via terminal task events (#2882)
- [ ] `4063dd71` feat(debug): print presented file paths with physical resolution (#2825)
- [ ] `680187dd` fix: Supplement list_running in RemoteSandboxBackend (#2716)

```bash
git cherry-pick 44ab21fc
git cherry-pick e37912e2
git cherry-pick 923f516d
git cherry-pick eab7ae3d
git cherry-pick 4063dd71
git cherry-pick 680187dd
```

**验证**

- [ ] Serper provider 配置可选
- [ ] sandbox 文件下载功能可用
- [ ] trace 中 agent_name 正确标记

## L: 新功能手动适配 (Phase 15)

**优先级**: 🟡 Important，架构性
**策略**: 每个系列单独分支 + 手动适配
**预计耗时**: 10-14h，是最耗时批次
**决策状态**: 多项已决定采用

### L1: Token Usage 显示体系重构

**决策**: 后端归因系统全盘采用上游；前端以 fork 的 turn-anchored 渲染 + `useTweenNumber` 动画为基础，吸收上游的 `step_debug` 模式和 header preset 切换。默认展示为 `per_turn` 模式。

- [ ] `d02f762a` feat: refine token usage display modes (#2329) — 后端 middleware 全盘采用；前端保留 fork 的 splitTurns + tween 动画，加入 debug 模式和 preset 切换
- [ ] `866d1ca4` Populate Codex usage metadata for token accounting (#2585)
- [ ] `bb8b234d` chore(2585): keep polishing the code of codex token usage (#2689)
- [ ] `530bda71` fix: dedupe token usage aggregation by message id (#2770)
- [ ] `41741608` fix: use backend thread token usage for header total (#2800)
- [ ] `5127f08e` enable token usage by default (#2841)
- [ ] `9892a7d4` fix: bucket subagent token usage into parent run totals (#2838)
- [ ] `2a1ac06b` fix(persistence): reuse token usage model grouping expression (#2910)
- [ ] `2eeb5979` fix(runs): expose active progress counters (#3148)

```bash
git checkout -b merge/token-usage merge/2026-05-22-upstream-sync

git cherry-pick d02f762a
git cherry-pick 866d1ca4
git cherry-pick bb8b234d
git cherry-pick 530bda71
git cherry-pick 41741608
git cherry-pick 5127f08e
git cherry-pick 9892a7d4
git cherry-pick 2a1ac06b
git cherry-pick 2eeb5979
```

**前端手动适配**

- [ ] 保留 fork 的 `splitTurns()` + `useTweenNumber` 动画
- [ ] 从上游吸收 `step_debug` 展示模式
- [ ] 从上游吸收 header DropdownMenu preset 切换: `per_turn` / `per_run` / `step_debug` / `off`
- [ ] 默认展示模式设为 `per_turn`

**验证**

- [ ] 后端 token usage 归因正确: thinking / final_answer / tool_batch / subagent
- [ ] 前端 `per_turn` 模式下 `useTweenNumber` 动画平滑
- [ ] `step_debug` 模式可切换并正确显示
- [ ] header total 使用后端线程级汇总

### L2: app_config 穿透重构

**决策状态**: ✅ 已决定采用

- [ ] `8ba01dfd` refactor: thread app_config through lead and subagent task path (#2666) — 19 files, 769+ lines

```bash
git checkout -b merge/app-config merge/2026-05-22-upstream-sync

git cherry-pick 8ba01dfd
```

**冲突解决要点**

- [ ] fork 的 `middleware_builder.py` 需要接收 `app_config` 参数
- [ ] `agents/lead_agent/agent.py` 大量定制，逐段适配
- [ ] `agents/factory.py` 适配 `app_config` 传入

**验证**

- [ ] lead/subagent/task 路径不再隐式依赖 `get_app_config()`
- [ ] agent 创建流程正常工作
- [ ] config 变更不需要重启即可生效

### L3: RunStore 持久化 + 中断状态

**决策状态**: ✅ 已决定采用
**说明**: 上游 breaking change，`RunManager` 改为从 `RunStore` 混合读取，支持 gateway 重启后恢复历史 run。

- [ ] `c810e9f8` fix(harness)!: hydrate runs from RunStore and persist interrupted status (#2932)
- [ ] `39f901d3` fix(runs): restore historical runs from persistent store after gateway restart (#2989)

```bash
git checkout -b merge/run-store merge/2026-05-22-upstream-sync

git cherry-pick c810e9f8
git cherry-pick 39f901d3
```

**验证**

- [ ] gateway 重启后历史 run 可恢复
- [ ] 中断的 run 状态正确持久化
- [ ] `RunManager.get()` async 调用链正确

### L4: Custom Agent 自更新

**决策状态**: ✅ 已决定采用
**说明**: 新增 `update_agent` 内置工具，支持自定义 agent 在聊天中自行更新 `SOUL.md` / `config.yaml` + 用户隔离。

- [ ] `59c4a3f0` feat(agent): add custom-agent self-updates with user isolation (#2713) — 18 files, 956+ lines

```bash
git checkout -b merge/custom-agent merge/2026-05-22-upstream-sync

git cherry-pick 59c4a3f0
```

**冲突解决要点**

- [ ] fork 已有 `user_id` 隔离逻辑，需与上游的 user isolation 合并
- [ ] `agents_config.py` 和 `paths.py` 中两套隔离逻辑需统一

**验证**

- [ ] `update_agent` 工具可用
- [ ] agent 自更新 `SOUL.md` / `config.yaml` 后立即生效
- [ ] 用户隔离: 用户 A 的修改不影响用户 B

### L5: model_name 穿透到持久层

- [ ] `de253e4a` feat(run): Propagates model_name from gateway to SQLite (#2775)

```bash
git cherry-pick de253e4a
```

### L6: Langfuse Tracing 增强

**决策状态**: ✅ 已决定采用
**说明**: 将 Langfuse callback 从 model 级移到 graph root，传播 `session_id` / `user_id` / `trace_name` / `tags`。

- [ ] `df951542` fix(tracing): propagate session_id and user_id into Langfuse traces (#2944) — 19 files, 910 lines

```bash
git cherry-pick df951542
```

**冲突解决要点**

- [ ] 涉及 fork 定制的 `agents/lead_agent/agent.py` 和 `models/factory.py`
- [ ] Langfuse callback 从 model 级移到 graph root，需在 fork 的 agent 构建流程中适配
- [ ] 保留 fork 的 `user_id` 传播路径，确保与上游的 `session_id` / `user_id` / `trace_name` 注入合并

**验证**

- [ ] Langfuse trace 中正确显示 `session_id` 和 `user_id`
- [ ] `trace_name` 和 `tags` 正确传播
- [ ] 不影响现有 agent 运行流程

## M: Auth 独立修复 (Phase 16)

**优先级**: 🟢 Recommended
**策略**: 直接 cherry-pick
**预计耗时**: 15min

> 以下 auth 修复独立于上游的 auth 大重构，可单独适用。

- [x] `6d611c2b` fix(auth): persist auto-generated JWT secret to survive restarts (#2933)
- [x] `b5108e35` fix(auth): replace setup-status 429 rate limit with cached response (#2915)

```bash
git cherry-pick 6d611c2b
git cherry-pick b5108e35
```

**执行备注**

- `6d611c2b` 已采用运行时代码与 `test_auth_config.py` 中的 JWT secret 持久化测试；未恢复上游 `backend/docs/AUTH_UPGRADE.md`，因为该文档描述了当前 fork 尚未完整采用的 `/initialize` 首次 admin 创建流程。
- `b5108e35` 仅移植 `/setup-status` per-IP cache 与 single-flight 查询逻辑，保留 fork 当前 `count_users()` 判定与 `username` / `display_name` 响应结构，不引入上游 auth 初始化端点。

**验证**

- [ ] JWT secret 在 gateway 重启后保持一致
- [ ] setup-status 接口不再被 rate limit 阻断

## 合并完成后

- [ ] 全量测试

```bash
make lint
make test
pnpm lint && pnpm typecheck
```

- [ ] 集成测试: 启动 gateway + frontend，运行完整对话流程
- [ ] 合入 main

```bash
git checkout main
git merge merge/2026-05-22-upstream-sync
```

- [ ] 推送

```bash
git push origin main
```

- [ ] 清理临时分支

```bash
git branch -d merge/2026-05-22-upstream-sync
git branch -d merge/dynamic-context merge/loop-detection merge/safety-termination merge/stability-p0
git branch -d merge/token-usage merge/app-config merge/run-store merge/custom-agent
```

## 依赖升级 (独立处理，不 cherry-pick)

> 在所有功能合并完成后，单独 PR 处理依赖升级。

| 包 | 变更 |
|---|---|
| langsmith | -> 0.8.0 |
| langchain-core | -> 1.3.3 |
| next | 16.1.7 -> 16.2.6 |
| uuid (frontend) | -> 14.0.0 |
| urllib3 | -> 2.7.0 |
| idna | -> 3.15 |
| python-multipart | -> 0.0.27 |
| mako | -> 1.3.12 |
| brace-expansion (frontend) | -> 5.0.5 |

```bash
git checkout -b chore/deps-upgrade-2026-05

# 后端
pip install langsmith==0.8.0 langchain-core==1.3.3 urllib3==2.7.0 idna==3.15 python-multipart==0.0.27 mako==1.3.12
# 更新 requirements.txt / pyproject.toml

# 前端
cd frontend && pnpm update next@16.2.6 uuid@14.0.0
```

## 跳过内容

| Commit(s) | 说明 | 跳过理由 |
|-----------|------|----------|
| `48e038f7` | feat(channels): enhance Discord with mention-only mode, thread routing, and typing indicators (#2842) | fork 已移除 Discord |
| `af6e48cc` | fix(i18n): add Chinese translations for account settings page (#2712) | 属于上游 auth 重构的 UI |
| `b10eb7ba` | feat(github): Added container push workflow (#2709) | CI workflow，fork 不用 |
| `94da8f67` | fix(scripts): preserve uv extras across `make dev` restarts (#2754) | 开发脚本，fork 有自己的 Makefile |
| `ca7042de` | chore(windows): add PYTHONIOENCODING and PYTHONUTF8 to backend Makefile targets (#3069) | Windows Makefile，fork 不需要 |
| `0c223490` | chore(dev): add async/thread boundary detector (#2936) | 开发工具 |
| `6e8e6a96` | test: add blocking IO detector (#2924) | 测试工具 |
| `6b922e49` | test(runtime): add lifecycle e2e coverage (#2946) | 测试 |
| `b69ca7ad` | test(middleware): lock tool-call transcript boundary invariants (#3049) | 测试 |
| `0d1053ca` | fix(uploads): add Windows support for safe symlink-protected uploads (#2794) | Windows 专用 |
| `914d6a4f`, `253542ea`, `4cb2a224`, `506be8bf`, `f734e14d`, `84f88b66`, `e82b2fb4` | docs 系列 | 文档站/独立文档 |
| `00096554`, `1f978393`, `ba864112`, `b1ec7e81`, `00694823`, `109490da`, `14c0a32e`, `1edc9d9f`, `41b04a55` | chore(deps) 系列 | 依赖升级单独处理 |
| `1c96a6af` | fix: keep new agent bootstrap in user scope (#2784) | 属于 `59c4a3f0` custom-agent 系列，一起处理 |
| `68d8caec` | fix(agents): make update_agent honor runtime.context user_id (#2867) | 属于 `59c4a3f0` custom-agent 系列 |
| `e9deb6c2` | perf(harness): push thread metadata filters into SQL (#2865) | 属于持久化重构系列 |
| `2eb11f97` | fix(runtime): persist run message summaries (#2850) | 依赖 RunStore 重构 |
| `7caf03e9` | fix(packaging): add postgres extra for store/checkpointer (#2584) | packaging 修复 |
| `17447fcc` | fix(runtime): make rollback restore checkpoint supersede newer checkpoints (#2582) | 依赖 RunStore 重构 |
| `c1b7f1d1` 中 nginx 修复部分 | 已在核心 commit 中 | 仅 nginx 部分不单独列出 |

## 全局冲突预警

| Commit | 预期冲突点 | 处理策略 |
|--------|-----------|----------|
| `c1b7f1d1` (DynamicContext) | `prompt.py` 中 memory/date 注入逻辑，`memory_middleware.py` | 保留 fork 的 `user_id` 参数，采纳 middleware 拆分方案 |
| `daa3ffc2` (LoopDetection) | `factory.py`、`lead_agent/agent.py` | fork 用 `middleware_builder`，需在 builder 中注册 `from_config` |
| `be0eae98` (SafetyFinish) | `lead_agent/agent.py` middleware 注册 | 在 fork 的 `middleware_builder.py` 中添加注册 |
| `e93f6584` (Stability P0) | `gateway/app.py`、`gateway/deps.py` | 选择性提取，评估 config 生命周期变化 |
| `cef42243` (allowed-tools) | `lead_agent/agent.py`、`lead_agent/prompt.py`、`subagents/executor.py` | fork 的 `agent.py` 有大量定制 |
| `59c4a3f0` (custom-agent) | `agents_config.py`、`paths.py` | fork 已有 `user_id` 路径，需合并两套隔离逻辑 |
| `813d3c94` (subagent SystemMessage) | `subagents/executor.py` | fork 的 executor 有定制 |

## 上次延后项状态

| 延后项 | 状态 | 本次建议 |
|--------|------|----------|
| `487c1d93` fix(subagents): use model override for tools and middleware (#2641) | 仍未合并 | 继续延后，上游 `8ba01dfd` app_config 重构已涵盖部分动机 |
| `c09c3345` fix(harness): resolve runtime paths from project root (#2642) | 仍未合并 | 继续延后 |
| `8939ccae` fix(uploads): enforce streaming upload limits in gateway (#2589) | 仍未合并 | 继续延后 |
| `30d619de` feat(subagents): support per-subagent skill loading (#2253) | 仍未合并 | 继续延后，`cef42243` allowed-tools 提供了部分能力 |
| `c42ae3af` / `3a611268` debug.py 增强 | 仍未合并 | 继续延后 |
| `db5ad863` chat history loading hooks | 仍未合并 | 继续延后 |
| `78633c69` propagate agent_name into ToolRuntime.context | 仍未合并 | 继续延后 |
| `1ad1420e` refactor(skills): Unified skill storage | 仍未合并 | 继续延后 |
| Phase 8 依赖升级 | 部分已升级 | 参见本文档依赖升级节 |

## 时间估算汇总

| 批次 | 预计耗时 | 累计 |
|------|----------|------|
| A: 安全修复 | 30min | 30min |
| B: Middleware | 1h | 1.5h |
| C: MCP + Runtime | 45min | 2.25h |
| D: Subagent + Memory | 45min | 3h |
| E: 前端修复 | 1h | 4h |
| F: Sandbox + 通用 | 2h | 6h |
| G: DynamicContext | 3-4h | 9-10h |
| H: Loop Detection | 2h | 11-12h |
| I: Safety Termination | 1.5h | 12.5-13.5h |
| J: Stability P0 | 2h | 14.5-15.5h |
| K: 新功能 cherry-pick | 30min | 15-16h |
| L: 新功能手动适配 | 10-14h | 25-30h |
| M: Auth 修复 | 15min | 25-30h |
| 最终验证 | 2h | 27-32h |

## 里程碑检查点

| 日期 | 目标 | 包含批次 |
|------|------|----------|
| Day 1 | 安全 + 关键修复 | A + B + C |
| Day 2 | 功能修复完成 | D + E + F |
| Day 3 | 架构改动验证 | G + H + I |
| Day 4 | 手动适配 | J + K + L(部分) |
| Day 5 | 手动适配 + 收尾 | L(完成) + M + 最终验证 |

## 已确认决策

- [x] Langfuse Tracing (L6): 本轮采用，手动适配 fork 的 agent/model factory
- [x] Stability P0 的 gateway config 热重载: 采用，适配 fork 的 gateway 层
- [x] DynamicContextMiddleware: 本轮采用，迁移 memory/date 到 dynamic context reminder
- [x] app_config 穿透重构: 本轮采用，减少隐式全局配置依赖
- [x] RunStore 持久化 + 中断状态: 本轮采用，支持 gateway 重启恢复历史 run
- [x] Custom Agent 自更新: 本轮采用，需与 fork 的 user_id 隔离合并
- [ ] 依赖升级时机: 合并完成后单独 PR 处理
