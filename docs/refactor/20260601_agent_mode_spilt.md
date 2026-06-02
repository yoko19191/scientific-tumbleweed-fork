# Agent 模式拆分重构方案：Chat / Computer 模式 + 统一 build_prompt 工厂 + 推理深度解耦

> 文档版本：2026-06-01
> 作者：科学风滚草 (Kiro)
> 状态：待执行（需求与实现细节已细化，含「待敲定」清单）
> 关联计划文件：`~/.claude/plans/chat-mutable-raven.md`

---

## 第一部分 · 需求（Requirements）

> 这是本次重构的源头诉求。下面每一条都给出「原始诉求」+「精确定义」+「完成判据」，避免歧义。

### R1 — 拆分 Chat 模式与 Computer 模式

- **原始诉求**：把后端单一的 `lead_agent` 图拆成 `chat_lead_agent` 和 `computer_lead_agent` 两个图。
- **精确定义**：
  - LangGraph 注册两个独立图 id：`chat_lead_agent`、`computer_lead_agent`。
  - `computer_lead_agent` 的能力 = 今天的 `lead_agent`（完整 AioSandbox + bash + 全工具）。
  - `chat_lead_agent` = 轻量对话变体（见 R6 文件空间定义）。
- **完成判据**：前端按模式发不同 `assistant_id`；两个图分别可被 Gateway 正确路由并构建；旧 `lead_agent` 不再被任何运行路径引用。

### R2 — 取消前端 Swarm 显式开启，默认开启 Subagents

- **原始诉求**：前端不再有 Swarm 模式；Chat 和 Computer 都默认开启子代理。
- **精确定义**：
  - 前端模式枚举从 `chat | agent | swarm` 变为 `chat | computer`。
  - `subagent_enabled` 不再由前端模式控制，而是两个图在后端**默认置 True**。
  - `max_concurrent_subagents` 不再由「swarm」特例决定，取后端默认（当前 3，可在变体默认值中调整）。
- **完成判据**：前端无 swarm 任何残留（grep 为空）；两图构图后 `subagent_enabled=True` 且 `task_tool` 在工具集中。

### R3 — 统一的 build_prompt 工厂函数

- **原始诉求**：做一个 `build_prompt` 工厂函数，配合 langchain-dev-utils 和 jinja2，对每一个 agent 和 subagent 在统一入口和 `ground_truth` 完成配置。
- **精确定义**：
  - 存在单一函数 `build_prompt(agent_key, ctx) -> str`，作为 **lead agent（chat/computer）+ 全部 subagent** 的唯一提示词生成入口。
  - 提示词内容由 jinja2 模板渲染；所有 agent/subagent 共享一份 `ground_truth`（canonical 事实：身份、规则、科学方法论、安全约束）。
  - langchain-dev-utils 的 `FormatPromptMiddleware(template_format="jinja2")` 负责**运行时**占位符注入（日期、动态 memory 等）；jinja2 `Environment` 负责**构建时**结构渲染。
  - 现有 `SystemPromptBuilder` / `sections.py` 字符串拼接方式被替换（激进重构）。
- **完成判据**：lead + 5 个 subagent 全部经 `build_prompt` 生成；存在 `ground_truth.yaml` 被所有模板引用；渲染输出对比重构前无语义回归；静态/动态缓存边界保持。

### R4 — 两个 lead agent 默认开启 plan 模式

- **原始诉求**：`chat_lead_agent` 和 `computer_lead_agent` 默认开启 plan 模式。
- **精确定义**：两个图的 `is_plan_mode` 默认值为 `True`（仅在调用方未显式传值时生效，显式 context 仍可覆盖）。
- **完成判据**：两图构图后 `TodoMiddleware`（plan 中间件）启用，提示词含 plan 指引。

### R5 — reasoning_effort 与 thinking_enabled 同模式彻底解耦

- **原始诉求**：这两者完全由「模型」+「模型选择旁的 reasoning_effort 下拉框」控制，与模式选择完全解耦。
- **精确定义**：
  - 前端 `reasoning_effort` 只来自下拉框（默认取模型 `default_reasoning_effort`），切换模式**不重置、不影响** effort。
  - `thinking_enabled = model.supports_thinking && (reasoning_effort !== "none")`，即下拉框选 `none` 即关闭思考。
  - 后端两图不再从「模式/variant」派生 effort 或 thinking，全部从 context 透传。
- **完成判据**：删除 `getModeDefaultReasoningEffort` 等 mode→effort 逻辑（grep 为空）；effort=none → `thinking_enabled=false`；切模式 effort 不变；后端工厂内无 mode→effort/thinking 派生。

### R6 — Chat 模式的文件空间（已敲定）

- **原始诉求**：Chat 模式不启动沙盒、无 bash、不能 exec；但依旧有文件空间可输出文件。参考 `~/repo_learn/langchain-ai-repos/deepagents` 的设计。
- **最终定义（已敲定）**：
  - Chat 的文件系统后端 = **与现在 `lead_agent` 一致的 `/mnt/user-data`（含 `workspace/uploads/outputs`）虚拟路径 → 本地文件映射**。
  - 行为上等同 state-backed deepagent 的虚拟文件空间，但**不启动 Docker 沙盒容器**；工作区开辟方式与现在 `lead_agent` 完全一样。
  - **实现路径（已定）**：复用现有 `LocalSandboxProvider`（`deerflow/sandbox/local/local_sandbox_provider.py`）—— 它已经做到 per-thread `/mnt/user-data/{workspace,uploads,outputs}` → 宿主目录映射、**不起容器**、镜像 AioSandbox 的路径契约。Chat 变体强制用 Local provider；**文件工具、产物、`get_artifact` 下载全部沿用，零改动**。
  - Chat 工具集含 `ls/read_file/write_file/str_replace`，**不含** `bash`（从工具组剔除 `bash`）。
  - **子代理**：Chat 默认开 subagents，但**所有子代理同样无 exec/bash**（保留子代理、剥夺执行能力），不被绕过。
  - Computer 与今天一致（AioSandbox 容器 + bash）。
- **唯一工程障碍（P2a 核心任务）**：`get_sandbox_provider()` 是**进程级全局单例**（从 `config.sandbox.use` 解析缓存）。需改造为 **variant 感知**：Chat→`LocalSandboxProvider`，Computer→配置的 `AioSandboxProvider`，同进程共存。见 Phase 2a 实现方法。
- **完成判据**：Chat 构图无 bash、`docker ps` 无新容器；Chat 任务有 `/mnt/user-data` → 本地目录映射且可读写；Chat 产物经前端 `get_artifact` 可下载；Chat 子代理无法 exec。

### R7 — 旧 lead_agent 处置 + 依赖迁移（澄清确认项）

- **原始诉求**：完全废弃 `lead_agent`；bootstrap 与 custom agent 的依赖先讲清再决定。
- **已敲定**：
  - `lead_agent` 图与 `make_lead_agent` 工厂**彻底移除**。
  - Bootstrap（`is_bootstrap=True`）→ 迁到 `computer_lead_agent`。
  - 自定义 agent（`agent_name` 路径，加载 `agents/<name>/SOUL.md`）→ 默认按 **computer** 能力运行，可经 per-agent 配置覆盖为 chat。
- **完成判据**：代码库无 `make_lead_agent` 悬挂引用；bootstrap/custom agent 路径在新图上可用。

---

## 第二部分 · 关键架构事实（探索阶段已验证）

> 实现方法都建立在这些事实上。执行时若与现实不符，触发对应 Phase 的「阻塞停止条件」。每条标注了文件:行号，便于核对。

### A. 后端路由（最易踩坑）

- **实际生效路由是 Gateway，不是 LangGraph Server。** `docker/nginx/nginx.local.conf` 把 `/api/langgraph/* → gateway`。图选择在 `app/gateway/services.py`：
  - `resolve_agent_factory(assistant_id)`（L158-169）当前**忽略** `assistant_id`，永远返回 `make_lead_agent`。
  - `build_run_config(...)`（L172-240）：任何 `assistant_id != "lead_agent"` 被规范化为注入的 `agent_name`（自定义 agent 启发式，L228）。`_DEFAULT_ASSISTANT_ID = "lead_agent"`（L109）。
  - **结论**：只在 `langgraph.json` 注册新图不够，Gateway 必须认识两个新 id，否则 `computer_lead_agent` 被误判为名为 `computer-lead-agent` 的自定义 agent。
- **Channel / Bootstrap**：`app/channels/manager.py:26` `DEFAULT_ASSISTANT_ID = "lead_agent"`；bootstrap 在 L912 以 `extra_context={"is_bootstrap": True}` 派发；`DEFAULT_RUN_CONTEXT`（L29-33）设 `is_plan_mode: False, subagent_enabled: False`。

### B. Lead Agent 工厂（`deerflow/agents/lead_agent/agent.py`）

- `make_lead_agent(config)`（L487）。`cfg = _get_runtime_config(config)` 合并 `configurable`+`context`。读取（L497-506）：
  ```python
  thinking_enabled        = cfg.get("thinking_enabled", True)
  reasoning_effort        = cfg.get("reasoning_effort", None)
  requested_model_name    = cfg.get("model_name") or cfg.get("model")
  is_plan_mode            = cfg.get("is_plan_mode", False)
  subagent_enabled        = cfg.get("subagent_enabled", False)
  max_concurrent_subagents= cfg.get("max_concurrent_subagents", 3)
  is_bootstrap            = cfg.get("is_bootstrap", False)
  agent_name              = validate_agent_name(cfg.get("agent_name"))
  user_id                 = config.get("metadata", {}).get("user_id")
  ```
- Bootstrap 分支（L561-575）：用最小提示词 + `setup_agent` 工具，`get_available_tools(model_name, subagent_enabled)`，`apply_prompt_template(... available_skills={"bootstrap"})`。
- 非 bootstrap 主路径用 `_build_middlewares(...)`；plan 开关在 `_build_middlewares` L451：`plan_mode=_create_todo_list_middleware(cfg.get("is_plan_mode", False))`。
- 沙盒初始化中间件在 `_build_middlewares` 的 `sandbox=[ThreadDataMiddleware(lazy_init=True), UploadsMiddleware(), SandboxMiddleware(lazy_init=True)]`（L437-439）。
- 子代理由 `subagent_enabled` 开启 → `get_available_tools(subagent_enabled=True)` 加 `task_tool` + `SubagentLimitMiddleware`。

### C. 工具与沙盒

- `deerflow/tools/tools.py:get_available_tools(groups=None, ..., subagent_enabled=False)`（L43）按 `tool.group` 过滤。`subagent_enabled` 时加子代理工具（L97+）。
- 工具组（`config.yaml` L224）：`web, academic_search, file:read, file:write, bash`。
- 文件工具定义（`config.yaml` L391-412）：`ls_tool/read_file_tool/write_file_tool/str_replace_tool` 均 `deerflow.sandbox.tools:*`；`bash_tool` 属 `bash` 组。
- **文件工具与沙盒强耦合**：`write_file_tool`（`sandbox/tools.py`）调用 `ensure_sandbox_initialized(runtime)` + `sandbox.write_file(...)`。
- 沙盒 provider 全局配置（`config.yaml` L511 `sandbox.use: deerflow.community.aio_sandbox:AioSandboxProvider`），非 per-graph。本地有 `LocalSandboxProvider`（落宿主目录，`allow_host_bash` 默认 false）。

### D. 提示词系统

- `deerflow/agents/lead_agent/prompt.py:apply_prompt_template(subagent_enabled, max_concurrent_subagents, *, agent_name, user_id, available_skills, tone_style, app_config)`（L836）→ `_apply_prompt_via_builder()`（L625）用 `SystemPromptBuilder`（`deerflow/prompts/builder.py`），失败回退 `_apply_legacy_prompt_template()`（L873）。
- `SystemPromptBuilder` 组合 `deerflow/prompts/sections.py` ~20 函数：`intro/platform_persona/conversation_craft/collaboration_mechanics/scientific_method/system_rules/task_philosophy/actions/tool_usage/tone_style/environment/git_safety/linter/making_code_changes/session_guidance` 等。静态/动态边界常量 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY`（sections.py L14），`DEFAULT_AGENT_NAME="科学风滚草"`（L12）。
- **子代理**：`deerflow/subagents/builtins/*.py` 5 个内置（general-purpose/bash/explore/plan/verification），各为 `SubagentConfig` dataclass（`config.py`），含**内联静态 `system_prompt` 字符串**。注册表 `registry.py`。执行器 `executor.py:_create_agent`（L339）用 `create_chat_model(thinking_enabled=False)`，`_build_initial_state`（L433-444）把 `config.system_prompt`+skills 合成**单个** `SystemMessage`（注释明示某些 API 拒绝多 system message）。

### E. 状态与产物

- `deerflow/agents/thread_state.py:ThreadState(AgentState)`（L48）：`artifacts: Annotated[list[str], merge_artifacts]`（L52）、`sandbox/thread_data/title/todos/uploaded_files/viewed_images`。**无 `files` 通道**。
- `present_files` 工具（`tools/builtins/present_file_tool.py:79`）：把规范化后的 `/mnt/user-data/outputs/*` 路径经 `Command(update={"artifacts": ...})` 推入 state（L112-117）。
- Gateway `app/gateway/routers/artifacts.py:get_artifact`（L141）从**真实文件系统**经 `thread_resource.resolve_virtual_path` 读内容（L182+）。→ state-backed FS 需桥接。

### F. 模型工厂

- `deerflow/models/factory.py:create_chat_model(name=None, thinking_enabled=False, **kwargs)`（L92）应用 provider 特定推理/thinking kwargs。模型配置 flag：`supports_thinking/supports_reasoning_effort/reasoning_effort_levels/default_reasoning_effort`。

### G. 依赖

- `backend/packages/harness/pyproject.toml`：当前 `langchain>=1.2.3`、`langgraph>=1.0.6,<1.0.10`（已装 langchain 1.2.3 / langgraph 1.0.9）。**无 jinja2、无 langchain-dev-utils**。`uv` 0.11.17 可用。
- langchain-dev-utils：`FormatPromptMiddleware(template_format="jinja2")`（模型调用时从 state+runtime context 解析 `{{ }}`，state 优先）；`load_chat_model`、`register_model_provider`、扩展 `create_agent(model: str, ...)`。

### H. deepagents 文件系统参考（`~/repo_learn/langchain-ai-repos/deepagents`）

- `middleware/filesystem.py`：
  - `FileData`（`backends/protocol.py:157`）：`{content: str, encoding: "utf-8"|"base64", created_at?, modified_at?}`。
  - 状态通道（L264）：`files: Annotated[NotRequired[dict[str,FileData]], DeltaChannel(_file_data_delta_reducer, snapshot_frequency=50)]`。
  - reducer（L242-258）：批量写入，`value is None` 表示删除，否则覆盖。
  - 工具 `ls/read_file/write_file/edit_file/glob/grep`；`execute` 仅当 backend 实现 `SandboxBackendProtocol` 才可用，否则返回 "Execution not available" —— **默认无 bash**。
  - 工具经 `Command(update={"files": ...})` 改状态。

### I. 前端

- `core/threads/use-thread-stream.ts:149` 硬编码 `assistantId: "lead_agent"`；L508-525 mode→后端 flag。
- 模式类型 `"chat"|"agent"|"swarm"`：`core/settings/local.ts:56`、`input-box/mode-utils.ts:3`、`input-box.tsx:100/114`、`welcome.tsx:76`、`mode-hover-guide.tsx:8`。
- `mode-utils.ts`：`getResolvedMode`、`getModeDefaultReasoningEffort`（swarm/agent→high, chat→medium）、`resolveReasoningEffort(..., preferModeDefault)`。
- `input-box.tsx:handleModeSelect` 切模式重置 effort（`preferModeDefault=true`）；agent/swarm 受 `supportThinking` 闸门；沙盒容量拦截 agent/swarm。
- 模式存**全局** settings（非 per-thread），`core/settings/local.ts`/`store.ts`。i18n 在 `core/i18n/locales/{en-US,zh-CN,types}.ts` 的 `inputBox.*`（含 `chatMode/agentMode/swarmMode` + `*Description` + `reasoningEffort*`）。
- `core/threads/types.ts:35` `lead_agent: number` 是 **token-usage caller key**，与路由无关（保留）。

---

## 第三部分 · 执行顺序总览

```
Phase 0  依赖引入 (jinja2 + langchain-dev-utils)
   │
   ▼
Phase 1  统一 build_prompt 工厂 + ground_truth          ←─ 阻塞 Phase 2a
   │
   ▼
Phase 2a 变体核心 + state-backed 虚拟文件系统            ←─ 阻塞 Phase 2b
   │
   ▼
Phase 2b Gateway + Channels 路由 + 图注册
   │
   ├──────────────┬──────────────┐
   ▼              ▼
Phase 3        Phase 4          (3、4 可并行)
effort 解耦     前端模式改造
   └──────┬───────┘
          ▼
Phase 5  验证 (lint / tests / e2e)
```

依赖：P1←P0；P2a←P0+P1；P2b←P2a；P3/P4←P2b；P5←全部。

---

## 第四部分 · 各 Phase 详述（含实现方法）

> 每个 Phase 含六要素表 + 「实现方法」细节。

---

## Phase 0 — 依赖引入

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | `jinja2>=3.1` 与 `langchain-dev-utils`（含 jinja2 中间件所需 extra）进入 `backend/packages/harness/pyproject.toml` 的 `dependencies`；锁文件更新；import 探针成功。 |
| **Verification surface** | `uv lock` 无冲突；`uv sync` 成功；`python -c "import jinja2; from langchain_dev_utils.agents.middleware import FormatPromptMiddleware"` 无报错；`uv pip show langchain-dev-utils jinja2` 显示版本。 |
| **Constraints** | 不动既有依赖版本约束（尤其 `langchain>=1.2.3`、`langgraph>=1.0.6,<1.0.10`）；不引入与现 langchain/langgraph 不兼容的 langchain-dev-utils 版本 —— 有冲突则选兼容版本，而非放宽既有约束。 |
| **Boundaries** | 仅 `backend/packages/harness/pyproject.toml` + `uv.lock`。不碰任何 `.py`。 |
| **Iteration policy** | 加依赖 → `uv lock` → 看冲突 → 不兼容则试兼容版本号 → 每次锁定后跑 import 探针。记录版本矩阵。 |
| **Blocked stop condition** | 若在不放宽既有约束下 langchain-dev-utils 无兼容版本，停止并报告：已试版本组合、`uv lock` 冲突输出、langchain-dev-utils 对 langchain 的版本要求，请求决策（降级功能/仅用 jinja2 自建运行时注入/升级 langchain）。 |

### 实现方法

1. 在 `pyproject.toml` `dependencies` 末尾追加：
   ```toml
   "jinja2>=3.1",
   "langchain-dev-utils>=<经 uv 解析的兼容版本>",
   ```
   若 jinja2 中间件需 extra（文档示例为 `langchain-dev-utils[standard]`），用 `"langchain-dev-utils[standard]>=..."`。
2. 在 `backend/` 执行 `uv lock` → `uv sync`。
3. import 探针：确认 `FormatPromptMiddleware` 的导入路径（候选 `langchain_dev_utils.agents.middleware`，以实际包结构为准）。
4. 记录最终锁定版本到本文件「版本矩阵」附录。

---

## Phase 1 — 统一 build_prompt 工厂 + ground_truth

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | 单一入口 `build_prompt(agent_key, ctx) -> str`，lead（chat/computer）+ 5 子代理全经此生成；内容来自 jinja2 模板 + 共享 `ground_truth.yaml`；`apply_prompt_template` 变薄封装；子代理 `system_prompt=None` 改走 `build_prompt`；静态/动态缓存边界保持；运行时易变量经 `FormatPromptMiddleware(jinja2)` 注入。 |
| **Verification surface** | (a) 快照测试：`build_prompt("computer_lead", ctx)` vs 重构前 `apply_prompt_template(...)` 语义一致（关键 section 出现、顺序、边界标记）。(b) 5 子代理各渲染非空且含 ground_truth 块。(c) `make lint` 绿。(d) 缓存边界测试：仅动态部分变化时静态前缀逐字节一致。 |
| **Constraints** | 不丢任何现有 section 语义；不破坏 prompt-cache 静态前缀稳定性；子代理仍合成**单个** `SystemMessage`；`DEFAULT_AGENT_NAME` 等常量语义不变。 |
| **Boundaries** | `deerflow/prompts/`（新增 `factory/`、`templates/*.j2`、`ground_truth.yaml`）、`deerflow/agents/lead_agent/prompt.py`（改 shim）、`deerflow/prompts/builder.py`+`sections.py`（内容迁模板）、`deerflow/subagents/builtins/*.py`（清内联 prompt）、`deerflow/subagents/executor.py`（`_build_initial_state` 改走 build_prompt）。不碰 agent 工厂 flag 解析（P2a）、不碰前端。 |
| **Iteration policy** | 搭骨架（Environment + ground_truth.yaml + 1 lead 模板）→ 快照对比 1 section → 逐个迁 section 到 partials，每迁一个跑快照 diff 并消解 → 最后迁子代理。每轮记录：迁了哪个 section、diff、下一目标。 |
| **Blocked stop condition** | 若 `FormatPromptMiddleware` jinja2 模式与当前 `create_agent` 中间件链不兼容，停止并报告：报错栈、build-time 渲染能否独立工作、能否退化为「纯 build-time jinja2，不用 FormatPromptMiddleware」，请求决策。若某 section 无法在不破坏缓存边界下模板化，记录该 section + 冲突点后停止。 |

### 实现方法

**1. 目录结构**
```
deerflow/prompts/
├── ground_truth.yaml
├── factory/
│   ├── __init__.py
│   └── build_prompt.py          # Environment + build_prompt(agent_key, ctx)
└── templates/
    ├── ground_truth.j2          # include 进每个 agent/subagent
    ├── lead/{chat.j2, computer.j2}
    ├── subagents/{general_purpose,bash,explore,plan,verification}.j2
    └── partials/{tool_usage,git_safety,linter,memory,skills,
                  subagent_section,environment,tone_style,
                  clarification,working_directory,citations,mcp}.j2
```

**2. `ground_truth.yaml` 模式**
```yaml
identity:
  agent_name: "科学风滚草"
  platform: "Scientific Tumbleweed"
rules:            # 系统级规则（迁自 system_rules_section）
  - ...
scientific_method:   # 迁自 scientific_method_section
  - ...
safety:
  git: ...          # 迁自 git_safety_section
  linter: ...       # 迁自 linter_section
  tools: ...        # 迁自 tool_usage_section
```

**3. `build_prompt(agent_key, ctx)` 签名与契约**
```python
def build_prompt(agent_key: str, ctx: PromptContext) -> str:
    """统一提示词入口。
    agent_key ∈ {"chat_lead","computer_lead",
                 "general-purpose","bash","explore","plan","verification", <custom>}
    ctx 提供 build-time 上下文：
      variant, subagent_enabled, max_concurrent_subagents, agent_name,
      available_skills, tone_style, is_bootstrap, tool_groups,
      memory_section, skills_section, ...
    返回：静态前缀 + SYSTEM_PROMPT_DYNAMIC_BOUNDARY + 动态后缀
    """
```
- jinja2 `Environment(loader=FileSystemLoader(templates/), cache_size=...,
  trim_blocks=True, lstrip_blocks=True)`，模块级单例（缓存编译模板）。
- ground_truth.yaml 解析后作为全局变量注入所有模板（`env.globals["ground_truth"] = ...`）。
- 模板结构：`{% include "ground_truth.j2" %}` + `{% include "partials/..." %}`，静态块在边界标记前，动态块在后。

**4. 运行时注入分工**
- **build-time（jinja2 Environment）**：渲染稳定结构（persona、规则、工具说明、子代理 section、skills 列表）。这部分进 prompt-cache 静态前缀。
- **runtime（FormatPromptMiddleware）**：把 `{{ current_date }}`、`{{ dynamic_memory }}` 等易变量留作占位，挂中间件在模型调用时从 state/runtime context 填充。需在 P2a 把该中间件加入两图的中间件链（本 Phase 先准备模板里的占位语法与中间件实例）。

**5. 迁移策略**
- `apply_prompt_template(...)` 内部改为：组织 `ctx` → `return build_prompt("computer_lead"/"chat_lead", ctx)`。保留函数签名以兼容现有调用点（最小爆破）。
- `sections.py` 每个函数的字符串体逐个搬进对应 `partials/*.j2`；函数可暂保留为「读取模板」的薄封装或最终删除（迁完再删，便于快照对比）。
- 子代理：`builtins/*.py` 的 `system_prompt` 置 `None`；`executor._build_initial_state` 改为 `build_prompt(self.config.name, ctx)`，仍合并进单个 `SystemMessage`。

**6. 快照测试**
- 新增 `tests/prompts/test_build_prompt_parity.py`：固定 ctx，断言 `build_prompt` 输出包含重构前所有关键标记（section 标题/标签），并断言静态前缀在两组仅动态不同的 ctx 下逐字节一致。

---

## Phase 2a — 变体核心 + LocalSandboxProvider 虚拟文件系统

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | `make_lead_agent` 重构为 `_make_lead_agent(config, *, variant)`，暴露 `make_chat_lead_agent`/`make_computer_lead_agent`；`VARIANT_DEFAULTS` 令两者默认 plan ON + subagents ON；chat 用 **variant 感知的 `LocalSandboxProvider`**（`/mnt/user-data` → 本地目录，不起 Docker、无 bash）；computer 与今天 `lead_agent` 等价；chat 产物经 `present_files` + `get_artifact` 可下载（零改动复用）。 |
| **Verification surface** | (a) `make_chat_lead_agent` 工具集不含 bash、文件读写经 Local provider 落本地目录、`docker ps` 无新容器。(b) `make_computer_lead_agent` 含 bash + AioSandbox 容器。(c) 两变体 `is_plan_mode`/`subagent_enabled` 默认 True。(d) chat `write_file→read_file/ls` 往返一致（走 `/mnt/user-data` 映射）。(e) chat 下 `present_files` 后 `get_artifact` 取到内容。(f) 同进程内 chat 用 Local、computer 用 Aio 互不串扰。 |
| **Constraints** | computer 可观察行为（工具集/中间件链/提示词/provider）与重构前一致；provider 全局单例改造**不破坏**现有 thread 内并发取 provider 的线程安全；chat 不拉起 Docker 容器；chat 子代理无 exec。 |
| **Boundaries** | `deerflow/agents/lead_agent/agent.py`、`deerflow/sandbox/sandbox_provider.py`（provider 解析改 variant 感知）、`deerflow/sandbox/middleware.py` 与 `deerflow/sandbox/tools.py`（取 provider 的入口需带 variant/runtime 线索）、`deerflow/tools/tools.py`（按 variant 选工具组、剔 bash）、`deerflow/subagents/*`（chat 子代理无 exec）、`deerflow/agents/__init__.py`。暂不碰 Gateway/Channels/langgraph.json（P2b），本阶段经直接 import 测两工厂。 |
| **Iteration policy** | 先做 `_make_lead_agent(variant)` 重构 + `make_computer_lead_agent` 过「与旧行为一致」快照（工具集/中间件/provider）→ 改 provider 解析为 variant 感知并验证 chat 取到 Local、computer 取到 Aio → chat 剔 bash + 子代理无 exec → 验证 chat 文件往返 + 产物下载。每轮记录：改了什么、computer 一致性快照是否仍绿、下一步。 |
| **Blocked stop condition** | 若 provider 全局单例无法在不破坏 thread 内并发/线程安全的前提下改为 variant 感知（例如取 provider 的调用点拿不到 variant/runtime 线索），停止并报告：受影响的取 provider 调用点清单、并发/线程安全约束、候选方案（按 thread 绑定 variant 的 provider 路由表 vs 双 provider 注册表 + runtime 标记），请求决策。 |

### 实现方法

**1. 变体核心**
```python
# agent.py
VARIANT_DEFAULTS = {
    "chat":     {"is_plan_mode": True, "subagent_enabled": True,
                 "max_concurrent_subagents": 3,
                 "filesystem": "local_dir",   # per-thread 本地目录，无 Docker 沙盒、无 bash（待 Q1 最终确认）
                 "tool_groups": ["web", "academic_search", "file:read", "file:write"]},
    "computer": {"is_plan_mode": True, "subagent_enabled": True,
                 "max_concurrent_subagents": 5,
                 "filesystem": "sandbox",
                 "tool_groups": None},   # None = 全部组
}

def _make_lead_agent(config, *, variant: str):
    cfg = _get_runtime_config(config)
    d = VARIANT_DEFAULTS[variant]
    is_plan_mode     = cfg.get("is_plan_mode", d["is_plan_mode"])
    subagent_enabled = cfg.get("subagent_enabled", d["subagent_enabled"])
    filesystem       = d["filesystem"]   # variant 决定，不从 context 取
    ...  # 其余沿用 make_lead_agent 逻辑

def make_chat_lead_agent(config):     return _make_lead_agent(config, variant="chat")
def make_computer_lead_agent(config): return _make_lead_agent(config, variant="computer")
```
- **默认值仅在 flag 缺省时生效**（显式 context 覆盖），保持向后兼容与可测性。
- `is_bootstrap=True` 走 computer 变体默认。

**2. `ThreadState.files` 通道**（`thread_state.py`）
- 引入 `FileData`（content/encoding/created_at?/modified_at?，对齐 deepagents）。
- 起步用**简单 dict-merge reducer**（非 DeltaChannel，降低 checkpoint 兼容风险）：
  ```python
  def merge_files(existing, new):
      if existing is None: return new or {}
      if new is None:      return existing
      result = dict(existing)
      for k, v in new.items():
          if v is None: result.pop(k, None)
          else:         result[k] = v
      return result
  class ThreadState(AgentState):
      ...
      files: Annotated[NotRequired[dict[str, "FileData"]], merge_files]
  ```
- 若后续大文件深度有性能问题，再评估迁 DeltaChannel（标注在「待敲定」）。

**3. state-FS 工具**（新建 `deerflow/tools/state_fs.py`）
- 提供与沙盒版**同名同签名**的 `ls/read_file/write_file/str_replace`，但经 `state.files` 操作、经 `Command(update={"files": ...})` 写回，**不调用** `ensure_sandbox_initialized`。
- 工具名/参数与沙盒版一致 → 提示词与用户体验不变。
- 写入时填 `created_at/modified_at`（注意：脚本环境禁用 `Date.now()` 等，后端 Python 用 `datetime` 无此限制）。

**4. 按 variant 选工具与中间件**
- `get_available_tools`/工厂：`variant=="chat"`（`filesystem=="state"`）→ 用 state-FS 工具、排除 `bash` 组与沙盒文件工具；`variant=="computer"` → 现状。
- `_build_middlewares`：把 `sandbox=[ThreadDataMiddleware, UploadsMiddleware, SandboxMiddleware]` 门控于 `filesystem=="sandbox"`；chat 跳过这三者，避免沙盒初始化。

**5. 产物桥接（chat）—— 推荐方案 (a)**
- 新建 `state_fs_flush_middleware.py`：在 chat 路径，当 `present_files` 把某路径推入 `state.artifacts` 时，将对应 `state.files[path]` 内容落盘到该 thread 的真实 outputs 目录（`thread_data.outputs_path`），使 Gateway `get_artifact` 下载路径**零改动**。
- 备选 (b)：扩展 `get_artifact` 直接读 checkpoint 的 `state.files`（改动跨到 Gateway，属边界外，作为 Blocked 时的上报选项）。

---

## Phase 2b — Gateway + Channels 路由 + 图注册

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | `langgraph.json` 注册两新图、移除 `lead_agent`；`resolve_agent_factory` 映射两新 id 到工厂；`build_run_config` 把两新 id 当一等图（不降级为 `agent_name`）；`_DEFAULT_ASSISTANT_ID="chat_lead_agent"`；Channels `DEFAULT_ASSISTANT_ID="computer_lead_agent"` + `DEFAULT_RUN_CONTEXT` plan+subagents ON；自定义 agent 默认 computer，可经 per-agent `variant` 覆盖；无 `make_lead_agent` 悬挂引用。 |
| **Verification surface** | (a) 集成请求 `assistant_id="chat_lead_agent"` → 命中 `make_chat_lead_agent`，不被当 agent_name；computer 同理。(b) 自定义 agent（`assistant_id="my-agent"`）仍注入 `agent_name` 并加载 SOUL。(c) bootstrap channel 命令落 computer。(d) `grep -rn "make_lead_agent\|\"lead_agent\""` 仅剩无关项。(e) `make lint` 绿。 |
| **Constraints** | 自定义 agent 的 `agent_name` 注入 + SOUL 加载可用；IM channel 与 HTTP API 行为一致；LangGraph Server 直连路径仍能解析图；`recursion_limit` 等默认不变。 |
| **Boundaries** | `backend/langgraph.json`、`app/gateway/services.py`、`app/gateway/routers/assistants_compat.py`（若校验图名）、`app/channels/manager.py`、`deerflow/config/agents_config.py`（`AgentConfig` 加可选 `variant`）、`debug.py`、`deerflow/agents/__init__.py`。不碰前端、不碰提示词。 |
| **Iteration policy** | 注册图 + 改 `resolve_agent_factory` → 改 `build_run_config` 白名单使两新 id 不被当 agent_name → 改 channels 默认 + bootstrap → 自定义 agent 的 variant 覆盖。每轮用一条 Gateway 集成请求验证路由，记录命中的工厂。 |
| **Blocked stop condition** | 若移除 `lead_agent` 后仍有运行路径硬依赖该图名且边界内无法修复，停止并报告：失败路径与栈、依赖性质、是否需 `lead_agent → chat_lead_agent` 兼容别名，请求决策。 |

### 实现方法

**1. `langgraph.json`**
```json
"graphs": {
  "chat_lead_agent": "deerflow.agents:make_chat_lead_agent",
  "computer_lead_agent": "deerflow.agents:make_computer_lead_agent"
}
```

**2. `resolve_agent_factory`（services.py）**
```python
_GRAPH_FACTORIES = {
    "chat_lead_agent": "make_chat_lead_agent",
    "computer_lead_agent": "make_computer_lead_agent",
}
def resolve_agent_factory(assistant_id):
    from deerflow.agents import make_chat_lead_agent, make_computer_lead_agent
    name = _GRAPH_FACTORIES.get(assistant_id, "make_chat_lead_agent")  # 默认 chat
    return {...}[name]
```

**3. `build_run_config` 白名单（services.py）**
```python
_KNOWN_GRAPH_IDS = {"chat_lead_agent", "computer_lead_agent"}
# 仅当 assistant_id 不在 _KNOWN_GRAPH_IDS（且非空）时，才规范化为 agent_name
if assistant_id and assistant_id not in _KNOWN_GRAPH_IDS:
    normalized = ...  # 自定义 agent 注入逻辑不变
```
- `_DEFAULT_ASSISTANT_ID` → `"chat_lead_agent"`。

**4. Channels（manager.py）**
- `DEFAULT_ASSISTANT_ID = "computer_lead_agent"`（bootstrap 落点）。
- `DEFAULT_RUN_CONTEXT` → `{"thinking_enabled": True, "is_plan_mode": True, "subagent_enabled": True}`（与图默认对齐；注意 thinking 最终仍由 effort 决定，此处为 channel 缺省）。
- bootstrap 派发（L912）不变，仍 `is_bootstrap=True`，现落在 computer 图。

**5. 自定义 agent variant**（agents_config.py）
- `AgentConfig` 增 `variant: Literal["chat","computer"] | None = None`（None → computer 默认）。
- Gateway/factory：自定义 agent 经 `computer_lead_agent` 路由；`_make_lead_agent` 读 `agent_config.variant` 覆盖 filesystem/工具集（若为 chat）。

**6. 清理**
- `deerflow/agents/__init__.py`：移除 `make_lead_agent` 导出，加两新工厂。
- `debug.py` 及其它 import 点改名。`assistants_compat.py` 若枚举/校验图名，更新为两新图。

---

## Phase 3 — reasoning_effort / thinking 解耦（前后端）

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | 后端两图 effort/thinking 仅来自 context（无 mode/variant 派生）；前端 effort 仅来自下拉框（默认取模型默认），`thinking_enabled = supports_thinking && effort!=="none"`；切模式不重置/不影响 effort；`use-thread-stream.ts` 不再从 mode 派生 `is_plan_mode/subagent_enabled/max_concurrent_subagents`。 |
| **Verification surface** | (a) `pnpm typecheck` 绿。(b) `getModeDefaultReasoningEffort` 删除、无残留引用。(c) effort=none → 发送 `thinking_enabled=false`；effort=high 且支持 → true。(d) 切 chat↔computer 后 effort 不变。(e) 后端 grep 无 mode→effort/thinking 派生。 |
| **Constraints** | 不破坏 `supports_reasoning_effort=false` 模型（不发 effort）；不破坏 `supports_thinking=false`（thinking 强制 off）；档位集合仍由 `model.reasoning_effort_levels` 决定；effort 持久化语义不变。 |
| **Boundaries** | 前端 `use-thread-stream.ts`、`mode-utils.ts`、`input-box.tsx`（`handleModeSelect`）。后端仅 `agent.py`（确认无 mode 派生，做防御检查）。不碰提示词、不碰路由。 |
| **Iteration policy** | 删 `getModeDefaultReasoningEffort` 与 `resolveReasoningEffort` 的 `preferModeDefault` 分支 → 修 `handleModeSelect` 不重置 effort → 改 `use-thread-stream.ts` context 组装（thinking 由 effort 推导，移除 mode→flag）→ `pnpm typecheck`。每轮跑 typecheck 看断点。 |
| **Blocked stop condition** | 若移除 mode→flag 后某 UI 逻辑依赖被删函数且无干净替代，停止并报告：受影响组件、依赖链、建议替代信号源，请求确认。 |

### 实现方法

**前端 `use-thread-stream.ts`（L508-525 重写）**
```ts
context: {
  ...extraContext,
  ...context,
  thinking_enabled:
    !!model?.supports_thinking && context.reasoning_effort !== "none",
  reasoning_effort: context.reasoning_effort,  // 仅下拉框
  thread_id: threadId,
  // 删除：is_plan_mode / subagent_enabled / max_concurrent_subagents
  //（后端按图默认）
}
```
- `assistantId` 改为派生（与 P4 协同）：`context.mode === "computer" ? "computer_lead_agent" : "chat_lead_agent"`。

**`mode-utils.ts`**
- 删除 `getModeDefaultReasoningEffort`。
- `resolveReasoningEffort` 去掉 `preferModeDefault` 与 mode 入参，仅按 model 逻辑（默认 = `model.default_reasoning_effort`，限定在 `reasoning_effort_levels`）。

**`input-box.tsx:handleModeSelect`**
- 移除「切模式重算并重置 effort」逻辑；切模式只改 `mode`，不动 `reasoning_effort`。

**后端**
- 确认 `_make_lead_agent` 的 effort/thinking 全部来自 `cfg.get(...)`，variant 不参与（防御性 grep + 注释）。

---

## Phase 4 — 前端 chat/computer 模式改造

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | `InputMode = "chat" | "computer"`；菜单两项（chat=`MessageCircleIcon`，computer=`BotIcon`，去 `NetworkIcon`）；i18n 去 `swarmMode*`、`agentMode*`→`computerMode*`；`assistantId` 由 mode 派生；沙盒容量拦截仅 `computer`；旧持久值 `agent`/`swarm` 迁移为 `computer`。 |
| **Verification surface** | (a) `pnpm check` 绿。(b) `grep -rin "swarm" frontend/src` 空。(c) 切 Computer→请求 `assistantId=computer_lead_agent`；切 Chat→`chat_lead_agent`。(d) 旧 `swarm` localStorage → 规范化为 `computer`，UI 不崩。(e) 沙盒饱和仅拦 Computer。 |
| **Constraints** | 不破坏模式持久化（全局 settings）与跨标签同步；`types.ts` 的 `lead_agent` token-usage key 保留；`ModeHoverGuide`/`Welcome` 两模式都正常；不破坏 `use-chat-mode.ts` 等 URL 参数逻辑。 |
| **Boundaries** | `input-box/{mode-utils.ts,input-box.tsx}`、`core/settings/local.ts`、`workspace/{welcome.tsx,mode-hover-guide.tsx}`、`core/i18n/locales/{en-US,zh-CN,types}.ts`、`app/workspace/chats/[thread_id]/page.tsx`、`core/threads/use-thread-stream.ts`（assistantId，与 P3 协同）。不碰后端。 |
| **Iteration policy** | 改类型 `InputMode` 让 typecheck 报出全部引用 → 逐个修（i18n→图标→hover guide→welcome→page gate→assistantId）→ 加 localStorage 迁移 → `pnpm check`。每轮 typecheck 收敛错误列表。 |
| **Blocked stop condition** | 若「Computer」中英文文案需用户拍板影响 i18n key 定稿，或 welcome 的 swarm 渐变改造涉及视觉决策，停止并报告所需文案/视觉决策，给占位实现。其余技术问题不阻塞。 |

### 实现方法

1. **类型**：`mode-utils.ts` `InputMode = "chat" | "computer"`；同步 `local.ts:56`、`input-box.tsx:100/114`、`welcome.tsx:76`、`mode-hover-guide.tsx:8`（`AgentMode`）。
2. **i18n**（en-US/zh-CN/types）：删 `swarmMode`/`swarmModeDescription`；`agentMode`→`computerMode`、`agentModeDescription`→`computerModeDescription`（文案见「待敲定」，先占位）。
3. **图标/标签**（`input-box.tsx` L434-448 及菜单 L451+）：仅 chat/computer 两项；删 `NetworkIcon` 与 swarm 分支。
4. **`mode-hover-guide.tsx`**：`getModeLabelKey/getModeDescriptionKey` 改两分支。
5. **`welcome.tsx`**：删 `isSwarm` 渐变（L81-87），两模式中性样式（或给 computer 一个 accent，属视觉决策→待敲定）。
6. **`page.tsx` L241**：沙盒容量 gate 改为仅 `mode === "computer"`。
7. **迁移**：`local.ts:mergeLocalSettings` 把 `context.mode` 为 `"agent"|"swarm"` 规范化为 `"computer"`。
8. **`getResolvedMode`**：去掉 `supportsThinking` 对模式可见性的闸门（R5 后模式不再依赖 thinking）；两模式恒可选。

---

## Phase 5 — 验证（lint / tests / e2e）

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | 后端 `make lint`+`make test` 全绿（含更新/新增测试）；前端 `pnpm check` 全绿；`make dev` 起栈后 e2e 手测清单全过；`build_prompt` 输出 vs 重构前快照无回归。 |
| **Verification surface** | `make lint`/`make test`/`pnpm check` 退出码与输出；`make dev` 下实际 HTTP 请求（`assistantId`）、`docker ps`、产物下载 200、消息流 plan/subagent 行为；build_prompt 快照 diff。 |
| **Constraints** | 既有测试保持绿（不为过测删断言）；computer 行为与重构前等价；验证不留临时文件/脏状态。 |
| **Boundaries** | `backend/tests/**`、`frontend/tests/**`（如有）。可运行 `make lint`/`make test`/`pnpm check`/`make dev`。回归修复回溯到对应 Phase 边界文件。 |
| **Iteration policy** | backend `make lint`→`make test`（逐个修，分「测试需更新」与「真回归」）→ frontend `pnpm check` → `make dev` e2e。每轮记录失败项、根因分类、修复、下一项。 |
| **Blocked stop condition** | 若 `make test`/`make dev` 因环境（缺依赖/Docker/API key/沙盒镜像）无法运行，停止并报告：命令与报错、已过静态检查范围、所需环境前置，请求环境支持。若同一路径两次修复失败，停止并报告失败测试、两次尝试、怀疑根因、所需输入。 |

### e2e 手测清单

- [ ] Chat 发消息 → `assistantId=chat_lead_agent`
- [ ] Chat 下 `docker ps` 无新增沙盒容器
- [ ] Chat 写文件（state-FS）→ `present_files` → 前端可下载
- [ ] Chat plan（todo）+ subagent 委派可用、无 bash 工具
- [ ] Computer → `assistantId=computer_lead_agent`、全沙盒 + bash
- [ ] Computer plan + subagent 生效
- [ ] effort=none → 不思考；effort=high → 思考
- [ ] 切 chat↔computer → effort 不变
- [ ] `/bootstrap` channel 命令 → 落 computer 图
- [ ] 自定义 agent 默认按 computer 能力运行（或其配置 variant）
- [ ] build_prompt 渲染快照 vs 重构前无语义回归

---

## 第五部分 · 待敲定清单（需要和你确认）

> 这些点会影响实现细节，建议在进入对应 Phase 前确认。标 ⭐ 的影响较大。✅ = 已敲定。

1. ✅ **Chat 产物桥接 / 文件空间形态**：已定为「每个 Chat 任务默认开辟一个 per-thread 本地目录」。**遗留 ⭐ Q1’**（见下）：本地目录用「复用 `LocalSandboxProvider`」还是「纯 state-backed FS + flush 落盘」实现 —— 二者下载都可零改动，但实现路径不同。
2. ⭐ **Computer 模式文案**：i18n 的 `computerMode` / `computerModeDescription` 中英文最终用词（"Computer" / "电脑模式" / "电脑" / 其他）。Chat 文案是否也调整？（未定，P4 先占位）
3. ✅ **Chat 工具集范围**：已定 = `[web, academic_search, file:read, file:write]`（联网检索 + 读写文件，无 bash）。
4. **state-FS reducer**：仅当 Q1’ 选「纯 state-backed」时相关；选 LocalSandboxProvider 则无需 `ThreadState.files` 通道。
5. ✅ **max_concurrent_subagents 默认值**：已定 Computer=5 / Chat=3。
6. ✅ **Chat 联网检索**：已定保留（见 Q3）。
7. ✅ **Chat 的子代理 exec**：已定「保留子代理但同样无 exec/bash」。实现：Chat 路径下子代理也走无沙盒/无 bash 配置（剔除 bash 子代理的执行工具，或令其 execute 不可用）。
8. **兼容别名**：是否保留临时 `lead_agent → chat_lead_agent` 别名防遗漏外部调用？（默认否，彻底移除）
9. **thinking 与 channel 缺省**：IM channel 的 `DEFAULT_RUN_CONTEXT` 是否也按「effort 决定 thinking」，还是 channel 保持 `thinking_enabled: True` 简化？（未定）
10. ✅ **bootstrap 文件能力**：已定落 computer（有沙盒），符合技能创建需求。

### ⭐ Q1’ — Chat 本地目录的实现路径（已含关键约束，需你拍板，决定 P2a 写法）

> **关键约束（已核实）**：`deerflow/sandbox/sandbox_provider.py:get_sandbox_provider()` 是**进程级全局单例**（`_default_sandbox_provider`，从 `config.sandbox.use` 解析并缓存）。同一进程内 Chat 与 Computer **共享同一个 provider 实例**，无法仅靠「Chat 用 LocalSandboxProvider」按图切换。这否定了「直接复用沙盒文件工具但换 provider」的简单做法。

| 方案 | 做法 | 优点 | 代价 / 风险 |
| --- | --- | --- | --- |
| **(I) per-run provider 覆盖** | 把 provider 从全局单例改成可按 run/variant 解析（Chat→Local，Computer→Aio），文件工具沿用。 | 复用现有文件工具/产物/下载/中间件。 | 触碰全局单例核心，跨 `ensure_sandbox_initialized` 的取 provider 路径，回归面大、并发隔离要重验。 |
| **(II) 纯 state-backed FS + flush（deepagents 式）** | 新建 `ThreadState.files` + state-FS 工具，present 时 flush 落盘到 per-thread 目录。 | 与全局沙盒单例**完全解耦**，Chat 真正不碰沙盒；最贴合「不启动沙盒」。 | 新工具 + 状态通道 + reducer + checkpoint 兼容 + flush 中间件；与沙盒文件工具并行维护。 |
| **(III) 轻量本地目录文件工具（不走 provider 抽象）** | 新建一组直接读写 per-thread 宿主目录的文件工具（`ls/read_file/write_file/str_replace`），不经 `get_sandbox_provider`、不经 `ensure_sandbox_initialized`；目录即真实磁盘，`get_artifact` 零改动。 | 不动全局单例；天然落盘、下载零改动；比 (II) 少了状态通道/reducer/checkpoint 复杂度；契合「开辟一个本地目录」字面。 | 新增一组文件工具实现（但可薄封装 `pathlib`）；需做与沙盒版一致的路径校验/越界防护。 |

> **更新后的倾向：方案 (III)**。鉴于 provider 是全局单例，(I) 风险最高；(II) 引入状态通道与 checkpoint 复杂度且与你「本地目录」描述略有偏差；(III) 既满足「per-thread 本地目录、不启动 Docker 沙盒、无 bash、产物可下载」，又不触碰全局单例、不引入状态通道。**待你确认 (III) 是否就是你要的「本地目录」。**

> 无论选哪个，Chat 都**不暴露 bash**、其**子代理也无 exec**（Q7 已定）。

---

## 第六部分 · 完成定义（Definition of Done）

全部 Phase 的 Outcome 为真，且：

1. 前端只有 Chat / Computer 两个模式，无 Swarm。
2. 两模式默认 plan ON + subagents ON。
3. Chat 不起 Docker 沙盒、有 LocalSandboxProvider-backed 文件空间且产物可下载；Computer 与原 `lead_agent` 等价。
4. 所有 agent + subagent 提示词经 `build_prompt` + jinja2 + `ground_truth` 统一生成。
5. reasoning_effort / thinking 仅由模型 + effort 下拉框控制，与模式解耦。
6. `lead_agent` 图与 `make_lead_agent` 彻底移除，bootstrap/自定义 agent 已迁移。
7. `make lint` / `make test` / `pnpm check` 全绿，e2e 手测清单通过。

---

## 附录 · 版本矩阵（Phase 0 执行后填写）

| 包 | 锁定版本 | 备注 |
| --- | --- | --- |
| jinja2 | 3.1.6 | `uv lock` + `uv sync` 后探针通过 |
| langchain-dev-utils | 1.4.6 | FormatPromptMiddleware 导入路径：`langchain_dev_utils.agents.middleware` |
| langchain | 1.2.3 | 不变 |
| langgraph | 1.0.9 | 不变 |
