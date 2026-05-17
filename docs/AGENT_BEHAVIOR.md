# Agent Behavior Analysis — 科学风滚草 (Scientific Tumbleweed)

本文档分析整个多智能体系统的 prompt 行为，涵盖 Lead Agent、5 个内置 Subagent、Memory Agent 以及它们之间的协作机制。

---

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     Lead Agent (编排者)                    │
│  SystemPromptBuilder 组装 → 12 层 Middleware 链 → LLM     │
│                                                         │
│  工具: sandbox + built-in + MCP + community + subagent   │
│  记忆: <memory> 标签注入 (top 15 facts + context)         │
│  技能: <skill_system> 渐进式加载                          │
│  灵魂: SOUL.md 自定义人格叠加                              │
└──────────┬──────────────────────────────────┬────────────┘
           │ task() 工具调用                    │ 异步队列
           ▼                                  ▼
┌──────────────────────┐          ┌──────────────────────┐
│   Subagent 系统       │          │   Memory Agent       │
│                      │          │                      │
│  general-purpose     │          │  MEMORY_UPDATE_PROMPT │
│  explore (只读)      │          │  FACT_EXTRACTION      │
│  plan (只读)         │          │  → memory.json        │
│  verification (对抗)  │          └──────────────────────┘
│  bash (命令执行)      │
└──────────────────────┘
```

**关键数字**:
- Lead Agent 并发 subagent 上限: `MAX_CONCURRENT_SUBAGENTS = 3`（由 SubagentLimitMiddleware 截断多余调用）
- Subagent 默认超时: 900s (15 min)，verification 600s，explore/plan 300s
- Memory 注入上限: 2000 tokens，top 15 facts 按 confidence 降序
- Memory 更新去抖: 30s debounce，per-thread 去重

---

## 2. Lead Agent — 编排者行为

### 2.1 Prompt 组装流程

使用 `SystemPromptBuilder`（builder 模式），分为 **静态前缀**（可缓存）和 **动态后缀**（per-session）两段，中间用 `<!-- SYSTEM_PROMPT_DYNAMIC_BOUNDARY -->` 分隔，以利用 LLM API 的 prompt caching。

**静态段（跨 turn 不变）**:

| 顺序 | Section | 核心行为 |
|------|---------|---------|
| 1 | `intro` | 身份声明：默认"科学风滚草"，由良渚实验室开发；支持自定义 agent 名称继承平台气质 |
| 2 | `platform_persona` | 人格定位：成熟、可靠、克制的科学协作同事；目标函数是"单位用户注意力下降低认知不确定性" |
| 3 | `conversation_craft` | 对话工艺：禁止机械开场、禁止夸问题/夸用户、信息密度要求（每句必须携带新信息） |
| 4 | `collaboration_mechanics` | 协作机制：上下文连续、技能路由、文件交付、工具判断、学术搜索路由、关系边界、严肃主题处理 |
| 5 | `scientific_method` | 科学方法论：证据分级（4 类来源）、引用规范、概念展开、adversarial self-check、主动打断机制、反模式清单 |
| 6 | `system_rules` | 运行时约束：权限模型、工具拒绝处理、prompt injection 防御、context 压缩提示 |
| 7 | `task_philosophy` | 任务哲学：不加功能、不过度抽象、不加注释、先读后改、最小变更原则 |
| 8 | `actions` | 风险行为规范：破坏性操作需确认、不可逆操作需确认、外部可见操作需确认 |
| 9 | `git_safety` | Git 安全协议：禁止 force push、禁止 amend 已推送 commit、禁止跳过 hooks |
| 10 | `tool_usage` | 工具使用语法：FileRead 而非 cat、FileEdit 而非 sed、并行调用独立工具 |
| 11 | `making_code_changes` | 代码变更纪律：先读后改、不生成长 hash、注释只解释非显而易见的意图 |
| 12 | `linter` | Linter 反馈循环：编辑后检查 lint 错误、立即修复自己引入的错误 |
| 13 | `tone_style` | 语气风格：温暖平静克制、自然段落而非"AI 大纲体"、不用 emoji 除非用户用、语言一致性 |

**动态段（per-session 变化）**:

| Section | 内容 |
|---------|------|
| `soul` | SOUL.md 自定义人格（如果存在） |
| `memory` | `<memory>` 标签包裹的用户记忆（context + facts） |
| `environment` | 当前日期、工作目录 |
| `session_guidance` | 可用的专业 subagent 列表 + verification 契约 |
| `skills` | `<skill_system>` 渐进式加载指令 + 可用技能列表 |
| `deferred_tools` | 延迟加载工具列表（tool_search） |
| `subagent_section` | 完整的 subagent 编排指令（见 2.2） |
| `clarification` | 漏斗式缩放澄清系统 |
| `working_directory` | 沙箱路径映射（uploads/workspace/outputs） |
| `citations` | 引用格式规范（学术论文、网络搜索、本地文件） |
| `mcp_instructions` | MCP 服务器使用说明 |
| `project_rules` | 项目级规则 |

### 2.2 Subagent 编排行为

当 `subagent_enabled=True` 时，Lead Agent 被注入一段详细的编排指令 `<subagent_system>`，核心行为：

1. **角色转变**: Lead Agent 从"执行者"变为"任务编排者"——分解、委派、综合
2. **并发硬限制**: 每个 response 最多 N 个 `task()` 调用（默认 3），超出的被系统静默丢弃
3. **批次执行**: 超过 N 个子任务时，必须分多个 turn 执行（Turn 1: batch 1 → Turn 2: batch 2 → ... → Final: 综合）
4. **决策树**:
   - 可分解为 2+ 并行子任务 → 使用 subagent
   - 单步简单操作 → 直接执行
   - 需要用户澄清 → 直接问
   - 顺序依赖 → 自己顺序执行
5. **科研工作流示例**: explore(文献调研) + explore(数据检查) + plan(实验设计) → general-purpose(实验执行) + bash(训练脚本) → verification(结果审计) → 综合报告

### 2.3 澄清系统

`<clarification_system>` 定义了漏斗式缩放策略：

1. 用最强、最具体的方式复述问题（working formulation）
2. 挑出置信度最高的证据，标注 {high | medium | low}
3. 给出 2-4 个互斥的下一步选项，各标明后果
4. 只在"不可逆成本"时停下来问用户
5. 每步说明"没做什么、为什么没做"

明确请求直接行动，不走漏斗。`ask_clarification` 工具仅在信息缺失会实质改变结果时调用。

### 2.4 科学方法论纪律

`<scientific_method>` 是整个系统最独特的行为约束：

**证据分级**（4 类来源）:
- empirical finding（实验发现）
- theoretical derivation（理论推导）
- community consensus（领域共识）
- copilot inference（模型自身推断）

**引用规范**:
- 学术论文: `[Author et al., Year - 标题片段](Semantic Scholar URL)`
- 数据集: id
- 本地文件: `file_path:line`
- 网络来源: `[标题](URL)`
- 无可点击指针的学术论断不可接受

**反模式清单**:
- 不谄媚（sycophancy）：先查证据再同意
- 不对冲语气堆砌（hedge-soup）：要么给置信标签，要么说证据不足
- 不伪严谨（pseudo-rigor）：公式必须定义符号，引用必须可追溯
- 不把工具输出直接当结论（tool-as-identity）：对工具返回的内容负责

**主动打断机制**（4 种 stop 信号）:
- `stop: evidence-conflict` — 新证据与既有结论冲突
- `stop: irreversible-branch` — 下一步是高成本不可逆动作
- `stop: scope-drift` — 轨迹偏离用户原问题
- `stop: blindspot` — 检测到会实质改变方案的未知盲点

### 2.5 学术搜索路由

`<collaboration_mechanics>` 中定义了明确的学术搜索优先级：

```
学术内容 → academic_search_papers / academic_get_paper / academic_recommend_papers
         → academic_get_bibtex / academic_search_author / academic_get_citation_network

非学术内容 → web_search（新闻、产品文档、博客、教程）
```

典型工作流: `academic_search_papers`(发现) → `academic_get_paper`(详情) → `academic_recommend_papers`(发散) → `academic_get_bibtex`(引用) → `academic_get_citation_network`(关系)

---

## 3. Subagent 行为详解

所有 subagent 共享的约束:
- 禁止调用 `task`（防止嵌套委派）
- 禁止调用 `ask_clarification`（不能向用户提问）
- 禁止调用 `present_files`（不能直接向用户展示文件）
- 模型默认 `inherit`（继承 Lead Agent 的模型）
- thinking 固定关闭（`thinking_enabled=False`）

### 3.1 general-purpose — 通用执行者

| 属性 | 值 |
|------|-----|
| 工具 | 继承全部（除 task/ask_clarification/present_files） |
| max_turns | 100 |
| timeout | 900s (15 min) |

**行为特征**:
- 最强大的 subagent，可以同时探索和修改
- 适用于：文献综合、数据分析、研究执行、计算管道
- 自主完成任务，不向用户提问
- 输出格式：摘要 + 关键发现 + 文件路径 + 问题 + 引用
- 科研严谨性：记录参数/版本/种子、图表出版级质量、标注局限性

### 3.2 explore — 只读探索者

| 属性 | 值 |
|------|-----|
| 工具 | 继承全部，但禁止 bash |
| max_turns | 30 |
| timeout | 300s (5 min) |

**行为特征**:
- **严格只读**：不能创建/修改/删除/移动文件，不能用输出重定向，不能运行改变状态的命令
- 允许的 bash 命令白名单：ls, find, tree, git status/log/diff/show/branch, cat, head, tail, wc, sort, uniq, grep, rg, ag, file, stat, echo（仅打印）
- 策略：先广后深——目录结构 → Glob 找文件 → Grep 搜符号 → 读关键文件
- 学术探索：读上传论文 → academic_search_papers 找相关工作 → 交叉引用 → 标注矛盾和共识
- 输出格式：摘要 + 关键文件及角色 + 架构观察 + 直接回答 + 文件路径:行号
- 研究发现额外输出：证据强度评级、方法论比较、文献空白、Semantic Scholar 引用链接

### 3.3 plan — 只读规划者

| 属性 | 值 |
|------|-----|
| 工具 | 继承全部，但禁止 bash |
| max_turns | 20 |
| timeout | 300s (5 min) |

**行为特征**:
- **严格只读**：不创建/修改/删除文件，不运行改变状态的命令，不写代码——只规划
- 规划流程：理解需求 → 探索代码库 → 识别方案 → 评估权衡 → 输出计划
- 实验设计流程：定义问题 → 设计实验（变量/对照/样本量） → 选择方法 → 规划分析 → 预判威胁
- 输出格式（严格结构化）：
  - Summary（1-3 句）
  - Approach Analysis（多方案比较）
  - Implementation Steps（每步: What/Where/How/Why）
  - Critical Files（所有涉及文件清单）
  - Risks and Considerations
  - Estimated Complexity（trivial/small/medium/large/very large）
  - 研究计划额外：Hypothesis、Experimental Design、Analysis Plan、Threats to Validity
- 科学方法论：可复现设计（固定种子、环境锁定）、数据验证、统计假设检查、实验追踪

### 3.4 verification — 对抗验证者

| 属性 | 值 |
|------|-----|
| 工具 | 继承全部（除 task/ask_clarification/present_files） |
| max_turns | 40 |
| timeout | 600s (10 min) |

**行为特征**:
- **核心目标不是确认 OK，而是尝试打破它或证伪它**
- 必须防范的两种失败模式：
  1. Verification avoidance：只读代码不运行检查就写 PASS
  2. 80% blindness：测试通过就忽略边缘情况
- 强制检查清单（6 类）：
  1. **Build**: 编译/构建，检查 warnings
  2. **Test Suite**: 运行完整测试套件，检查新引入的失败
  3. **Linter/Type-check**: 静态分析，新 warnings 算问题
  4. **变更类型特定验证**: Frontend(渲染/console errors) / Backend(curl 端点) / CLI(stdout/stderr/exit code) / DB(up+down migration) / Refactor(公共 API 不变)
  5. **Adversarial probes**: 空输入/巨大输入/unicode/并发/错误路径/安全
  6. **研究声明验证**: 复现结果/统计方法正确性/p-hacking 检测/数据完整性/混杂因素/泛化性/数值稳定性/引用准确性
- 输出格式：每项检查必须包含 Command run + Output observed + Assessment (PASS/FAIL/WARN)
- 最终裁决：**VERDICT: PASS | FAIL | PARTIAL**，FAIL/PARTIAL 必须附 Remediation
- 硬规则：必须运行真实命令，读代码猜测不算验证

**Lead Agent 与 verification 的契约**:
> 完成非平凡实现后，SHOULD 委派给 verification agent 验证变更。

### 3.5 bash — 命令执行者

| 属性 | 值 |
|------|-----|
| 工具 | 仅 sandbox 工具: bash, ls, read_file, write_file, str_replace |
| max_turns | 60 |
| timeout | 900s (15 min) |

**行为特征**:
- 最受限的工具集，只有沙箱工具
- 适用于：一系列相关 bash 命令、git/npm/docker 操作、构建/测试/部署、数据处理管道、科学计算
- 依赖命令顺序执行，独立命令并行执行
- 科学计算特殊要求：
  - 捕获环境信息（软件版本、随机种子、硬件）
  - 保留原始命令输出，不静默四舍五入
  - 标记非确定性行为
  - 记录完整命令和参数
  - 安装包时锁定精确版本
  - 处理大数据集时报告每阶段行/列数

---

## 4. Memory Agent — 记忆管理

Memory Agent 不是一个独立的 subagent，而是通过 `MemoryMiddleware` + 异步队列 + LLM 调用实现的后台系统。

### 4.1 记忆更新流程

```
用户消息 + AI 最终回复
    │
    ▼ MemoryMiddleware 过滤
    │
    ▼ 去抖队列 (30s debounce, per-thread 去重)
    │
    ▼ 后台线程调用 LLM (MEMORY_UPDATE_PROMPT)
    │
    ▼ 原子写入 memory.json (temp file + rename)
    │
    ▼ 下次交互注入 <memory> 标签
```

### 4.2 MEMORY_UPDATE_PROMPT 行为

LLM 被要求扮演"记忆管理系统"，分析对话并更新用户画像：

**结构化反思（提取 facts 前必须执行）**:
1. 错误/重试检测：agent 是否犯错？记录根因和正确方法（category: correction, confidence ≥ 0.95）
2. 用户纠正检测：用户是否纠正了 agent？记录正确理解
3. 项目约束发现：是否发现项目特定约束？

**记忆数据结构**:

| 层级 | 字段 | 长度指导 | 更新频率 |
|------|------|---------|---------|
| User Context | workContext | 2-3 句 | 中 |
| User Context | personalContext | 1-2 句 | 低 |
| User Context | topOfMind | 3-5 句（详细段落） | 高（最频繁） |
| History | recentMonths | 4-6 句 / 1-2 段 | 中 |
| History | earlierContext | 3-5 句 / 1 段 | 低 |
| History | longTermBackground | 2-4 句 | 极低 |
| Facts | content + category + confidence | 单条 | 持续追加 |

**Fact 分类**: preference / knowledge / context / behavior / goal / correction

**Confidence 分级**:
- 0.9-1.0: 明确陈述（"I work on X"）
- 0.7-0.8: 强烈暗示
- 0.5-0.6: 推断模式（谨慎使用）

**硬规则**:
- 不记录文件上传事件（session-specific，未来不可访问）
- 保留原始语言的专有名词和技术术语
- topOfMind 保持 3-5 个并发主题，移除已完成/放弃的
- correction 类 fact 必须 confidence ≥ 0.95

### 4.3 记忆注入行为

`format_memory_for_injection()` 将 memory.json 格式化为 `<memory>` 标签注入 system prompt：

- 按 confidence 降序排列 facts
- 使用 tiktoken 精确计算 token 数
- 上限 2000 tokens，超出则截断
- correction 类 fact 附加 `(avoid: ...)` 提示
- 格式：`- [category | confidence] content`

---

## 5. Middleware 链行为

Lead Agent 的 12 层 middleware 按严格顺序执行，每层负责一个关注点：

| 顺序 | Middleware | 时机 | 行为 |
|------|-----------|------|------|
| 1 | ThreadData | before | 创建 per-thread 目录结构 |
| 2 | Uploads | before | 注入新上传文件到对话 |
| 3 | Sandbox | before | 获取沙箱，存储 sandbox_id |
| 4 | DanglingToolCall | before | 为缺少响应的 tool_call 注入占位 ToolMessage |
| 5 | Guardrail | before | 工具调用前授权检查（可选） |
| 6 | Summarization | before | 接近 token 上限时压缩上下文（可选） |
| 7 | TodoList | before | 任务追踪 write_todos 工具（plan_mode 可选） |
| 8 | Title | after | 首次完整交换后自动生成线程标题 |
| 9 | Memory | after | 将对话入队异步记忆更新 |
| 10 | ViewImage | before | 注入 base64 图像数据（vision 模型） |
| 11 | SubagentLimit | after | 截断超出并发限制的 task 调用 |
| 12 | Clarification | after | 拦截 ask_clarification，中断到 END（必须最后） |

---

## 6. 跨 Agent 协作模式

### 6.1 典型科研工作流

```
用户: "Transformer 和 LSTM 在时间序列预测上哪个更好？"

Lead Agent 分解:
  Turn 1 (3 并行 subagent):
    ├─ explore: academic_search_papers 调研论文和 benchmark
    ├─ explore: 检查上传数据集特征
    └─ plan: 设计实验（模型配置、评估指标、统计检验）

  Turn 2 (2 并行 subagent):
    ├─ general-purpose: 按计划实现并运行对比实验
    └─ bash: 执行训练脚本，收集指标

  Turn 3 (1 subagent):
    └─ verification: 审计结果（数据泄漏、统计显著性、复现关键数字）

  Final: Lead Agent 综合为结构化研究报告 + 引用
```

### 6.2 工具继承与隔离

```
Lead Agent 工具集
├─ sandbox tools (bash, ls, read_file, write_file, str_replace)
├─ built-in tools (present_files, ask_clarification, view_image)
├─ MCP tools (动态加载)
├─ community tools (tavily, jina_ai, firecrawl, image_search)
├─ academic tools (academic_search_papers, academic_get_paper, ...)
└─ subagent tool (task)

general-purpose: 全部 - {task, ask_clarification, present_files}
explore:         全部 - {task, ask_clarification, present_files, bash}
plan:            全部 - {task, ask_clarification, present_files, bash}
verification:    全部 - {task, ask_clarification, present_files}
bash:            仅 {bash, ls, read_file, write_file, str_replace}
```

### 6.3 Subagent 执行机制

- 双线程池架构：`scheduler_pool`(5 workers) + `execution_pool`(5 workers) + `isolated_loop_pool`(3 workers)
- 每个 subagent 在独立事件循环中运行，避免与父 agent 的 asyncio 冲突
- 支持协作式取消：通过 `cancel_event` 在 `astream()` 迭代边界检查
- 结果通过 `SubagentResult` 传回，包含 task_id、trace_id、status、result、ai_messages
- 后台任务 TTL: 15 分钟自动清理

---

## 7. 人格与语气系统

### 7.1 默认人格（platform_persona）

核心定位：**成熟、可靠、克制的科学协作同事**

- 不是啦啦队、不是速记员、不是搜索框
- 目标函数：单位用户注意力下，降低认知不确定性
- 温暖来自稳定判断和清楚语言，不是热情口号
- 诚实不是生硬否定，而是指出风险和更好路径
- 默认尊重用户能力，可以反驳但落在"怎样更好地完成"
- 犯错直接承认并修复，不长篇道歉

### 7.2 SOUL.md 叠加机制

每个自定义 agent 可以有 `SOUL.md` 文件，内容被包裹在 `<soul>` 标签中注入 system prompt 的动态段。这允许在保持平台气质的基础上叠加专业定位。

### 7.3 对话工艺约束

- 禁止机械开场（"当然可以""没问题""以下是"）
- 禁止夸问题/夸用户/总结需求凑开头
- 禁止"作为一个 AI""我无法体验""希望这能帮助你"
- 信息密度：每句必须携带新信息，能删掉不丢失论断的句子就删掉
- 科研任务优先体现可验证性：来源、假设、方法、实验、测试、限制、下一步

---

## 8. 配置覆盖层级

```
SubagentConfig 内置默认值
    ↓ 被覆盖
config.yaml → subagents 全局配置 (timeout, max_turns, model)
    ↓ 被覆盖
config.yaml → subagents.agents.{name} 单 agent 配置
    ↓ 被覆盖
运行时参数 (parent_model inherit, sandbox_state, thread_data)
```

---

## 9. 安全与边界

| 边界 | 机制 |
|------|------|
| Subagent 不能嵌套委派 | 禁止 `task` 工具 |
| Subagent 不能向用户提问 | 禁止 `ask_clarification` |
| Subagent 不能直接展示文件 | 禁止 `present_files` |
| explore/plan 不能修改文件 | 禁止 `bash`，prompt 中严格只读约束 |
| 并发限制 | SubagentLimitMiddleware 截断超额 task 调用 |
| 超时保护 | per-agent timeout + 协作式取消 |
| 记忆隐私 | 不记录文件上传事件，上传路径从对话中剥离 |
| Prompt injection 防御 | system_rules 中明确提示外部工具结果可能包含注入 |
| Git 安全 | 禁止 force push/amend 已推送/跳过 hooks |
| 破坏性操作 | 需要用户显式确认 |
| Guardrail | 可选的 pre-tool-call 授权中间件 |
