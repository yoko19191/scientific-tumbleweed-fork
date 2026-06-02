# Agents 模块化重构方案：围绕 create_agent 的语义化目录 + Prompt 正文全面模板化

> 文档版本：2026-06-02
> 作者：科学风滚草 (Kiro)
> 状态：已执行（核心 agents 模块化、prompt 单一路径、suggestion/title harness 模块已落地）
> 关联计划文件：`~/.claude/plans/quiet-snacking-waterfall.md`
> 前序方案：`docs/refactor/20260601_agent_mode_spilt.md`（Chat/Computer 拆分 + 统一 build_prompt 工厂，本方案在其基础上继续收敛）

---

## 总体目标

把 `backend/packages/harness/deerflow/agents/` 重构成**语义化、高内聚、低耦合**的模块结构，让一切围绕最核心的构造方法 `langchain.agents.create_agent` 展开：

- **每个 `agents/xxx_agent/` 是一个自包含的 agent 模块**：自己的构图逻辑、自己的 prompt、自己独有的配置都在模块内。
- **共享配置项下沉到 `config/` 或 agent 模块的 `config.py`**，用 typed profile 取代散落的 dict。
- **Prompt 正文全部进 `.j2` 模板**，Python 不再持有 prompt 正文，jinja2 + `ground_truth` 成为唯一的 prompt 语义来源。
- **尽可能减少 `load_*` / 重复 helper 函数**，消除多路径、多份拷贝。

本次落地的 agent 模块：两个 lead agent（`chat` / `computer`）+ `suggestion_agent` + `title_agent`。

---

## 第一部分 · 需求（Requirements）

> 每条给出「原始诉求」+「精确定义」+「完成判据」，避免歧义。

### R1 — agents 目录语义化模块化

- **原始诉求**：整个 agents 结构语义不清晰，没有高内聚低耦合；期望围绕 `create_agent` 构建语义，每个 `agents/xxx_agent` 是独立模块。
- **精确定义**：
  - `agents/` 顶层只保留**跨 agent 共享**的东西：`factory.py`（`create_deerflow_agent` SDK 入口）、`middleware_builder.py`、`features.py`、`thread_state.py`、`middlewares/`、`memory/`、`checkpointer/`。
  - 每个具体 agent 是一个子包：`lead_agent/`（含 chat/computer 两个变体）、`suggestion_agent/`、`title_agent/`，各自持有 `agent.py`/`config.py`/`prompt.py`（按需）。
  - agent 独有的配置（变体默认值、tool group、prompt key）放在该 agent 模块的 `config.py`，不再散落在 `agent.py` 顶部的模块级 dict。
- **完成判据**：`agents/` 顶层文件职责单一可一句话说清；`grep` 不到跨 agent 的私有配置 dict（如 `VARIANT_DEFAULTS`）残留在构图代码里；`make lint` 绿。

### R2 — Prompt 正文全面模板化（Python 不持有正文）

- **原始诉求**：`prompts/sections` 拆分没有分离；很多 prompt 没有实现 jinja2 控制。
- **精确定义**：
  - `prompts/sections.py` 与 `lead_agent/prompt.py` 中所有**返回 prompt 正文字符串**的函数，其正文迁入 `prompts/templates/partials/*.j2`。
  - Python 侧只保留「装配 `PromptContext` + 调用 `build_prompt`」的薄逻辑；不再有内联多行中文 prompt 正文。
  - 静态正文（身份、规则、科学方法论、安全约束）尽量收敛到 `ground_truth.yaml`，被所有模板 `include`。
  - 运行时易变占位符（日期、memory 等）由 `FormatPromptMiddleware(jinja2)` 注入，模板中以 `{% raw %}{{ var }}{% endraw %}` 透传到运行时。
- **完成判据**：`prompts/sections.py` 与 `lead_agent/prompt.py` 中无内联 prompt 正文（grep XML 标签如 `<git_safety>`、`<citations>` 仅命中 `.j2`）；重构前后 `build_prompt` 输出快照语义一致；静态/动态缓存边界 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 位置不变。

### R3 — lead_agent 拆分为 base + chat + computer + config

- **原始诉求**：`chat_lead_agent` 和 `computer_lead_agent` 没有实现模块拆分。
- **精确定义**：
  - `lead_agent/` 下拆为 `base.py`（共享 `create_agent` 装配 + 中间件链 + 模型解析）、`chat.py`（`make_chat_lead_agent`）、`computer.py`（`make_computer_lead_agent`）、`config.py`（typed `LeadProfile`，取代 `VARIANT_DEFAULTS` dict）、`prompt.py`（保留，但变薄）。
  - `agent.py` 现有 695 行的 `_make_variant_lead_agent` + 私有中间件工厂拆进 `base.py`；两个变体入口只声明差异（profile）。
- **完成判据**：`langgraph.json` 两个图 id 不变（`chat_lead_agent` / `computer_lead_agent`）且仍可构建；`VARIANT_DEFAULTS` dict 被 typed profile 取代；`test_lead_agent_*` 全绿（必要时更新 import 路径）。

### R4 — 抽出 suggestion_agent / title_agent 为 harness 模块

- **原始诉求**：agents 模块化应包含 suggestion_agent、title_agent 等。
- **精确定义**：
  - 新建 `agents/suggestion_agent/`：含 prompt（模板化）+ `generate_suggestions(messages, n, model_name) -> list[str]` 纯函数；`app/gateway/routers/suggestions.py` 变成只做 FastAPI 端点 + 鉴权 + 调用该函数的薄壳。
  - 新建 `agents/title_agent/`：把 `title_middleware.py` 中的 prompt 构造、`_parse_title`、`_fallback_title`、模型调用抽进模块；`TitleMiddleware` 保留 state 判定（`_should_generate_title`、`after_model`/`aafter_model` 钩子）并调用该模块。
- **完成判据**：harness 不 import `app`（保持现状）；`run_name` 仍为 `"suggest_agent"` / `"title_agent"`；`test_suggestions_router.py`、`test_title_*` 全绿（更新 import 到新模块）。

### R5 — 删除冗余 prompt 旧路径

- **原始诉求**：减少多余实现、提高内聚。
- **精确定义**：删除 `lead_agent/prompt.py` 的 `SYSTEM_PROMPT_TEMPLATE`（~50 行 `.format()` 模板）与 `_apply_legacy_prompt_template`；删除 `prompts/builder.py` 的 `SystemPromptBuilder`（现仅测试在用）；统一收敛到 `prompts/factory/build_prompt.py` 单一路径。
- **完成判据**：`grep SYSTEM_PROMPT_TEMPLATE / _apply_legacy_prompt_template / SystemPromptBuilder` 为空（除被改写的测试）；`build_prompt` 是唯一 prompt 生成入口；缓存边界测试仍绿。

### R6 — 尽可能减少 load / 重复 helper 函数

- **原始诉求**：尽可能减少 load 函数。
- **精确定义**：
  - 合并重复的 `_call_with_optional_app_config`（`agent.py:86` 与 `prompt.py:192` 两份）到一个共享位置。
  - `apply_prompt_template` 由「thick shim + builder + 回退」收敛为「组装 ctx → `build_prompt`」的薄包装（删除回退分支后自然变薄）。
  - 把 `prompt.py` 的 enabled-skills 缓存机制（~9 个私有/公开函数 + 模块级线程状态）收拢进单一 `skills_cache.py` 模块，对外只暴露必要入口（`prime` / `get_cached` / `invalidate`）。
- **完成判据**：`_call_with_optional_app_config` 仅一份定义；`prompt.py` 行数显著下降（目标 < 300 行）；skills 缓存内部细节不再散布在 `prompt.py` 顶层；`test_lead_agent_prompt.py` 中引用的缓存符号通过新模块或兼容再导出仍可访问。

---

## 第二部分 · 现状事实（已核实，含 file:line）

### A. 目录与入口

- `langgraph.json` 注册两图：`chat_lead_agent` / `computer_lead_agent` → `deerflow.agents:make_chat_lead_agent` / `make_computer_lead_agent`。
- `agents/__init__.py:1-25`：导出 `create_deerflow_agent`、`make_chat/computer_lead_agent`、`prime_enabled_skills_cache`；**模块导入期即调用 `prime_enabled_skills_cache()`**（L11，副作用）。
- `agents/lead_agent/__init__.py`：仅 re-export 两个 `make_*`。

### B. lead agent 构图（耦合点）

- `agents/lead_agent/agent.py`（695 行）：
  - `VARIANT_DEFAULTS` dict（L57-74）= chat/computer 两套差异（`is_plan_mode`/`subagent_enabled`/`max_concurrent_subagents`/`tool_groups`/`sandbox_provider_variant`/`agent_key`）。**这是该模块化掉的私有配置 dict**。
  - `_get_runtime_config`（L77）、`_call_with_optional_app_config`（L86，**与 prompt.py 重复**）。
  - 私有中间件工厂：`_create_guardrail_middleware`（L297）等 + `_build_middlewares`（L459-487 装配 `build_ordered_middleware_chain`）。
  - 单一 `_make_variant_lead_agent` 承载 bootstrap 分支（L641-660）与主路径（L662-687），两个 `make_*`（L690-695）只是 `variant=` 包装。
- `middleware_builder.py:build_ordered_middleware_chain`（L33-88）= 中间件顺序唯一真源，保留。

### C. prompt 系统（三路径 + 正文散落）

- `agents/lead_agent/prompt.py`（944 行）：
  - enabled-skills 缓存机制：`_load_enabled_skills_sync`/`_ensure_/_invalidate_/prime_/warm_enabled_skills_cache`/`_get_enabled_skills`/`get_cached_enabled_skills`/`get_enabled_skills_for_config`/`_refresh_enabled_skills_cache`（L30-176）+ 模块级线程状态（`_enabled_skills_lock`/`_enabled_skills_cache`/`_enabled_skills_refresh_event`，L22-27）。
  - **内联正文 section 构造器**：`_build_subagent_section`（L203）、`_build_clarification_section`（L698，含 OpenUI Lang 含字面量 `{`）、`_build_working_directory_section`（L788）、`_build_self_update_section`（L807）、`_build_citations_section`（L822）、`_build_acp_section`（L576）、`_build_custom_mounts_section`（L600）、`_build_skill_evolution_section`（L176）、`get_skills_prompt_section`/`_get_cached_skills_prompt_section`（L461-492）。
  - `apply_prompt_template`（L845）→ `_apply_prompt_via_builder`（L627，调 `build_prompt`）；失败回退 `_apply_legacy_prompt_template`（L884）用 `SYSTEM_PROMPT_TEMPLATE`（L374，`.format()` 模板）。
- `prompts/sections.py`（323 行）：~16 个 section 函数。静态：`intro/platform_persona/conversation_craft/collaboration_mechanics/scientific_method/system_rules/task_philosophy/actions/tool_usage/git_safety/linter/making_code_changes`；带参：`tone_style_section(tone_style)`、`environment_section(cwd,date_str)`、`session_guidance_section(...)`、`intro/platform_persona(agent_name)`。常量 `DEFAULT_AGENT_NAME="科学风滚草"`、`SYSTEM_PROMPT_DYNAMIC_BOUNDARY`（L12-14）。
- `prompts/builder.py:SystemPromptBuilder`（212 行）：**仅 `test_prompt_builder.py` 与 prompt.py 注释引用**，生产路径实际走 factory。
- `prompts/factory/build_prompt.py`：**已存在的统一工厂**。`PromptContext` dataclass（L51-76）；`_LEAD_AGENT_KEYS`/`_SUBAGENT_KEYS`（L38-48）；jinja2 `Environment` + `env.globals["ground_truth"]`（L88-98）；`_build_lead_static_sections`（L109）仍**调用 sections.py 函数拼接**（即正文仍在 Python）。
- `prompts/templates/`：`lead/chat.j2` 与 `lead/computer.j2` **字节相同**（仅 `{{ static_sections }}`/`{{ dynamic_sections }}`）；`ground_truth.j2` 已用 `{{ ground_truth.* }}` 循环；`subagents/*.j2` 5 个。
- `prompts/ground_truth.yaml`：已含 `identity/rules/scientific_method/safety.{git,tools}`。

### D. 运行时双重 jinja2 渲染（关键约束，已核实）

- `FormatPromptMiddleware`（`.venv/.../langchain_dev_utils/agents/middleware/format_prompt.py`）：`_format_prompt` 用 `get_template_variables(prompt, "jinja2")` 抽变量 → 从 `state` 再 `context` 取值 → `Template(system_prompt).render(**params)`（约 L107-128）。即**运行时对 system prompt 再渲染一次 jinja2**。
- `agent.py` 中间件链含 `FormatPromptMiddleware(template_format="jinja2")`（L457/476）。
- **共存安全性**：section 正文中**无 `{{ }}`/`{% %}` 元字符**（已 grep 确认），只有字面量单 `{`（sections.py 8 处、prompt.py 55 处，多在 OpenUI Lang 示例）。jinja2 只解析 `{{`/`{%`，单 `{` 安全；但 `.format()` 旧路径对单 `{` 不安全 → 删除 legacy 后这一隐患一并消除。
- **迁模板注意**：凡需运行时注入的占位符（如 `{{ current_date }}`），partial 内必须用 `{% raw %}...{% endraw %}` 包裹，避免 build-time 提前消费。

### E. harness / app 边界（已核实）

- `grep "^from app|^import app"` 在 `packages/harness/deerflow` **为空** → harness 不依赖 app。
- `app/gateway/routers/suggestions.py` import `deerflow.models.create_chat_model` → app 依赖 deerflow（方向正确）。
- suggestions 注册：`app/gateway/routers/__init__.py:1`、`app/gateway/app.py:23/381`（`/api/threads/{thread_id}/suggestions`）。

### F. suggestion / title 现状

- `suggestions.py`：纯函数 `_strip_markdown_code_fence`/`_parse_json_string_list`/`_extract_response_text`/`_format_conversation`（L31-93）+ 端点 `generate_suggestions`（L102），内联 system prompt（L113-123），`create_chat_model(thinking_enabled=False)` + `run_name="suggest_agent"`（L126-127）。
- `title_middleware.py`：`_build_title_prompt`（L94，用 `title_config.prompt_template.format(...)`）、`_parse_title`/`_fallback_title`、`_agenerate_title_result`（L142，`create_chat_model(thinking_enabled=False)` + `run_name="title_agent"`）、`after_model`/`aafter_model`（L166-172）。`title_config.py` 已是独立 config。

### G. 测试契约（必须保留/改写）

- `test_prompt_builder.py`：**全部测 `SystemPromptBuilder`**（删除后须改写为测 `build_prompt`，断言保持：`<role>`/`<platform_persona>`/边界/branding/各 section 出现）。
- `test_lead_agent_prompt.py`：测 `apply_prompt_template(...)` 签名与输出 + 直接 monkeypatch 缓存内部符号（`_get_cached_skills_prompt_section`/`_enabled_skills_lock`/`_enabled_skills_cache`/`_get_enabled_skills`）→ skills 缓存搬模块后需保留兼容再导出。
- `test_lead_agent_skills.py`：`from ...prompt import get_skills_prompt_section`。
- `test_suggestions_router.py`：`from app.gateway.routers import suggestions`，monkeypatch `suggestions.create_chat_model`，断言 `run_name=="suggest_agent"`，并直接调 `_strip_markdown_code_fence`/`_parse_json_string_list`/`_format_conversation`（这些须在 router 仍可访问 → router 从新模块再导出）。
- `test_title_generation.py` / `test_title_middleware_core_logic.py`：测 `TitleMiddleware` 初始化与 config，`run_name=="title_agent"`。

### H. load / 重复函数清单

- 重复：`_call_with_optional_app_config` 两份（`agent.py:86`、`prompt.py:192`）。
- `agents/`、`config/` 共 ~19 个 `load_*` / `apply_*`（多为 `config/*_config.py` 的 `load_*_from_dict`，本次**不动 config 层**，只收敛 agents 层的重复 helper 与 skills 缓存）。

---

## 第三部分 · 执行顺序

```
Phase 0  基线快照 + 契约固定        (保护网，先行)
   │
Phase 1  Prompt 正文全面模板化      (sections + lead 内联 builder → partials/*.j2；依赖 P0 快照)
   │
Phase 2  删除 legacy + SystemPromptBuilder   (单一 build_prompt 路径；依赖 P1)
   │
Phase 3  lead_agent 模块拆分        (base/chat/computer/config；依赖 prompt 稳定)
   │
Phase 4  suggestion_agent / title_agent 模块化   (与 P3 解耦，可并行，排在后)
   │
Phase 5  load 函数收敛 + 收尾       (合并 helper、skills_cache 模块、最终验证)
```

每个 Phase 独立可验证、可单独提交，绿灯后再进下一阶段。

---

## Phase 0 — 基线快照与契约固定

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | 生成「重构前」黄金快照：`build_prompt("chat_lead", ctx)`、`build_prompt("computer_lead", ctx)`、5 个 subagent prompt，落盘为快照基线；锁定关键断言（section 出现、顺序、`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 位置、branding）。 |
| **Verification surface** | 新增 `tests/test_prompt_snapshot.py` 跑通并写出基线；`make lint`/现有 `make test` 子集绿；记录当前 `prompt.py`/`agent.py` 行数作为收敛基线。 |
| **Constraints** | 不改任何生产代码，仅加测试与快照夹具；快照需用**确定性 ctx**（固定 `date_str`、固定 skills 列表）避免环境噪声。 |
| **Boundaries** | 仅 `backend/tests/`（新增快照测试 + 夹具）。 |
| **Iteration policy** | 写快照测试 → 跑一次写基线 → 人工抽查关键 section 完整 → 提交基线。 |
| **Blocked stop condition** | 若 `build_prompt` 输出含不可控非确定性（随机/时间）无法稳定快照，先定位来源并以参数注入消除；无法消除则记录并改用「关键 section 子串断言」替代逐字节快照。 |

### 实现方法

1. 新增 `tests/test_prompt_snapshot.py`：用固定 `PromptContext`（`date_str="2026-06-02"`、`agent_name=None`、`subagent_enabled=True/False` 两组）调 `build_prompt`，对输出做逐字节快照（首跑写 `tests/snapshots/*.txt`）。
2. 覆盖 lead（chat/computer × subagent on/off）+ 5 个 subagent key。
3. 锁断言：`<role>`/`<platform_persona>`/`<git_safety>`/`<citations>`/`<scientific_method>` 出现，`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 唯一且位置正确，`科学风滚草`/`良渚实验室` 在静态前缀，`DeerFlow 2.0` 不出现。
4. 记录基线行数：`prompt.py` 944 / `agent.py` 695。

---

## Phase 1 — Prompt 正文全面模板化

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | `prompts/sections.py` 与 `lead_agent/prompt.py` 的所有 prompt 正文迁入 `prompts/templates/partials/*.j2`；`sections.py` 函数体改为「渲染对应 partial」或直接删除并由 `build_prompt` 模板 `include`；静态正文尽量进 `ground_truth.yaml`。 |
| **Verification surface** | Phase 0 快照逐字节一致（或差异仅为空白，经审阅 accept 后更新基线）；`grep` XML 标签（`<git_safety>`/`<citations>`/`<clarification_system>`/`<working_directory>`/`<self_update>`/`<subagent_system>`）仅命中 `.j2`；`make lint` 绿。 |
| **Constraints** | 不丢任何 section 语义；缓存静态前缀逐字节稳定；运行时占位符用 `{% raw %}{{ var }}{% endraw %}`；OpenUI Lang 字面量 `{` 在模板中保持原样（jinja2 不解析单 `{`）。 |
| **Boundaries** | `prompts/templates/`（新增 partials）、`prompts/sections.py`（正文搬空）、`prompts/factory/build_prompt.py`（`_build_lead_*_sections` 改为模板 include 或渲染 partial）、`prompts/ground_truth.yaml`（扩充）、`lead_agent/prompt.py`（内联 builder 改为渲染 partial）。不碰 agent 工厂、不碰 builder.py（留待 P2 删）。 |
| **Iteration policy** | 一次迁一个 section：建 partial → 改 Python 调用点为渲染该 partial → 跑快照 diff → 消解差异 → 下一个。先迁纯静态（git_safety/linter/scientific_method...），再迁带参（intro/platform_persona/tone_style/environment），最后迁条件型（subagent/clarification/working_directory/self_update/citations/acp）。 |
| **Blocked stop condition** | 若某 section 含运行时占位符与 build-time 渲染冲突且 `{% raw %}` 不能解决，记录该 section + 报错栈后停止请求决策；若双重 jinja2 渲染对某 partial 报错（如 OpenUI 含被误判的语法），记录最小复现后停止。 |

### 实现方法

**1. 目标模板结构**
```
prompts/templates/
├── ground_truth.j2                 # 已存在，扩充
├── lead/{chat.j2, computer.j2}     # 已存在；引入差异化 include
└── partials/
    ├── intro.j2  platform_persona.j2  conversation_craft.j2
    ├── collaboration_mechanics.j2  scientific_method.j2  system_rules.j2
    ├── task_philosophy.j2  risk_actions.j2  tool_usage.j2  tone_style.j2
    ├── git_safety.j2  linter.j2  making_code_changes.j2  environment.j2
    ├── subagent_section.j2  clarification.j2  working_directory.j2
    ├── self_update.j2  citations.j2  skills.j2  skill_evolution.j2
    └── acp.j2  custom_mounts.j2
```

**2. ground_truth.yaml 扩充**：把 `system_rules` / `scientific_method` / `git_safety` / `linter` / `tool_usage` 中**已是 canonical 事实**的条目并入 `ground_truth.yaml`（其余 agent 专属语气留 partial），由 `ground_truth.j2` 循环渲染。

**3. Python 侧改造**：`sections.py` 的 `git_safety_section()` 等改为 `return _render_partial("git_safety.j2")` 或彻底删除、由 lead 模板直接 `{% include "partials/git_safety.j2" %}`。带参 section（`intro_section(agent_name)`）→ partial 用 `{{ agent_name }}`（build-time 由 `build_prompt` 传入，非运行时）。

**4. 条件型 section**：`subagent_section` 在 `lead/*.j2` 用 `{% if subagent_enabled %}{% include "partials/subagent_section.j2" %}{% endif %}`，并发数 `{{ max_concurrent_subagents }}` build-time 注入。`clarification.j2` 原样搬入（含 OpenUI Lang），单 `{` 不动。

**5. 运行时占位符**：`environment` 的日期若走 `FormatPromptMiddleware`，在 partial 中 `{% raw %}{{ current_date }}{% endraw %}`；若走 build-time，则直接 `{{ date_str }}`（保持现状语义，二选一与现状对齐）。

---

## Phase 2 — 删除 legacy 模板 + SystemPromptBuilder

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | 删除 `lead_agent/prompt.py` 的 `SYSTEM_PROMPT_TEMPLATE` + `_apply_legacy_prompt_template`；删除 `prompts/builder.py:SystemPromptBuilder`；`build_prompt` 成为唯一 prompt 路径；`apply_prompt_template` 收敛为「组 ctx → build_prompt」薄包装。 |
| **Verification surface** | `grep SYSTEM_PROMPT_TEMPLATE / _apply_legacy_prompt_template / SystemPromptBuilder` 为空；`test_prompt_builder.py` 改写为测 `build_prompt` 后绿；Phase 0 快照仍一致；`make lint` 绿。 |
| **Constraints** | 删除前确认无生产引用（已核实 builder 仅测试在用、legacy 仅作回退）；`split_prompt_for_caching` 与 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 保留（被 `prompts/__init__.py` 与缓存逻辑用）。 |
| **Boundaries** | `lead_agent/prompt.py`（删 legacy 分支 + 模板常量）、`prompts/builder.py`（删除文件）、`prompts/__init__.py`（移除 `SystemPromptBuilder` 导出）、`tests/test_prompt_builder.py`（改写）。 |
| **Iteration policy** | 先改写测试指向 `build_prompt` 并绿 → 删 `apply_prompt_template` 的 try/except 回退 → 删 `_apply_legacy_prompt_template` + `SYSTEM_PROMPT_TEMPLATE` → 删 `builder.py` + 导出 → 全量跑相关测试。 |
| **Blocked stop condition** | 若删除 `SystemPromptBuilder` 后发现非测试隐式引用（动态 import / 反射），记录引用点后停止；若 `apply_prompt_template` 去回退后某路径 `build_prompt` 抛错，回到 P1 修模板而非恢复 legacy。 |

### 实现方法

1. 改写 `tests/test_prompt_builder.py`：`SystemPromptBuilder(...).build()` → `build_prompt("computer_lead", PromptContext(...))`，断言不变（branding/边界/section）。
2. `apply_prompt_template`（prompt.py L845）：删除 `try: _apply_prompt_via_builder() except: _apply_legacy_prompt_template()` 结构，直接 `return _apply_prompt_via_builder(...)`（或内联其体）。
3. 删 `_apply_legacy_prompt_template`（L884-944）与 `SYSTEM_PROMPT_TEMPLATE`（L374-425）。
4. 删 `prompts/builder.py`；`prompts/__init__.py` 移除 `SystemPromptBuilder` import/`__all__`。

---

## Phase 3 — lead_agent 模块拆分（base + chat + computer + config）

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | `lead_agent/` 拆为 `base.py`（共享 `create_agent` 装配 + `_build_middlewares` + 模型/工具解析 + bootstrap 分支）、`chat.py`/`computer.py`（薄入口）、`config.py`（typed `LeadProfile` 取代 `VARIANT_DEFAULTS`）、`prompt.py`（保留薄逻辑）；`__init__.py` 仍导出两个 `make_*`。 |
| **Verification surface** | `langgraph.json` 两图仍可构建（import 探针 `from deerflow.agents import make_chat_lead_agent, make_computer_lead_agent`）；`test_lead_agent_model_resolution.py`/`test_lead_agent_skills.py`/`test_lead_agent_prompt.py` 绿（更新 import 路径）；快照一致。 |
| **Constraints** | 图 id 与对外 `make_*` 签名不变；中间件顺序经 `build_ordered_middleware_chain` 不变；bootstrap 与 custom-agent（`update_agent`/`setup_agent`）路径不回归。 |
| **Boundaries** | `agents/lead_agent/`（新增 base/chat/computer/config，瘦身 agent.py 或并入 base 后删除）、`agents/lead_agent/__init__.py`、`agents/__init__.py`（import 路径）。不碰 `middleware_builder.py`、不碰 config 层。 |
| **Iteration policy** | 先抽 `config.py`（`LeadProfile` dataclass + `CHAT_PROFILE`/`COMPUTER_PROFILE`）并让 `agent.py` 用之、跑测试 → 再把 `_build_middlewares` + 私有中间件工厂搬 `base.py` → 再把主构图搬 `base.py:build_lead_agent(profile, config)` → `chat.py`/`computer.py` 调它 → 删空壳 `agent.py`（或重命名）。每步跑 `test_lead_agent_*` + 快照。 |
| **Blocked stop condition** | 若 `agents/__init__.py` 导入期 `prime_enabled_skills_cache()` 副作用与新模块拆分产生循环导入，记录导入链后停止（候选解：把副作用挪到显式 init 调用）。 |

### 实现方法

1. `config.py`：
   ```python
   @dataclass(frozen=True)
   class LeadProfile:
       variant: str            # "chat" | "computer"
       agent_key: str          # "chat_lead" | "computer_lead"
       is_plan_mode: bool
       subagent_enabled: bool
       max_concurrent_subagents: int
       tool_groups: list[str] | None
       sandbox_provider_variant: str
   CHAT_PROFILE = LeadProfile("chat", "chat_lead", True, True, 3, CHAT_TOOL_GROUPS, "chat")
   COMPUTER_PROFILE = LeadProfile("computer", "computer_lead", True, True, 5, None, "computer")
   ```
2. `base.py`：迁入 `_get_runtime_config`、`_build_middlewares` + 全部 `_create_*_middleware`、`_resolve_effective_tool_groups`、bootstrap+主构图，暴露 `build_lead_agent(profile: LeadProfile, config: RunnableConfig)`。
3. `chat.py`/`computer.py`：`def make_chat_lead_agent(config): return build_lead_agent(CHAT_PROFILE, config)`。
4. `__init__.py`：`from .chat import make_chat_lead_agent` / `from .computer import make_computer_lead_agent`。

---

## Phase 4 — suggestion_agent / title_agent 模块化

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | 新建 `agents/suggestion_agent/`（prompt 模板化 + `generate_suggestions(...)` 纯函数）与 `agents/title_agent/`（prompt + `generate_title(...)` + 解析/回退）；`routers/suggestions.py` 与 `TitleMiddleware` 变薄壳调用之。 |
| **Verification surface** | `test_suggestions_router.py` 绿（`run_name=="suggest_agent"`，helper 仍可达）；`test_title_*` 绿（`run_name=="title_agent"`）；harness 仍不 import app（grep 为空）。 |
| **Constraints** | harness↔app 方向不变（app→deerflow）；`run_name` 不变；suggestion 的纯函数（`_strip_markdown_code_fence` 等）测试可达 → router 从新模块 re-export；title 的 state 判定（`_should_generate_title`）留在 middleware。 |
| **Boundaries** | 新增 `agents/suggestion_agent/`、`agents/title_agent/`、对应 `templates/agents/{suggestion,title}.j2`；改 `app/gateway/routers/suggestions.py`、`agents/middlewares/title_middleware.py`；按需更新 `tests/`。不碰 `config/title_config.py`（保留）。 |
| **Iteration policy** | 先 suggestion：建模块（搬纯函数 + prompt）→ router re-export + 调用 → 跑 router 测试。再 title：建模块（搬 prompt 构造 + `_parse_title`/`_fallback_title` + 模型调用）→ middleware 调用 → 跑 title 测试。 |
| **Blocked stop condition** | 若 `test_suggestions_router.py` 直接调的 helper 在搬模块后测试无法 import，且 re-export 仍失败，记录失败 import 后停止（候选解：测试改为 import 新模块）。 |

### 实现方法

1. `agents/suggestion_agent/agent.py`：`async def generate_suggestions(messages, n, model_name=None) -> list[str]`，内部用 `build_prompt("suggestion", ...)` 或渲染 `templates/agents/suggestion.j2`，`create_chat_model(thinking_enabled=False)` + `run_name="suggest_agent"`，搬入 `_strip_markdown_code_fence`/`_parse_json_string_list`/`_extract_response_text`/`_format_conversation`。
2. `routers/suggestions.py`：保留 FastAPI 端点 + `require_thread_owner` + 请求/响应模型；`from deerflow.agents.suggestion_agent import generate_suggestions, _strip_markdown_code_fence, ...`（re-export 供旧测试）。
3. `agents/title_agent/agent.py`：`async def generate_title(user_msg, assistant_msg, config) -> str` + `parse_title`/`fallback_title`；prompt 来自 `templates/agents/title.j2`（或保留 `title_config.prompt_template`，正文模板化为可选）。
4. `title_middleware.py`：`_agenerate_title_result` 改为调用 `title_agent.generate_title(...)`；保留 `_should_generate_title`/钩子。

---

## Phase 5 — load 函数收敛与收尾

### 六要素

| 要素 | 内容 |
| --- | --- |
| **Outcome** | 合并重复 `_call_with_optional_app_config` 为单份共享 helper；enabled-skills 缓存收拢进 `agents/lead_agent/skills_cache.py`，`prompt.py` 仅留薄装配（目标 < 300 行）；`agents/__init__.py` 副作用与导出梳理清楚。 |
| **Verification surface** | `grep "def _call_with_optional_app_config"` 仅一处；`prompt.py` 行数 < 300（基线 944）；`test_lead_agent_prompt.py` 引用的缓存符号经 `skills_cache` 或兼容 re-export 仍可达且绿；全量 `make test` 相关子集 + `make lint` 绿；快照一致。 |
| **Constraints** | 不改 config 层 `load_*_from_dict`（超范围）；缓存线程语义不变（懒加载 + 后台刷新 + 失效）；`test_lead_agent_prompt.py` 的 monkeypatch 目标符号需保持可访问（同名 re-export）。 |
| **Boundaries** | 新增 `agents/lead_agent/skills_cache.py`；改 `agents/lead_agent/prompt.py`、`agents/lead_agent/base.py`（共用 helper）；新增/改 `agents/_shared.py` 或复用既有工具放 `_call_with_optional_app_config`；`agents/__init__.py`。 |
| **Iteration policy** | 先抽 `skills_cache.py`（搬缓存机制 + 模块级状态）→ `prompt.py` 从中 import 并 re-export 旧符号（保测试）→ 跑测试 → 合并 `_call_with_optional_app_config`（移到 base 或 _shared，两处改 import）→ 跑测试 → 行数核对与收尾。 |
| **Blocked stop condition** | 若搬缓存模块导致 `test_lead_agent_prompt.py` 的 `prompt_module._enabled_skills_lock` 等 monkeypatch 失效，且 re-export 无法满足（测试改的是模块属性绑定），记录失败断言后停止请求决策（候选解：测试改 patch 新模块）。 |

### 实现方法

1. `skills_cache.py`：搬 `_enabled_skills_lock`/`_enabled_skills_cache`/`_enabled_skills_refresh_*` 状态 + `_load_enabled_skills_sync`/`_ensure_/_invalidate_/prime_/warm_`/`_get_enabled_skills`/`get_cached_enabled_skills`/`get_enabled_skills_for_config`/`_refresh_enabled_skills_cache`。对外暴露 `prime_enabled_skills_cache`/`get_cached_enabled_skills`/`invalidate`/`get_enabled_skills_for_config`。
2. `prompt.py` 顶部：`from deerflow.agents.lead_agent.skills_cache import (...)` 并保留同名绑定（供 `test_lead_agent_prompt.py` monkeypatch）。
3. `_call_with_optional_app_config`：放 `agents/_shared.py`（或 `base.py`），`prompt.py` 与 `base.py` 均 import 之，删两处重复定义。
4. 行数核对：`wc -l prompt.py agent? base.py`，记录收敛结果到本文件「收敛矩阵」。

---

## 验证总览（端到端）

- **构图探针**：`python -c "from deerflow.agents import make_chat_lead_agent, make_computer_lead_agent, create_deerflow_agent"` 无报错。
- **快照回归**：`pytest tests/test_prompt_snapshot.py`（P0 基线）每个 Phase 末逐字节比对。
- **契约测试**：`pytest tests/test_lead_agent_prompt.py tests/test_lead_agent_skills.py tests/test_lead_agent_model_resolution.py tests/test_prompt_builder.py tests/test_suggestions_router.py tests/test_title_generation.py tests/test_title_middleware_core_logic.py`。
- **静态检查**：`make lint`（ruff）。
- **残留扫描**：`grep -rn "VARIANT_DEFAULTS|SYSTEM_PROMPT_TEMPLATE|_apply_legacy_prompt_template|SystemPromptBuilder" packages/ app/`（应仅命中改写后的测试或为空）；`grep -rn "^from app" packages/harness/deerflow`（应为空）。
- **行数收敛**：`prompt.py` 944 → <300，`agent.py` 695 → 拆分到 base/chat/computer/config。

---

## 风险与回滚

- **最大风险**：Phase 1 模板化语义漂移 → 由 P0 黄金快照逐字节防护，差异必须人工 accept。
- **双重 jinja2 渲染**：partial 内运行时占位符必须 `{% raw %}` 包裹，否则 build-time 被提前消费（已在 P1 约束）。
- **缓存 monkeypatch**：P5 搬 skills 缓存须 re-export 同名符号，否则 `test_lead_agent_prompt.py` 失效（已列 stop condition）。
- **回滚粒度**：每 Phase 独立提交，任一 Phase 失败可单独回退而不影响前序。

---

## 附录 · 收敛矩阵（执行时填写）

| 指标 | 重构前 | 重构后 | 备注 |
| --- | --- | --- | --- |
| `lead_agent/prompt.py` 行数 | 944 | 198 | 目标 < 300 |
| `lead_agent/agent.py` 行数 | 695 | 62 | 兼容 facade；实现 → base/chat/computer/config |
| prompt 生成路径数 | 3（builder/factory/legacy） | 1（build_prompt） | 删除 `SystemPromptBuilder` 与 legacy fallback |
| `_call_with_optional_app_config` 定义数 | 2 | 1 | `agents/_shared.py` |
| inline prompt 正文 section | ~25 | 0 | 全部 → `.j2` |
| 独立 agent 模块 | 1（lead） | 4（chat/computer/suggestion/title） | suggestion/title 已在 harness |
