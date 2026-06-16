# upstream/main -> main 合并执行计划 (2026-06-15)

本文档把上一版“选择性同步建议”改为执行清单。目标不是整枝 merge `upstream/main`，而是按人类意见中已经标记“采纳/采纳吸收”的点，逐块手工移植、逐块验证、逐块停止。

## 基本信息

| 项目 | 内容 |
|---|---|
| 日期 | 2026-06-15 |
| 合并来源 | `upstream/main` |
| 合并目标 | `main` |
| source tip | `25fbd25b` |
| target tip | `aab3d891` |
| 本地 source mirror | `source/deerflow...upstream/main = 0 405`，不得以 stale mirror 为准 |
| 执行原则 | 不整枝 merge；不整文件覆盖；每个点先写测试/验证面，再手工移植 |

## 执行规则

- [x] 每个执行点开始前先确认工作树中已有 dirty state，不回滚非本点文件。
- [x] 每个执行点只触碰其 Boundaries 中列出的文件；若必须越界，先停止并更新本计划。
- [x] 每个执行点完成后把实际验证命令、失败旧债和剩余 tradeoff 回写到本文件。
- [x] 所有上游内容都要改成本项目语境，禁止带入 DeerFlow branding、landing/blog/docs 站内容。
- [x] `deerflow.*` 继续不得 import `app.*`；前端不得暴露 provider、host、token 或 API key 细节。

## 待商定 Tradeoff

- [x] **T1 Docker socket overlay 粒度**：已采用备选方案，默认不挂载 Docker socket；仅 DooD overlay 同时覆盖 gateway/langgraph，以兼容两种 runtime 入口。
- [x] **T2 CLI auth 安全文档落点**：已采用推荐方案，写入 `backend/docs/CONFIGURATION.md`；root `SECURITY.md` 本轮不恢复。
- [x] **T3 Gateway workers 默认值**：已采用推荐方案，同步改为 `GATEWAY_WORKERS=1`；如果未来要恢复多 worker，需要先补共享 run/stream state。
- [x] **T4 MCP 用户可见配置形态**：已采用推荐方案，普通用户走 catalog/effective view 与 per-user enabled toggle；完整 MCP config 留给未来 admin endpoint。
- [x] **T5 Upload limits 来源**：已采用推荐方案，新增 app-level `max_files/max_file_size/max_total_size`，并保持与现有 nginx body limit 分层约束。
- [x] **T6 Human message 纯文本**：已采用推荐方案，human message 纯文本渲染；assistant Markdown/KaTeX/citation 链路保留。
- [x] **T7 Tool output 外部化存储**：已采用推荐方案，先放 thread-local outputs；是否进入 OpenDAL 持久存储另开任务。
- [x] **T8 Subagent frontend 测试基础设施**：已采用推荐方案，暂不引入 Vitest/Playwright；本轮以后端 contract 与 `pnpm check` 为主。
- [x] **T9 Memory token_counting 默认值**：已采用推荐方案，默认 `tiktoken`，网络受限部署可显式设 `char`。
- [x] **T10 Run shutdown 语义**：已采用推荐方案，shutdown 时把未完成 run 标记为 `interrupted`，drain timeout 先定 5s。
- [x] **T11 MCP deferred registry 兼容**：已移除旧 ContextVar registry，切到 graph-state promotion。
- [x] **T12 Workspace 删除当前会话后的去向**：已采用推荐方案，删除当前会话后回到空白新会话。
- [x] **T13 社区 provider 入口**：已采用推荐方案，SearXNG/Browserless 只进 `config.example.yaml`，暂不进 wizard；Brave 作为 API key 型 search provider 进入 wizard。

## Phase 1: 安全基线

### - [x] 1.1 diff : Docker socket 默认挂载收紧

类型：安全  
来源：`5d61718c`  
位置：`docker/docker-compose.yaml`, `docker/docker-compose-dev.yaml`, `docker/docker-compose.dood.yaml`, `scripts/deploy.sh`, `scripts/docker.sh`  
人类意见：采纳吸收  
子智能体调研：已完成
执行状态：已完成。默认 prod/dev compose config 不再渲染 Docker socket；叠加 `docker-compose.dood.yaml` 后 prod/dev 都会挂载 `/var/run/docker.sock`；`bash -n` 与 `git diff --check` 通过。

**Outcome**：默认 production/dev Compose 栈不再 bind-mount `/var/run/docker.sock`；只有 `sandbox_mode == "aio"` / DooD 模式显式加载 `docker-compose.dood.yaml` 时才挂载 `${DEER_FLOW_DOCKER_SOCKET:-/var/run/docker.sock}`。保留 Scientific Tumbleweed 服务名、端口、gateway/langgraph 双 runtime、ParadeDB 和 nginx route。

**Verification surface**：`rg "/var/run/docker.sock|DEER_FLOW_DOCKER_SOCKET|docker-compose.dood" docker scripts`；分别渲染 local/provisioner/aio compose config，local/provisioner 不得出现 socket，aio 必须出现；`--standard` 与 `--gateway` runtime 形态不变；`git diff --check`。

**Constraints**：不 cherry-pick 整个 commit；不删除 `langgraph`、ParadeDB 或 nginx routing；不夹带 CLI auth、internal token、worker 数量调整；不带入 DeerFlow 命名。

**Boundaries**：允许改 `docker/docker-compose.yaml`、`docker/docker-compose-dev.yaml`、新增 `docker/docker-compose.dood.yaml`、`scripts/deploy.sh`、`scripts/docker.sh`。可选改安全文档；不得改 backend runtime、frontend、依赖、CI、数据库迁移。

**Iteration policy**：第一轮只改 compose 和 overlay；第二轮改脚本加载条件；第三轮跑 grep/compose config。若 local/provisioner 仍渲染 socket，回到第一轮修正。

**Blocked stop condition**：如果无法确认 aio sandbox 实际运行在 gateway、langgraph 还是二者都可能运行，停止并报告；如果实现要求删除 langgraph 或切成上游单 runtime，停止。

**Tradeoff**：推荐最小权限：`--standard` 只挂 langgraph，`--gateway` 只挂 gateway；若想降低脚本复杂度，可接受单 overlay 同时覆盖两者。

### - [x] 1.2 diff : CLI auth 目录默认挂载收紧

类型：安全  
来源：`474c89ba`  
位置：`.env.example`, `docker/docker-compose.yaml`, `docker/docker-compose-dev.yaml`, `docker/docker-compose.cli-auth.yaml`, `backend/docs/CONFIGURATION.md`  
人类意见：采纳吸收  
子智能体调研：已完成

**Outcome**：默认 compose 不再挂载宿主 `~/.claude` / `~/.codex`；新增 opt-in `docker/docker-compose.cli-auth.yaml`，仅在用户明确需要完整 CLI config dir 时加载。文档优先推荐 Claude env token/单文件 credentials、Codex `CODEX_AUTH_PATH`、ACP adapter 自身 env API key。

**Verification surface**：`rg -n "\.claude|\.codex|docker-compose\.cli-auth" docker .env.example backend/docs config.example.yaml`；默认 prod/dev compose config 不含 `/root/.claude`、`/root/.codex`；叠加 cli-auth overlay 后 gateway/langgraph 只读挂载；跑 `cd backend && PYTHONPATH=. uv run pytest tests/test_credential_loader.py tests/test_cli_auth_providers.py tests/test_acp_config.py tests/test_invoke_acp_agent_tool.py -q`。

**Constraints**：不改变 Claude/Codex provider 行为；不提交真实凭据、本地 `.env`、`config.yaml`、`.claude`、`.codex`；保留 gateway/langgraph 分离和本项目容器命名。

**Boundaries**：允许改 `.env.example`、compose prod/dev、新 overlay、`backend/docs/CONFIGURATION.md`、`config.example.yaml` 中 ACP auth 注释。不得改 Docker socket、internal token、provider 重构、前端 UI。

**Iteration policy**：先补 env/example 与说明，再移除默认 mounts，再加 overlay，最后跑 compose config 与 focused backend tests。失败只修本执行块相关文件。

**Blocked stop condition**：如果 overlay 无法同时兼容 prod/dev 的 gateway + langgraph，停止给出两套方案；如果 provider 测试证明必须依赖完整目录且无 env/单文件替代，停止。

**Tradeoff**：推荐安全说明主落 `backend/docs/CONFIGURATION.md`；overlay 先只文档化手动 `-f`，暂不加脚本 env 开关。

### - [x] 1.3 diff : internal gateway token 跨 worker 固定

类型：安全  
来源：`b00749a8`, 关联 `05ae4467`  
位置：`backend/app/gateway/internal_auth.py`, `.env.example`, `docker/docker-compose.yaml`, `docker/docker-compose-dev.yaml`, `scripts/deploy.sh`  
人类意见：采纳吸收  
子智能体调研：已完成
执行状态：已完成。新增部署级 `DEER_FLOW_INTERNAL_AUTH_TOKEN`、production compose 默认 `GATEWAY_WORKERS=1`，并通过 internal auth/channel header focused tests、compose config、`bash -n` 与 `git diff --check` 验证。

**Outcome**：`internal_auth.py` 优先读取 `DEER_FLOW_INTERNAL_AUTH_TOKEN`，无 env 时才 fallback 到进程内随机值；部署脚本生成并持久化 `$DEER_FLOW_HOME/.internal-auth-token`，权限 `600`；compose 透传 env。保留 `GATEWAY_INTERNAL_USER_ID` 与 `token_version=0`。

**Verification surface**：新增 `backend/tests/test_internal_auth.py` 覆盖 env token、错误 token、fallback；跑 channel header tests；`bash -n scripts/deploy.sh`；若吸收 `05ae4467`，补 compose 静态测试确认 `${GATEWAY_WORKERS:-1}` 且可 override。

**Constraints**：不把 token 暴露给 frontend；生成 secret 不入 git；`deploy.sh down` 不得因缺 token/config 失败；不重写 channel manager、nginx sticky 或 stream bridge。

**Boundaries**：只处理 internal gateway auth token 一致性和可选 worker 默认值。不得实现完整多 worker Gateway runtime。

**Iteration policy**：第一轮只做 token/env/deploy 和最小测试；第二轮根据 T3 决定是否把 production Docker 默认 worker 改为 1；每轮只跑 auth/env/compose 相关测试。

**Blocked stop condition**：如果要求“默认多 worker 且完整保证 run/SSE/cancel 跨 worker 可用”，停止并升级为 runtime 设计任务；如果部署不允许 `$DEER_FLOW_HOME` 持久化 secret，停止确认平台 secret 注入方案。

**Tradeoff**：推荐同步 `GATEWAY_WORKERS=1`；保留 4 会有更高并发但仍有进程内 RunManager/StreamBridge 状态风险。

### - [x] 1.4 diff : REST history 隐藏 base64 图片

类型：安全  
来源：`09429644`  
位置：`backend/packages/harness/deerflow/runtime/serialization.py`, `backend/app/gateway/routers/threads.py`, `backend/app/gateway/routers/runs.py`, `backend/app/gateway/routers/thread_runs.py`  
人类意见：采纳  
子智能体调研：已完成
执行状态：已完成。新增 REST API serializer，REST state/history/wait final-state 已切到隐藏 base64 图片路径；`tests/test_serialization.py`、`tests/test_thread_runs_router.py` 和 ruff check 通过。

**Outcome**：新增 REST API 专用 serializer，只在 REST state/history/wait 输出中移除隐藏消息里的 `data:image/...;base64,...` block；SSE、checkpoint、agent internal serializer 保持完整内容。过滤规则只处理 `hide_from_ui=True` 且 content block 为 `type=image_url`、`image_url.url` 以 `data:` 开头的图片。

**Verification surface**：`backend/tests/test_serialization.py` 覆盖 hidden data image 移除、non-hidden 保留、hidden https 保留、string/non-dict 安全、`__pregel_*`/`__interrupt__` 仍剥离；`backend/tests/test_thread_runs_router.py` 覆盖 wait state；跑 `cd backend && PYTHONPATH=. uv run pytest tests/test_serialization.py tests/test_thread_runs_router.py -q`。

**Constraints**：不改 ViewImageMiddleware/checkpoint 持久化；不改 SSE；不在 `deerflow.*` import `app.*`；serializer 返回新结构，不原地修改 checkpoint；不做通用 base64 清洗。

**Boundaries**：允许改 serialization、runtime export、threads/runs/thread_runs REST call site 和相关 tests。不得改 frontend、ViewImage、store schema、stream bridge。

**Iteration policy**：先加 serializer 和单测，再替换 REST call site；若发现更多 REST values call site，用 `rg` 精确补齐；不要改 `serialize(mode="values")`。

**Blocked stop condition**：如果 `read_thread_final_state()` 还有非 REST/internal 消费方依赖完整 hidden base64，停止并新增 `read_thread_final_state_for_api()`。

**Tradeoff**：推荐若 `read_thread_final_state()` 只服务 REST，则直接使用 API serializer；若想语义更清楚，则新增显式 API helper。

### - [x] 1.5 diff : MCP config endpoint hardening 增量

类型：安全  
来源：`40a371b8`  
位置：`backend/app/gateway/routers/mcp.py`, `backend/tests/test_mcp_config_secrets.py`, `frontend/src/core/mcp/hooks.ts`  
人类意见：采纳；未来考虑全局 admin MCP 与用户自配置 MCP  
子智能体调研：已完成
执行状态：已完成。前端 toggle 已改为 `/api/mcp/servers/{name}/enabled`；后端 per-user toggle 会把 server override 收敛为 `{enabled: ...}`，避免配置注入；`test_mcp_config_secrets.py`、`test_skill_enablement_user_prefixed.py`、ruff 和 `pnpm check` 通过。

**Outcome**：保持当前产品语义：`GET /api/mcp/config` 返回当前用户 effective config 且 mask secrets；全局 `PUT /api/mcp/config` 保持 403；普通用户唯一写入口是 `PUT /api/mcp/servers/{name}/enabled`，只写该用户 enabled override。修正前端 toggle 不再调用全量 PUT。

**Verification surface**：补 `backend/tests/test_mcp_config_secrets.py`：GET mask env/headers/OAuth secrets；global PUT 403 且不写入；未登录 toggle 401；登录 toggle 已存在 server 只写 user override；未知 server 404；override 不能注入未知 server；保留 skills/其他 MCP entries。跑 `cd backend && PYTHONPATH=. uv run pytest tests/test_mcp_config_secrets.py tests/test_skill_enablement_user_prefixed.py -q`；改前端则跑 `cd frontend && pnpm check`。

**Constraints**：不恢复全局 MCP PUT；不在本增量实现 admin/global UI 或用户自定义 MCP server；secret 读取接口不得回显真实 secret；不照搬上游 writable global config。

**Boundaries**：允许改 `mcp.py` GET/PUT/toggle、user extensions config、前端 MCP hooks 和 tests。不得引入 stdio user self-config、admin UI、MCP/channel header propagation。

**Iteration policy**：先补后端 endpoint tests 锁住 403 与 per-user toggle，再修前端 toggle path；admin/global 与 user self-config 放后续 phase。

**Blocked stop condition**：如果产品要求普通用户现在就能新增/编辑 MCP server，停止；这会改变权限、secret 存储和 stdio 执行风险。

**Tradeoff**：推荐普通用户只看 `name/enabled/description/type` catalog；未来 admin endpoint 用 `/api/admin/mcp/config`，带审计、write-only secrets、stdio allowlist 和部署开关。

### - [x] 1.6 diff : Upload size contract 与 skipped_files

类型：安全  
来源：`1aac408d`  
位置：`backend/app/gateway/routers/uploads.py`, `frontend/src/core/uploads/api.ts`, `frontend/src/components/ai-elements/prompt-input/prompt-input.tsx`, `frontend/src/core/uploads/file-validation.ts`  
人类意见：采纳吸收  
子智能体调研：已完成

**Outcome**：后端权威执行 `max_files`、`max_file_size`、`max_total_size`；上传与列表响应 `file.size` 为 number/int；`UploadResponse` 显式包含 `skipped_files`。所有 thread uploads 继续通过 `get_authenticated_thread_resource`、`thread_resource.thread_id/user_id/uploads_dir`。

**Verification surface**：后端 tests 覆盖 too many files、single too large、total too large、413 后不落盘/不同步 sandbox、`skipped_files` 只表示 unsafe destination、size int；前端 `api.ts` 补类型并跑 `cd frontend && pnpm check`；建议 `cd backend && PYTHONPATH=. uv run pytest tests/test_uploads_router.py tests/test_upload_config.py tests/test_client.py -q`。

**Constraints**：后端限制是权威限制，前端预检只是体验；不替换本地 ownership/auth；`skipped_files` 默认空数组，size 413 不混入 skipped_files；不改 nginx body limit 本身。

**Boundaries**：允许改 uploads router、frontend uploads API、PromptInput 文件预检、file-validation、相关 tests、必要时 Python client。不得改 auth/ownership 架构、OpenDAL/storage 迁移、上传 UI 大重写。

**Iteration policy**：先做后端 contract 和 tests，再做前端类型/预检，最后决定 limits 暴露方式；每步只跑对应 tests。

**Blocked stop condition**：如果无法确定 app-level limit 来源，停止确认；如果 response model optional 字段 null/缺省策略冲突，停止确认；如果 `/uploads/limits` 访问控制与 thread ownership 冲突，停止确认。

**Tradeoff**：推荐 `config.yaml` app limits：`max_files=10`、`max_file_size=50MiB`、`max_total_size=100MiB`，并与 nginx body limit 取更严格值。

### - [x] 1.7 diff : 前端用户消息纯文本与深层 Markdown 限制

类型：安全  
来源：`503eeac7`, `0367fe6c`, `25fbd25b`  
位置：`frontend/src/components/workspace/messages/message-list-item.tsx`, `frontend/src/components/ai-elements/message.tsx`, `frontend/src/core/streamdown/preprocess.ts`, `frontend/src/core/streamdown/plugins.ts`  
人类意见：采纳吸收  
子智能体调研：已完成

**Outcome**：human message 改纯文本渲染并加强气泡换行；assistant message 继续走本地 citation-aware Markdown/KaTeX/artifact 链路。新增本地 `capMarkdownNesting`，在进入 Streamdown 前限制深层 list/blockquote，避免渲染崩溃。

**Verification surface**：新增 `frontend/tests/unit/core/streamdown/preprocess.test.ts` 覆盖 blockquote/list/fenced code；必要时补 human message 渲染测试；跑 `cd frontend && pnpm check` 和 `cd frontend && BETTER_AUTH_SECRET=local-dev-secret pnpm build`；手工窄屏验证超长 token 不撑破气泡。

**Constraints**：human message 保留 `stripUploadedFilesTag(rawContent)` 与 files list；assistant 保留 citation registry、artifact URL resolver、KaTeX、rehype word animation；不引入 feedback buttons、Mermaid preprocess、clipboard fallback。

**Boundaries**：允许改 message-list-item、ai-elements/message、可新增 ai-elements/streamdown wrapper、core/streamdown/preprocess、plugins/index、相关 tests。不得改 citation core、frontend e2e harness、landing/docs/blog。

**Iteration policy**：先改 human 纯文本和 CSS，再加 `capMarkdownNesting` 纯函数，再接入 MessageResponse wrapper，最后跑 check/build 和浏览器验证。

**Blocked stop condition**：如果 wrapper 破坏 streaming、citation link、artifact `/mnt/` 解析或 MessageResponseProps，停止并改为只在 MarkdownContent 调用前对 assistant content 做 preprocess。

**Tradeoff**：推荐接受 human message 纯文本；用户输入的 Markdown/数学公式不再渲染，但可避免 prompt/Markdown 注入和崩溃。

## Phase 2: Runtime 与 Agent 稳定性

### - [x] 2.1 diff : subagent checkpointer 隔离与结构化状态

类型：功能  
来源：`47e9570d`, `8d2e55a0`  
位置：`backend/packages/harness/deerflow/subagents/executor.py`, `backend/packages/harness/deerflow/subagents/status_contract.py`, `contracts/subagent_status_contract.json`, `frontend/src/core/tasks/subtask-result.ts`, `frontend/src/components/workspace/messages/message-list.tsx`  
人类意见：采纳吸收  
子智能体调研：已完成

**Outcome**：subagent `create_agent()` 显式 `checkpointer=False`；新增结构化 `subagent_status` contract，后端在 task ToolMessage `additional_kwargs` 打 stamp，前端优先读结构化状态，文本前缀 parser 保留 fallback。

**Verification surface**：`test_subagent_executor.py` 断言 `checkpointer=False`；新增 `test_subagent_status_contract.py`；task tool success/fail/cancel/timeout/polling timeout stamp tests；前端 parser 如不引入 Vitest，则至少跑 `pnpm check` 并做 fixture 人工验证。

**Constraints**：不覆盖当前 subagent executor 的 `sandbox_provider_variant`、`app_config`、skills loading、recursion limit、token usage collector、isolated loop、terminal state 原子写入；`subagent_status` 只进 `ToolMessage.additional_kwargs`，不改 task tool 文案。

**Boundaries**：允许改 executor、status_contract、tool_error_handling_middleware、contract JSON、frontend subtask parser/message-list、相关 tests。不得夹带 deferred MCP loading、RunManager lifecycle 或上游整版 message-list 重构。

**Iteration policy**：先做 `checkpointer=False` 和 regression test；再做后端 contract/stamping；再做前端 parser 与 message-list 接入；最后决定是否扩展前端测试栈。

**Blocked stop condition**：如果 LangChain `create_agent()` 不接受 `checkpointer=False`，停止；如果 `additional_kwargs` 无法在本地序列化链路保留，停止；如果前端拿不到 `message.additional_kwargs`，停止。

**Tradeoff**：推荐保留文本前缀 fallback 覆盖历史线程；是否引入 Vitest 作为自动 parser 测试需单独确认。

### - [x] 2.2 diff : Run lifecycle 与 checkpointer 稳定性

类型：功能  
来源：`268fdd69`, `031d6fbc`, `d133b111`  
位置：`backend/app/gateway/deps.py`, `backend/packages/harness/deerflow/runtime/runs/manager.py`, `backend/packages/harness/deerflow/agents/checkpointer/async_provider.py`, `backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py`  
人类意见：采纳吸收  
子智能体调研：已完成
执行状态：已完成。summary 调用已加 `TAG_NOSTREAM`，Postgres async checkpointer 已切到带 `check_connection` 与 keepalive 的 `AsyncConnectionPool`，gateway runtime 退出会在资源 context 关闭前调用 `RunManager.shutdown(timeout=5s)` 中断未完成 run。

**Outcome**：summarization LLM call 使用 `TAG_NOSTREAM`；Postgres async checkpointer 改用 `AsyncConnectionPool(check=check_connection, keepalives...)`；gateway shutdown 在 checkpointer context manager 退出前 bounded drain in-flight runs。

**Verification surface**：已通过 `cd backend && PYTHONPATH=. PYTHONPYCACHEPREFIX=/private/tmp/st-pycache UV_CACHE_DIR=/private/tmp/st-uv-cache uv run python -m pytest tests/test_summarization_middleware.py tests/test_checkpointer.py tests/test_run_manager.py tests/test_gateway_lifespan_shutdown.py tests/test_run_worker_rollback.py -q`，结果 `91 passed`；已通过 `uv run ruff check app/gateway/deps.py packages/harness/deerflow/agents/middlewares/summarization_middleware.py packages/harness/deerflow/agents/checkpointer/async_provider.py packages/harness/deerflow/runtime/runs/manager.py tests/test_summarization_middleware.py tests/test_checkpointer.py tests/test_run_manager.py tests/test_gateway_lifespan_shutdown.py`。

**Constraints**：保留本地 Gateway-mode runtime、RunManager、StreamBridge、RunStore、RuntimeContext；保留 `deerflow.agents.checkpointer.*` 路径；不把 DB engine close 逻辑搬进 deps；`_persist_status()` 需要返回 bool 或改写 shutdown 判断。

**Boundaries**：不引入上游 `runtime/checkpointer` 目录迁移、SQLAlchemy RunRepository、IM channel、RunEventStore/Journaling；summarization 只吸收 nostream，保留结构化摘要、skill rescue、dynamic context reminder、memory flush hook。

**Iteration policy**：先合 summarization nostream；再合 AsyncConnectionPool；最后合 RunManager.shutdown + deps drain。每步只跑对应 focused tests。

**Blocked stop condition**：如果 drain 需要改变 LangGraph-compatible request/SSE wire shape，停止；如果必须引入 Redis/持久 stream bridge 才能正确 drain，停止；如果 checkpointer pool 修复被迫迁移整个目录，停止。

**Tradeoff**：推荐 shutdown 未完成 run 标记 `interrupted`，timeout 先用 5s；title sync 后台任务先不纳入主修复。

### - [x] 2.3 diff : Memory injection offload 与 token_counting 配置

类型：功能  
来源：`51920072`, `167ef451`  
位置：`backend/app/gateway/app.py`, `backend/packages/harness/deerflow/agents/middlewares/dynamic_context_middleware.py`, `backend/packages/harness/deerflow/agents/memory/prompt.py`, `backend/packages/harness/deerflow/config/memory_config.py`, `backend/app/gateway/routers/memory.py`, `backend/packages/harness/deerflow/client.py`, `config.example.yaml`  
人类意见：采纳吸收  
子智能体调研：已完成
执行状态：已完成。异步 dynamic context 注入已通过 `asyncio.to_thread + wait_for` offload；memory token counting 已支持 `tiktoken | char`，char mode 不触碰 tiktoken；gateway startup 在 char mode 下跳过 warm-up，默认 tiktoken mode 继续限时预热。

**Outcome**：memory injection 中阻塞的 storage/tiktoken 读取移到 `asyncio.to_thread` 并加 timeout；`memory.token_counting` 支持 `tiktoken | char`；char mode 完全不触碰 tiktoken；gateway startup 根据配置 warm-up 或跳过 tiktoken。

**Verification surface**：已通过 `cd backend && PYTHONPATH=. PYTHONPYCACHEPREFIX=/private/tmp/st-pycache UV_CACHE_DIR=/private/tmp/st-uv-cache uv run python -m pytest tests/test_tiktoken_cache_and_count_tokens.py tests/test_memory_prompt_injection.py tests/test_dynamic_context_middleware.py tests/test_lead_agent_prompt.py tests/test_memory_middleware_strict_user.py tests/test_client.py::TestMemoryManagement tests/test_client.py::TestScenarioMemoryWorkflow tests/test_client.py::TestGatewayConformance::test_get_memory_config tests/test_client.py::TestGatewayConformance::test_get_memory_status tests/test_memory_router.py -q`，结果 `102 passed`；已通过 `tests/test_gateway_lifespan_shutdown.py -q`，结果 `2 passed`；已通过 ruff check 相关文件。`/api/memory/config` 已有 char mode contract 单测。

**Constraints**：保留 Postgres/SQLModel memory、user-scoped memory、auth dependency、Scientific Tumbleweed prompt、tool_cache vacuum、gateway/db shutdown 顺序；`dynamic_context_middleware` 继续用本地 `resolve_runtime_user_id(runtime)`。

**Boundaries**：允许改 app startup、memory prompt/config/router/client、lead_agent prompt、dynamic context middleware、config.example/tests。不得改 storage 默认回 FileMemoryStorage、替换 auth/user isolation、引入 blocking_io infra。

**Iteration policy**：先改 memory_config + prompt + token-counting tests；再改 middleware + app startup；最后改 router/client/config.example。

**Blocked stop condition**：如果 `to_thread` 后无法可靠保留 run owner user_id，停止；如果 char mode 仍调用 tiktoken，停止；如果 config upgrade 无法无损加载旧 config，停止。

**Tradeoff**：推荐默认 `tiktoken` 精度更高；网络受限部署显式设 `char`。若产品默认零网络依赖，则改默认 `char`。

### - [x] 2.4 diff : Sandbox lazy state 持久化与 stale cache 处理

类型：功能  
来源：`8955b322`, `919d8bc2`, `f401e7ba`  
位置：`backend/packages/harness/deerflow/agents/thread_state.py`, `backend/packages/harness/deerflow/sandbox/middleware.py`, `backend/packages/harness/deerflow/community/aio_sandbox/*`  
人类意见：采纳吸收  
子智能体调研：已完成
执行状态：已完成。`ThreadState.sandbox` 已增加 idempotent reducer；SandboxMiddleware 已在 lazy tool acquire 后通过 `Command(update=...)` 写回 sandbox state；AIO active/warm cache 复用前已接入 health/readiness 检查，明确 dead 才 drop，检查异常保持非破坏性。

**Outcome**：`ThreadState.sandbox` 增加 reducer；SandboxMiddleware 在 lazy tool acquire 后通过 `Command(update={"sandbox": ...})` 持久化 sandbox state；AIO provider 真实 acquire/reuse 路径复用 active/warm cache 前做 health check，避免 stale container。

**Verification surface**：已通过 `rg -n "merge_sandbox|_attach_sandbox_update|_drop_unhealthy_sandbox|_is_no_such_container_error" backend`；已通过 `cd backend && PYTHONPATH=. PYTHONPYCACHEPREFIX=/private/tmp/st-pycache UV_CACHE_DIR=/private/tmp/st-uv-cache uv run python -m pytest tests/test_thread_state_reducers.py tests/test_sandbox_middleware.py tests/test_aio_sandbox_provider.py tests/test_aio_sandbox_local_backend.py tests/test_remote_sandbox_backend.py tests/test_sandbox_orphan_reconciliation.py tests/test_sandbox_user_prefixed_paths.py tests/test_run_worker_sandbox_capacity.py -q`，结果 `128 passed`；已通过 ruff check 相关文件。测试结束后有 LangSmith 外网 DNS 上报警告，但 pytest 已成功退出。

**Constraints**：保留 `provider_variant`、`user_id:thread_id` cache key、user-scoped mount、capacity/warm-pool eviction、Remote provisioner image/resources/replicas/user_id；不整文件覆盖 provider；不照搬不存在的 replay fixture。

**Boundaries**：允许改 thread_state、sandbox middleware、aio_sandbox provider/local/remote backend 和 focused tests。不得改 ToolOutputBudget、frontend、Docker compose、capacity router、run worker 行为。

**Iteration policy**：先 reducer 和单测；再 middleware `wrap_tool_call/awrap_tool_call` 与 Command update；再把 health check 接入 `_reuse_in_process_sandbox` / `_reclaim_warm_pool_sandbox`；最后跑 focused tests 和可选真实容器 smoke。

**Blocked stop condition**：如果 reducer/middleware tests 不能证明 lazy sandbox id 进入图状态，停止；如果 health check 异常会误删可能健康 container，停止；如果需改 cache key/user path/capacity hard cap，停止。

**Tradeoff**：推荐不把 `AioSandbox.close()` 前置小修纳入本点，只在 drop-unhealthy 中 best-effort guard；真实 Docker/K8S smoke 可作为实现后额外验证。

### - [x] 2.5 diff : MCP session pooling 与 deferred tool loading

类型：功能  
来源：`162fb214`, `3b6dd0a4`, `d8b728f7`, `8fca56cf`, `d9f47249`, `2bbc7879`  
位置：`backend/packages/harness/deerflow/mcp/*`, `backend/packages/harness/deerflow/tools/builtins/tool_search.py`, `backend/packages/harness/deerflow/agents/middlewares/deferred_tool_filter_middleware.py`, `backend/packages/harness/deerflow/agents/lead_agent/*`, `backend/packages/harness/deerflow/subagents/executor.py`, `backend/packages/harness/deerflow/client.py`  
人类意见：采纳吸收  
子智能体调研：已完成

**Outcome**：HTTP/SSE MCP 不进入 stdio session pool；stdio session pool 使用 owner-task + close event + inflight creation 去重；deferred MCP 从 ContextVar registry 迁移到 graph-state catalog/promotion，lead agent、embedded client、subagent 共用同一 deferred setup。

**Verification surface**：MCP tests 确认只有 `transport == "stdio"` 被 pool 包装；session pool tests 覆盖 create/reuse/LRU/close；`extensions_config` tests 覆盖 `transport` alias；deferred tests 覆盖 catalog/hash、promotion、middleware visibility、thread_state promoted reducer、lead/subagent/client 一致。已跑：`rg "get_deferred_registry|set_deferred_registry|reset_deferred_registry|DeferredToolRegistry|DeferredToolEntry" backend/packages/harness/deerflow backend/tests` 无命中；`PYTHONPATH=. PYTHONPYCACHEPREFIX=/private/tmp/st-pycache UV_CACHE_DIR=/private/tmp/st-uv-cache uv run python -m pytest tests/test_mcp_client_config.py tests/test_mcp_session_pool.py tests/test_tool_search.py tests/test_deferred_tool_registry_promotion.py tests/test_deferred_tool_promotion_real_llm.py tests/test_tool_deduplication.py tests/test_thread_state_reducers.py tests/test_tool_error_handling_middleware.py tests/test_subagent_executor.py tests/test_lead_agent_prompt.py tests/test_client.py::TestEnsureAgent -q`，结果 `161 passed`；`uv run ruff check ...` 结果 `All checks passed`。

**Constraints**：不整文件覆盖 `extensions_config.py`、`tools/tools.py`、`lead_agent/agent.py` 或 `tool_error_handling_middleware.py`；保留 plugin tools、skill evolution、host bash gate、view image、dedup priority、per-user extensions、lead-agent split、subagent `app_config/sandbox_provider_variant/skills`。

**Boundaries**：允许改 mcp tools/session_pool、extensions_config、tool_search、mcp_metadata、tools.py、thread_state、deferred middleware、lead_agent dynamic sections/prompt/base、tool_error_handling_middleware、subagents executor、client 和相关 tests。不得夹带 MCP/channel header propagation、ToolOutputBudget、structured subagent status、sandbox reducer。

**Iteration policy**：先做 `transport` alias + HTTP/SSE 不 pooling；再做 owner-task session pool；最后做 deferred graph-state 迁移。每批都有独立 tests；若保留兼容 shim，必须记录删除条件。

**Blocked stop condition**：如果 final tool list、prompt deferred section、middleware deferred setup 无法共用同一 catalog/hash，停止；如果 `ThreadState.promoted` 不能跨 turn 持久化，停止；如果 HTTP/SSE 仍被 pool 包装或 stdio close 仍跨 task 风险，停止。

**Tradeoff**：推荐本点不夹带 header forwarding；推荐最终不保留旧 ContextVar registry。若 deferred subagent tests 需要 `checkpointer=False`，可依赖 2.1 先完成。

### - [x] 2.6 diff : ToolOutputBudgetMiddleware

类型：功能  
来源：`ca487578`, `64d923b0`  
位置：`backend/packages/harness/deerflow/agents/middlewares/tool_output_budget_middleware.py`, `backend/packages/harness/deerflow/config/tool_output_config.py`, `config.example.yaml`  
人类意见：采纳吸收  
子智能体调研：已完成

**Outcome**：新增全局 ToolOutputBudget middleware，对所有工具输出做预算保护；小输出 passthrough，超大输出外部化到 thread outputs，可读路径回传模型；保留已有 `bash/read_file/ls` 工具级截断作为第一道局部保护。

**Verification surface**：新增 config 与 middleware tests；确认 `AppConfig.tool_output` 解析，`config.example.yaml` 本地 `config_version` 已递增到 `10`；lead agent、SDK factory、subagent runtime builder 三入口都注册 middleware；已跑 `PYTHONPATH=. PYTHONPYCACHEPREFIX=/private/tmp/st-pycache UV_CACHE_DIR=/private/tmp/st-uv-cache uv run python -m pytest tests/test_tool_output_budget_middleware.py tests/test_tool_error_handling_middleware.py tests/test_create_deerflow_agent.py tests/test_lead_agent_model_resolution.py tests/test_tool_output_truncation.py tests/test_sandbox_middleware.py tests/test_aio_sandbox_provider.py tests/test_remote_sandbox_backend.py tests/test_harness_boundary.py -q`，结果 `182 passed`（LangSmith DNS warning 非阻断）；已跑 `uv run ruff check ...`，结果 `All checks passed!`。

**Constraints**：新增 middleware 不得 import `app.*`；不覆盖 app_config 大重构；不删除 sandbox 工具级截断；sandbox provider 解析必须适配本地 variant/user_id。

**Boundaries**：允许新增 middleware/config/tests，接入 lead agent、SDK factory、subagent runtime builder，更新 config.example。不得改前端渲染、REST/SSE 协议、OpenDAL 存储、landing/docs/branding。

**Iteration policy**：先核心 config + middleware + 单测；再适配 sandbox provider variant/user_id 与 non-mounted remote sandbox；最后补链路顺序和入口一致性 tests。

**Blocked stop condition**：如果 non-mounted remote sandbox 下不能生成可读外部化路径，停止确认策略；不得返回不可读 `/mnt/user-data/outputs/...` 假装成功。

**Tradeoff**：推荐默认启用，上游阈值 `externalize_min_chars=12000`、`fallback_max_chars=30000` 先沿用；科研长日志再通过 config 调整。

## Phase 3: 前端体验与可选能力

### - [x] 3.1 diff : 前端 workspace 稳定性

类型：功能  
来源：`34e126ee`, `5819bd8a`, `5b81588b`, `b6fbf0d1`  
位置：`frontend/src/components/workspace/chats/use-thread-chat.ts`, `frontend/src/components/workspace/recent-chat-list.tsx`, `frontend/src/core/threads/hooks.ts`, `frontend/src/core/clipboard.ts`, `frontend/src/components/workspace/copy-button.tsx`, AuthProvider/AuthGuard 相关文件  
人类意见：采纳吸收  
子智能体调研：已完成

**Outcome**：选择性吸收四个稳定性行为：删除当前会话后 reset active chat；线程列表支持分页/增量加载；clipboard fallback；网关短暂不可达时 workspace 不立即踢回 login，而进入可恢复的 unavailable 状态。

**Verification surface**：`cd frontend && pnpm check`，已通过；`cd frontend && BETTER_AUTH_SECRET=local-dev-secret pnpm build`，已通过；因改 backend thread list contract，已跑 `cd backend && PYTHONPATH=. PYTHONPYCACHEPREFIX=/private/tmp/st-pycache UV_CACHE_DIR=/private/tmp/st-uv-cache uv run python -m pytest tests/test_threads_router.py tests/test_threads_router_ownership.py -q`，结果 `44 passed`；静态检查 `rg -n "navigator\\.clipboard|writeTextToClipboard|installClipboardFallback|useInfiniteThreads|listByUser" frontend/src backend/app/gateway/routers/threads.py` 确认 clipboard 走 helper、infinite threads 走 Gateway `listByUser?limit&offset`。

**Constraints**：thread list/query key 带当前 `user.id`；Gateway 请求继续 `fetchWithAuth`；保留 AuthProvider cache/session/CSRF 清理；保留 recent-chat-list 导出 HTML/JSON、时间戳、static website 判断、用户显示名；不重写 assistant markdown/citation 链路。

**Boundaries**：不覆盖 workspace layout 为上游 SSR auth；不引入上游 workspace-content 结构；不用 LangGraph SDK 替代本地 Gateway ownership API；不批量替换 recent-chat-list/chat pages/AuthProvider。

**Iteration policy**：先做 thread reset；再定后端分页 contract 并做 infinite cache/UI；再做 clipboard helper/wrapper；最后做 gateway unavailable 状态机。每步跑 `pnpm check`，涉及后端则跑 focused pytest。

**Blocked stop condition**：如果无法确认删除当前会话后去向，停止；如果 `listByUser` 与 search 在线程标题、legacy、ownership、updated_at 上无法保持等价，停止；如果 AuthProvider 不能区分未登录和网关不可达，停止。

**Tradeoff**：推荐删除当前会话后回空白新会话；推荐给 `listByUser` 加分页而不是切 SDK；gateway unavailable 推荐短时保留 workspace shell 和 offline banner。

### - [x] 3.2 diff : 社区搜索 provider

类型：功能  
来源：`330a2ff8`, `6e839342`, `f92a26d5`, `10c1d9f4`，伴随配置示例 `bbce6c0a`  
位置：`backend/packages/harness/deerflow/community/searxng/*`, `browserless/*`, `brave/*`, `jina_ai/*`, `ddg_search/*`, `config.example.yaml`, `scripts/doctor.py`, `scripts/wizard/providers.py`  
人类意见：采纳吸收  
子智能体调研：已完成
执行状态：已完成。已新增 Brave、SearXNG、Browserless provider；DDG 已支持 region/backend/safesearch 与 Wikipedia region 修复；Jina 已支持 proxy/trust_env；新增 provider 输出均适配 citation contract；前端无 provider 名称/host/token 泄漏。

**Outcome**：手工吸收 web research provider 增量：DDGS region/backend/safesearch 修复；Jina proxy/trust_env；新增 Brave、SearXNG、Browserless provider。所有 provider 输出适配 Scientific Tumbleweed citation contract，前端不暴露 provider 细节。

**Verification surface**：已通过静态 `rg -n "searxng|browserless|Brave|BRAVE_SEARCH_API_KEY|BROWSERLESS_TOKEN|localhost:3032|localhost:8088|api.search.brave.com|X-Subscription-Token" frontend/src frontend/tests -S`，无命中；已通过 `cd backend && PYTHONPATH=. PYTHONPYCACHEPREFIX=/private/tmp/st-pycache UV_CACHE_DIR=/private/tmp/st-uv-cache uv run python -m pytest tests/test_searxng_client.py tests/test_browserless_client.py tests/test_brave_tools.py tests/test_jina_client.py tests/test_ddg_search_tools.py tests/test_doctor.py tests/test_setup_wizard.py tests/test_citation_normalizers.py -q`，结果 `103 passed`；已通过 `uv run ruff check` 覆盖新增/修改 provider、doctor、wizard 与 tests。测试结束后有 LangSmith 外网 DNS 上报警告，但 pytest 已成功退出。live smoke 未执行，因为本地未假设可用 Brave key、SearXNG/Browserless 服务或代理。

**Constraints**：不整文件覆盖 `config.example.yaml`、`scripts/doctor.py`、`scripts/wizard/providers.py`；不改 landing/blog/docs；不暴露 provider 到 frontend；学术论文/科研证据继续走 `academic_search_*`，`web_search` 只增强网页/新闻/产品文档事实。

**Boundaries**：允许新增 searxng/browserless/brave 目录，小改 jina_ai、ddg_search、config.example、doctor、wizard provider entry。不得改 frontend provider UI、`academic_data_search_service.py`、academic/web routing prompt、Docker compose/proxy 脚本。

**Iteration policy**：先 DDGS region；再 Jina proxy；再 Brave provider/doctor/wizard/config；再 SearXNG config；最后 Browserless fetch 并接 citation-aware 输出。每步只跑对应 tests。

**Blocked stop condition**：如果必须整文件覆盖 config/wizard，停止；如果 Browserless/Jina 无法保留 `citationUrl/citationProvider`，停止；如果 provider 名称/host/token 泄漏到 frontend，停止；如果 `ddgs` 版本不支持上游参数，停止。

**Tradeoff**：推荐 SearXNG/Browserless 暂不进 setup wizard，只写 config.example；Browserless 作为可选高级 fetch provider，不替代 Jina 默认。

## 本轮明确不执行

- [x] `MCP/channel user_id 与 header 传播`：人类意见为跳过。本轮不吸收 `3ae82dc6`；若以后要做，必须单独验证 IM channel -> internal gateway -> MCP header/user_id 链路。
- [x] `user-owned IM channel connections`：人类意见为跳过。Telegram/Slack/Feishu/WeCom 用户自连属于产品级功能，不混入本轮同步。
- [x] `Dev/test guardrails`：人类意见为跳过。blocking IO runtime gate、record/replay e2e、CI fixtures 另开测试基础设施任务。
- [x] landing/blog/docs、README 多语言、issue templates、skills/public 大范围变更、依赖-only 升级：继续不进本轮。

## 推荐执行队列

- [x] Phase 1.1 -> 1.4：先清默认凭据/host socket/internal token/REST base64 泄露。
- [x] Phase 1.5 -> 1.7：再收紧 MCP config、uploads contract、前端用户消息渲染。
- [x] Phase 2.1 -> 2.3：先做 subagent、run lifecycle、memory 这三个高确定性稳定性点。
- [x] Phase 2.4 -> 2.6：再做 sandbox/MCP deferred/ToolOutputBudget，因它们互相涉及 runtime state 与 sandbox 路径。
- [x] Phase 3.1 -> 3.2：最后做前端 workspace 体验与社区搜索 provider。
