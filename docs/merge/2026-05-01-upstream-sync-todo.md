# 合并计划: upstream/main → main (2026-05-01)

## 基本信息

| 项目 | 内容 |
|---|---|
| 日期 | 2026-05-01 |
| 合并来源 | `upstream/main` (bytedance/deer-flow) |
| 合并目标 | `main` (scientific-tumbleweed-fork) |
| 上次合并点 | `092bf13f` fix(makefile): route Windows shell-script targets through Git Bash |
| 上游 tip | `189b8240` fix(sandbox): pass no_change_timeout to exec_command to prevent 120s premature termination (#2685) |
| 待处理上游 commit 数 | 146 个 (不含 merge) |
| 预计可直接 cherry-pick | ~68 个 |
| 预计需手动适配 | 2 个 |

---

## Phase 1: 安全修复 (🔴 最高优先级)

- [x] ~~`74081a85` [security] fix(sandbox): bind local Docker ports to loopback (#2633)~~
- [x] ~~`80e210f5` [security] fix(uploads): require explicit opt-in for host-side document conversion (#2332)~~
- [x] ~~`6bd88fe1` fix(sandbox): block host bash traversal escapes (#2560)~~
- [x] ~~`39c5da94` fix(sandbox): prevent local custom mount symlink escapes (#2558)~~
- [x] ~~`707ed328` fix(skills): scan skill archives before install (#2561)~~
- [x] ~~`f7dfb88a` fix(aio-sandbox): redact env values in container logs (#2562)~~
- [x] ~~`af8c0cfb` fix(harness): constrain view_image to thread data paths (#2557)~~
- [x] ~~`2176b2bb` fix: validate bootstrap agent names before filesystem writes (#2274)~~
- [x] ~~`0691c4dd` fix(security): allow disabling API docs in production via GATEWAY_ENABLE_DOCS (#2651)~~
- [x] ~~`950821cb` fix: use subprocess instead of os.system in local_backend.py (#2494)~~
- [x] ~~`02569136` fix(sandbox): improve sandbox security and preserve multimodal content (#2114)~~
- [x] ~~`ca1b7d5f` fix(sandbox): add missing path masking in ls_tool output (#2317)~~
- [x] ~~`12214480` fix(scripts): Cloud Provider Reports Security Issue (aliyun cloud) (#2323)~~

## Phase 2: Memory 系统修复 (🔴 Critical)

⚠️ `898f4e8a` 和 `07fc25d2` 需注意保留 fork 的 `user_id` 字段

- [x] ~~`898f4e8a` fix: Memory update system has cache corruption, data loss, and thread-safety bugs (#2251)~~
- [x] ~~`87609374` fix(memory): use asyncio.to_thread for blocking file I/O in aupdate_memory (#2220)~~
- [x] ~~`c0da2782` fix(memory): replace short-lived asyncio.run() with persistent event loop (#2627)~~
- [x] ~~`4ba3167f` feat: flush memory before summarization (#2176)~~
- [x] ~~`07fc25d2` feat: switch memory updater to async LLM calls (#2138) — **跳过：已被 c0da2782 覆盖**~~

## Phase 3: Middleware & Agent 修复 (🟡 Important)

⚠️ `5db71cb6` 需检查 fork 的 middleware chain builder 兼容性

- [x] ~~`5b633449` fix(middleware): add per-tool-type frequency detection to LoopDetectionMiddleware (#1988)~~
- [x] ~~`5db71cb6` fix(middleware): repair dangling tool-call history after loop interruption (#2035)~~
- [x] ~~`e4f896e9` fix(todo-middleware): prevent premature agent exit with incomplete todos (#2135)~~
- [x] ~~`f4c17c66` fix(middleware): fix present_files thread id fallback (#2181)~~
- [x] ~~`f9ff3a69` fix(middleware): avoid rescuing non-skill tool outputs during summarization (#2458)~~
- [x] ~~`5ba1dacf` fix: rename present_file to present_files in docs and prompts (#2393)~~
- [x] ~~`8b61c94e` fix: keep lead agent graph factory signature compatible (#2678) — **跳过：依赖上游 `_get_runtime_config` 重构，fork 中不存在**~~

## Phase 4: Subagent 修复 (🟡 Important)

⚠️ `83938cf3` 需确认 fork 的 user_id 传播路径；`487c1d93` 建议手动移植

- [x] ~~`55474011` fix(subagent): inherit parent agent's tool_groups in task_tool (#2305)~~
- [x] ~~`d78ed5c8` fix: inherit subagent skill allowlists (#2514)~~
- [x] ~~`7dea1666` fix: avoid temporary event loops in async subagent execution (#2414)~~
- [x] ~~`b9709934` fix: read lead agent options from context (#2515)~~
- [x] ~~`83938cf3` fix(subagents): propagate user context across threaded execution (#2676)~~
- [ ] `487c1d93` fix(subagents): use model override for tools and middleware (#2641) — **手动移植，延后**

## Phase 5: 前端修复 (🟡 Important)

- [x] ~~`24a5a006` fix: avoid duplicate call to extractReasoningContentFromMessage (#2661)~~
- [x] ~~`7c87dc5b` fix(reasoning): prevent LLM-hallucinated HTML tags from rendering as DOM elements (#2321)~~
- [x] ~~`ef041741` Fix invalid HTML nesting in reasoning trigger during complex task rendering (#2382)~~
- [x] ~~`c91785dd` fix(title): strip \<think\> tags from title model responses and assistant context (#1927)~~
- [x] ~~`0e16a7fe` fix(frontend): make Suggestion button opaque in dark mode (#2276)~~
- [x] ~~`4d3038a7` fix(frontend): stop artifact panel from auto-opening on rehydrated write_file (#2278)~~
- [x] ~~`f2013f47` fix command palette hydration mismatch (#2301)~~
- [x] ~~`35fb3dd6` fix(frontend): resolve /mnt/ links in markdown to artifact API URLs (#2243)~~
- [x] ~~`772538dd` fix(frontend): add skills API rewrite rule to prevent HTML fallback (#2241)~~
- [x] ~~`c2332bb7` fix memory settings layout overflow (#2420)~~

## Phase 6: 其他通用修复

- [x] ~~`189b8240` fix(sandbox): pass no_change_timeout to exec_command to prevent 120s premature termination (#2685)~~
- [ ] `c09c3345` fix(harness): resolve runtime paths from project root (#2642) — **延后：冲突面广，涉及 paths/skills storage 重构**
- [ ] `8939ccae` fix(uploads): enforce streaming upload limits in gateway (#2589) — **延后：uploads router 冲突面广，需手动移植**
- [x] ~~`eba3b9e1` fix(config): unify log_level from config.yaml across Gateway and debug entry points (#2601)~~
- [x] ~~`11afd324` Fix the log Injection error of skills.py — **手动应用 sanitization**~~
- [x] ~~`a664d2f5` fix(checkpointer): create parent directory before opening SQLite in sync provider (#2272)~~
- [x] ~~`1df389b9` fix: wrap blocking readability call with asyncio.to_thread in web_fetch (#2157)~~
- [x] ~~`a62ca5dd` fix: Catch httpx.ReadError in the error handling (#2309)~~
- [x] ~~`f514e35a` fix(backend): make clarification messages idempotent (#2350) (#2351)~~
- [x] ~~`55bc09ac` fix(backend): fix uploads for mounted sandbox providers (#2199)~~
- [x] ~~`dc50a7fd` fix(sandbox): resolve paths in read_file/write_file content for LocalSandbox (#1935)~~
- [x] ~~`e8572b9d` fix(jina): log transient failures at WARNING without traceback (#2484) (#2485)~~
- [x] ~~`24fe5fbd` fix(mcp): prevent RuntimeError from escaping except block in get_cache (#2252)~~
- [x] ~~`053e18e1` fix(skills): avoid blocking custom skill deletion on readonly history writes (#2197)~~
- [x] ~~`6dce26a5` fix: resolve tool duplication and skill parser YAML inconsistencies (#2107)~~
- [x] ~~`fc94e90f` fix(setup-agent): prevent data loss when setup fails on existing agent (#2254)~~
- [x] ~~`c99865f5` fix(token-usage): enable stream usage for openai-compatible models (#2217)~~
- [x] ~~`1f59e945` fix: cap prompt caching breakpoints at 4 to prevent API 400 errors (#2449)~~
- [x] ~~`ec8a8cae` fix: gate deferred MCP tool execution (#2513)~~
- [x] ~~`4e72410` fix(gateway): bound lifespan shutdown hooks to prevent worker hang under uvicorn reload (#2331)~~
- [x] ~~`c43c803f` fix: remove mismatched context param in debug.py to suppress Pydantic warning (#2446)~~
- [x] ~~`085c13ed` fix: remove unnecessary f-string prefixes and unused import (#2352)~~

## Phase 7A: 新功能 — 直接 cherry-pick

- [x] ~~`4d4ddb3d` feat(llm): introduce lightweight circuit breaker to prevent rate-limit bans (#2095)~~
- [x] ~~`105db009` feat: show token usage per assistant response (#2270)~~
- [x] ~~`f394c0d8` feat(mcp): support custom tool interceptors via extensions_config.json (#2451)~~
- [x] ~~`b90f219b` fix(skills): validate bundled SKILL.md front-matter in CI (#2457)~~
- [x] ~~`11f557a2` feat(trace): Add run_name to the trace info for system agents (#2492)~~

## Phase 7B: 新功能 — 手动适配

- [ ] `30d619de` feat(subagents): support per-subagent skill loading and custom subagent types (#2253) — 适配 fork 的 Explore/Plan/Verification 子智能体

## Phase 8: 依赖升级 (独立处理，不 cherry-pick)

- [ ] langsmith 0.6.4 → 0.7.31
- [ ] langchain-core 1.2.17 → 1.2.28
- [ ] langsmith (frontend) 0.5.2 → 0.5.18
- [ ] pillow 12.1.1 → 12.2.0
- [ ] python-multipart 0.0.22 → 0.0.26
- [ ] python-dotenv 1.2.1 → 1.2.2
- [ ] lxml 6.0.2 → 6.1.0
- [ ] pytest 9.0.2 → 9.0.3
- [ ] uuid (frontend) 13.0.0 → 14.0.0
- [ ] dompurify (frontend) 3.3.1 → 3.4.1
- [ ] langchain-ollama, ollama — 新增 optional deps

## Phase 9: 可选功能 (按需)

- [ ] `c42ae3af` feat: add optional prompt-toolkit support to debug.py (#2461) — **延后：debug.py 已大改，需手动适配**
- [ ] `3a611268` fix: keep debug.py interactive terminal free from background log noise (#2466) — **延后：同上**
- [ ] `db5ad863` feat: enhance chat history loading with new hooks and UI components (#2338)
- [x] ~~`410f0c48` fix(channels): accept single slack allowed user (#2481)~~
- [x] ~~`9dc25987` fix(channels): update the logger for the channel config (#2524)~~
- [ ] `78633c69` fix(agents): propagate agent_name into ToolRuntime.context for setup_agent (#2679) — **延后：runtime layer 冲突面广**
- [x] ~~`692f7945` fix(gateway): forward agent_name and is_bootstrap from context to configurable (#2242) — **已包含在之前的合并中**~~

---

## 跳过内容

| Commit(s) | 说明 | 跳过理由 |
|-----------|------|----------|
| `08afdcb9` | feat(channels): add DingTalk channel integration (#2628) | fork 已移除 DingTalk |
| `c4d273a6` | feat(channels): add Discord channel integration (#1806) | fork 已移除 Discord |
| `88f822a8`, `814a488b`, `716cae20` | docs: 文档站内容填充 | 与上次一样跳过文档站 |
| `44d9953e` | feat: Add metadata to documentation pages in Chinese | 文档站 |
| `979a461a` | docs: move completed async migration to Completed Features | 文档 |
| `c6b04235` | feat(frontend): add Playwright E2E tests with CI workflow (#2279) | fork 已移除 E2E workflow |
| `4efc8d40` | feat(frontend): set up Vitest frontend testing infrastructure (#2147) | fork 已移除前端测试 workflow |
| `8a044142` | feat(dev): add pre-commit hooks for ruff, eslint, prettier (#2525) | fork 已移除 pre-commit |
| `2bb1a2df`, `395c1435` | feat(models): Provider for MindIE model engine | 特定硬件适配，不需要 |
| `ac04f270` | feat(subagents): allow model override per subagent (#2064) | fork 已有完整实现 |
| `35ef8b7c` | feat: add default database configuration for AppConfig | 属于 auth 重构系列 |
| 多个 lint fix (Willem Jiang) | fix lint errors in frontend/backend | 上游 CI 修复，不适用 |
| `98a5b34f` | fix: resolve merge conflict in pnpm-lock.yaml | 上游合并冲突解决 |
| `748429ef` | fix(frontend): add missing mock routes | 上游测试基础设施 |
| `f7b10d42` | fix(frontend): create thread on first submit in new-agent page (#2656) | 属于 API 重构 |
| `88d47f67` | fix(nginx): add catch-all /api/ location for auth routes (#2657) | 属于 auth 重构 |
| `ed9ebfac` | fix: enforce 'request' parameter in require_auth decorator | 属于 auth 重构 |
| `3b71e2d3` | feat: add request parameter to generate_suggestions endpoint | 属于 API 重构 |
| `69649d8a` | Fix the issues when reviewing 2566 persistent part (#2604) | 属于持久化重构 |
| `8e359131` | test: add unit tests for ViewImageMiddleware (#2256) | 测试 |
| `d8ecaf46`, `56d5fa33`, `2e05f380` | 持久化重构系列 (3 commits, 61-66 files each) | fork 已有不同架构的用户隔离 |
| `94eee95f`, `848ace98`, `00a90bbd` | Auth 重构系列 (92+ files) | fork 有独立 JWT auth 系统 |
| `7bf618de`, `da174dfd` | Gateway API / internal auth 重构 | 依赖持久化重构 |
| `4e4e4f92` | fix(security): harden auth system (#2593) | 依赖上游 auth 架构 |
| `38714b6c`, `e82940c0`, `b8bc4826` | Middleware 配置传递重构 | fork 有 canonical middleware builder，提取思路独立实现 |
| `1ad1420e` | refactor(skills): Unified skill storage (#2613) | 延后至下轮合并 |

---

## 冲突预警

以下 commit 在 cherry-pick 时可能需要手动解决冲突：

| Commit | 预期冲突点 | 处理策略 |
|--------|-----------|----------|
| `898f4e8a` | memory 模块的 `user_id` 字段 | 保留 fork 的 `user_id`，采纳上游的线程安全修复 |
| `07fc25d2` | memory updater 的 `get_memory_data(user_id)` | 保留 fork 的 `user_id` 参数，采纳 async LLM 调用 |
| `5db71cb6` | middleware chain 位置 | 检查 fork 的 `middleware_builder.py` 中对应位置 |
| `83938cf3` | user context 传播路径 | 确认 fork 的 user_id 传播与上游 user context 兼容 |
| `487c1d93` | `build_subagent_runtime_middlewares()` 签名 | 手动将 `app_config` + `model_name` 参数加入 fork 的实现 |
| `8b61c94e` | lead agent graph factory 签名 | 检查 fork 的 agent.py 签名是否已有差异 |
