# Human-in-the-Loop × GenerativeUI 交互设计

> 使用 OpenUI 框架为 Agent 的人机交互环节提供结构化、可渲染的 UI 组件，替代纯文本问答。
> 开发分支：`hil-openui`

---

## 设计目标

1. **结构化交互** — Agent 需要用户输入时，生成可交互的 UI 组件而非纯文本
2. **Token 高效** — OpenUI Lang 比 JSON 节省 ~60% token，适合流式生成
3. **渐进增强** — 纯文本 fallback 始终可用，GenerativeUI 是增强层
4. **前后端解耦** — 后端输出 OpenUI Lang，前端通过 Renderer 渲染，互不侵入
5. **永远可逃逸** — 每种交互类型都包含"其他/Chat"文本输入框，用户可以跳过结构化选项直接发送自由文本

---

## 通用设计规则：Chat Escape

每种 HIL 交互的底部都必须包含一个自由文本输入区域，允许用户绕过所有结构化选项：

```
┌─────────────────────────────────────────────────────┐
│  ... (结构化交互组件) ...                             │
│                                                     │
│  ─── 或者 ───                                       │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ 输入其他想法...                               │    │
│  └─────────────────────────────────────────────┘    │
│  [ 发送 ]                                           │
└─────────────────────────────────────────────────────┘
```

**OpenUI Lang 模式**（所有类型复用）：
```
separator = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者，直接告诉我你的想法：", TextArea("chat_message", "输入其他想法...", 2))
chatBtn = Buttons([Button("发送", Action([@ToAssistant("发送")]), "secondary")])
```

当用户填写 `chat_message` 并点击发送时，Agent 收到的是自由文本，按普通对话处理。

---

## HIL 交互类型清单

### Type 1: 方案选择 (Approach Choice)

**交互描述**：Agent 分析后提供 2-4 个可选方案，用户选择一个继续执行。每个选项附带简要说明和权衡分析。

**典型场景**：用户要求"优化这个查询的性能"，Agent 识别出多种优化路径。

```
┌─────────────────────────────────────────────────────┐
│  🤔 我发现了 3 种优化方案，请选择：                    │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ ○ 方案 A：添加复合索引                        │    │
│  │   预计提升 5x，需要 ~2min 迁移                 │    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────┐    │
│  │ ○ 方案 B：查询重写为 CTE                      │    │
│  │   预计提升 3x，无需 schema 变更                │    │
│  └─────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────┐    │
│  │ ○ 方案 C：引入物化视图                        │    │
│  │   预计提升 10x，增加存储和维护成本              │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  [ 确认选择 ]                                       │
│                                                     │
│  ─── 或者 ───                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │ 输入其他想法...                               │    │
│  └─────────────────────────────────────────────┘    │
│  [ 发送 ]                                           │
└─────────────────────────────────────────────────────┘
```

**OpenUI Lang**：
```
root = Card([header, options, actions, separator, chatEscape])
header = TextContent("我发现了 3 种优化方案，请选择：", "medium")
options = RadioGroup("approach", [optA, optB, optC])
optA = RadioItem("index", "方案 A：添加复合索引 — 预计提升 5x，需要 ~2min 迁移")
optB = RadioItem("cte", "方案 B：查询重写为 CTE — 预计提升 3x，无需 schema 变更")
optC = RadioItem("matview", "方案 C：引入物化视图 — 预计提升 10x，增加存储和维护成本")
actions = Buttons([Button("确认选择", Action([@ToAssistant("确认选择")]), "primary")])
separator = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者，直接告诉我你的想法：", TextArea("chat_message", "输入其他想法...", 2))
chatBtn = Buttons([Button("发送", Action([@ToAssistant("发送")]), "secondary")])
```

**用户响应格式**：
- 结构化：`{ "approach": "index" }` + 按钮 "确认选择"
- 逃逸：`{ "chat_message": "我觉得应该先 EXPLAIN ANALYZE 看看瓶颈在哪" }` + 按钮 "发送"

---

### Type 2: 信息补全 (Missing Information Form)

**交互描述**：Agent 缺少必要信息无法继续，生成结构化表单收集缺失字段。支持多种输入类型（文本、选择、数值等）。

**典型场景**：用户要求"部署到生产环境"，但未指定版本号和目标区域。

```
┌─────────────────────────────────────────────────────┐
│  📝 需要补充以下信息才能继续部署：                      │
│                                                     │
│  版本号 *                                            │
│  ┌─────────────────────────────────────────────┐    │
│  │ v2.3.1                                      │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  目标区域 *                                          │
│  ┌─────────────────────────────────────────────┐    │
│  │ ▼ 请选择区域                                 │    │
│  │   us-east-1                                  │    │
│  │   us-west-2                                  │    │
│  │   ap-southeast-1                             │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  部署备注（可选）                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │                                              │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  [ 提交 ]                                           │
│                                                     │
│  ─── 或者 ───                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │ 输入其他想法...                               │    │
│  └─────────────────────────────────────────────┘    │
│  [ 发送 ]                                           │
└─────────────────────────────────────────────────────┘
```

**OpenUI Lang**：
```
root = Card([header, form, separator, chatEscape])
header = TextContent("需要补充以下信息才能继续部署：", "medium")
form = Form("deploy_info", btns, [versionField, regionField, noteField])
versionField = FormControl("版本号 *", Input("version", "v2.3.1", "text", {required: true}))
regionField = FormControl("目标区域 *", Select("region", [r1, r2, r3], "请选择区域", {required: true}))
r1 = SelectItem("us-east-1", "us-east-1")
r2 = SelectItem("us-west-2", "us-west-2")
r3 = SelectItem("ap-southeast-1", "ap-southeast-1")
noteField = FormControl("部署备注（可选）", TextArea("note", "输入备注...", 3))
btns = Buttons([Button("提交", Action([@ToAssistant("提交")]), "primary")])
separator = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者，直接告诉我你的想法：", TextArea("chat_message", "输入其他想法...", 2))
chatBtn = Buttons([Button("发送", Action([@ToAssistant("发送")]), "secondary")])
```

**用户响应格式**：
- 结构化：`{ "version": "v2.3.1", "region": "us-east-1", "note": "hotfix for #1234" }`
- 逃逸：`{ "chat_message": "先别部署了，我想回滚上一个版本" }`

---

### Type 3: 风险确认 / 审阅批准 (Confirmation & Approval)

**交互描述**：Agent 即将执行高风险操作或完成阶段性成果，需要用户明确确认/批准。展示操作详情、影响范围，提供批准/拒绝/修改三态选择。

**典型场景 A — 风险确认**：Agent 准备执行数据库迁移，涉及删除列操作。

```
┌─────────────────────────────────────────────────────┐
│  ⚠️  高风险操作确认                                   │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ 操作：DROP COLUMN users.legacy_email          │    │
│  │ 影响：12,847 行数据将永久删除                   │    │
│  │ 回退：需从备份恢复（最近备份 2h 前）             │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  [ 确认执行 ]  [ 取消 ]                              │
│                                                     │
│  ─── 或者 ───                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │ 输入其他想法...                               │    │
│  └─────────────────────────────────────────────┘    │
│  [ 发送 ]                                           │
└─────────────────────────────────────────────────────┘
```

**典型场景 B — 审阅批准**：Agent 完成重构计划，展示变更摘要。

```
┌─────────────────────────────────────────────────────┐
│  📋 重构计划审阅                                      │
│                                                     │
│  变更摘要：将 UserService 拆分为 3 个独立模块          │
│                                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │  M  src/services/user-service.ts  (-245行)   │    │
│  │  A  src/services/user-auth.ts     (+89行)    │    │
│  │  A  src/services/user-profile.ts  (+112行)   │    │
│  │  A  src/services/user-settings.ts (+67行)    │    │
│  │  M  src/index.ts                  (+3行)     │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  影响范围：12 个文件的 import 需要更新                  │
│  测试状态：所有现有测试通过 ✓                          │
│                                                     │
│  修改意见（可选）                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │                                              │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  [ 批准执行 ]  [ 需要修改 ]  [ 放弃 ]                 │
│                                                     │
│  ─── 或者 ───                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │ 输入其他想法...                               │    │
│  └─────────────────────────────────────────────┘    │
│  [ 发送 ]                                           │
└─────────────────────────────────────────────────────┘
```

**OpenUI Lang（风险确认）**：
```
root = Card([alert, details, actions, separator, chatEscape])
alert = Alert("高风险操作确认", "warning")
details = Stack([op, impact, rollback], "column", "s")
op = TextContent("操作：DROP COLUMN users.legacy_email")
impact = TextContent("影响：12,847 行数据将永久删除")
rollback = TextContent("回退：需从备份恢复（最近备份 2h 前）")
actions = Buttons([
  Button("确认执行", Action([@ToAssistant("确认执行")]), "destructive"),
  Button("取消", Action([@ToAssistant("取消")]), "secondary")
])
separator = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者，直接告诉我你的想法：", TextArea("chat_message", "输入其他想法...", 2))
chatBtn = Buttons([Button("发送", Action([@ToAssistant("发送")]), "secondary")])
```

**OpenUI Lang（审阅批准）**：
```
root = Card([header, summary, changes, impact, feedbackForm, actions, separator, chatEscape])
header = CardHeader("重构计划审阅")
summary = TextContent("变更摘要：将 UserService 拆分为 3 个独立模块")
changes = CodeBlock("diff", " M  src/services/user-service.ts  (-245行)\n A  src/services/user-auth.ts     (+89行)\n A  src/services/user-profile.ts  (+112行)\n A  src/services/user-settings.ts (+67行)\n M  src/index.ts                  (+3行)")
impact = TextContent("影响范围：12 个文件的 import 需要更新\n测试状态：所有现有测试通过 ✓")
feedbackForm = FormControl("修改意见（可选）", TextArea("feedback", "输入修改建议...", 2))
actions = Buttons([
  Button("批准执行", Action([@ToAssistant("批准执行")]), "primary"),
  Button("需要修改", Action([@ToAssistant("需要修改")]), "secondary"),
  Button("放弃", Action([@ToAssistant("放弃")]), "destructive")
])
separator = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者，直接告诉我你的想法：", TextArea("chat_message", "输入其他想法...", 2))
chatBtn = Buttons([Button("发送", Action([@ToAssistant("发送")]), "secondary")])
```

**用户响应格式**：
- 风险确认：按钮动作 "确认执行" | "取消"
- 审阅批准：按钮动作 + `{ "feedback": "..." }`
- 逃逸：`{ "chat_message": "能不能先只迁移 staging 环境试试？" }`

---

### Type 4: 多步引导 (Step-by-Step Wizard)

**交互描述**：复杂任务需要分步收集信息，每步展示当前进度和上下文。Agent 每次只生成当前步骤的 UI，收到回答后生成下一步。

**典型场景**：用户要求"初始化一个新的微服务项目"，需要逐步确认技术栈、配置和集成。

```
┌─────────────────────────────────────────────────────┐
│  🚀 新服务初始化向导                                  │
│                                                     │
│  Step 1 of 3                                        │
│  ████████████░░░░░░░░░░░░░░░░░░░░░░░░  33%          │
│                                                     │
│  ── 基础配置 ──                                      │
│                                                     │
│  服务名称 *                                          │
│  ┌─────────────────────────────────────────────┐    │
│  │ order-service                                │    │
│  └─────────────────────────────────────────────┘    │
│                                                     │
│  运行时                                              │
│  ○ Python (FastAPI)                                 │
│  ● Go (Gin)                                         │
│  ○ TypeScript (NestJS)                              │
│                                                     │
│  端口号                                              │
│  ┌──────┐                                           │
│  │ 8080 │                                           │
│  └──────┘                                           │
│                                                     │
│  [ 下一步 → ]                                        │
│                                                     │
│  ─── 或者 ───                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │ 输入其他想法...                               │    │
│  └─────────────────────────────────────────────┘    │
│  [ 发送 ]                                           │
└─────────────────────────────────────────────────────┘
```

**OpenUI Lang**：
```
root = Card([header, progress, stepTitle, form, separator, chatEscape])
header = CardHeader("新服务初始化向导", "Step 1 of 3")
progress = Progress(33)
stepTitle = TextContent("基础配置", "large-heavy")
form = Form("wizard_step1", btns, [nameField, runtimeField, portField])
nameField = FormControl("服务名称 *", Input("name", "order-service", "text", {required: true}))
runtimeField = FormControl("运行时", RadioGroup("runtime", [rt1, rt2, rt3]))
rt1 = RadioItem("python", "Python (FastAPI)")
rt2 = RadioItem("go", "Go (Gin)")
rt3 = RadioItem("typescript", "TypeScript (NestJS)")
portField = FormControl("端口号", Input("port", "8080", "number"))
btns = Buttons([Button("下一步 →", Action([@ToAssistant("下一步")]), "primary")])
separator = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者，直接告诉我你的想法：", TextArea("chat_message", "输入其他想法...", 2))
chatBtn = Buttons([Button("发送", Action([@ToAssistant("发送")]), "secondary")])
```

**用户响应格式**：
- 结构化：`{ "name": "order-service", "runtime": "go", "port": 8080 }`
- 逃逸：`{ "chat_message": "直接用和 user-service 一样的配置就行" }`

**多步状态管理**：
- 不依赖 checkpointer 的 interrupt/resume
- 每步是一个独立的 run：Agent 生成当前步 UI → 用户回答 → 新 run 中 Agent 生成下一步 UI
- Agent 通过 message history 中的前几步回答来维持上下文

---

### Type 5: 建议采纳 (Suggestion Acceptance)

**交互描述**：Agent 主动提出改进建议或发现潜在问题，用户可以逐条接受或拒绝。适用于代码审查建议、性能优化建议、安全修复建议等。

**典型场景**：Agent 在代码分析中发现 3 个可优化点。

```
┌─────────────────────────────────────────────────────┐
│  💡 发现以下优化建议：                                 │
│                                                     │
│  ☐ 1. N+1 查询问题                                  │
│     src/api/users.py:45                              │
│     使用 selectinload 预加载，减少 ~20 次查询          │
│                                                     │
│  ☐ 2. 未使用的索引                                   │
│     migrations/0023_*.py                             │
│     删除 idx_legacy_status，节省 ~200MB               │
│                                                     │
│  ☐ 3. 缺少错误重试                                   │
│     src/clients/payment.py:78                        │
│     添加 exponential backoff，提升成功率 ~2%          │
│                                                     │
│  [ 全部采纳 ]  [ 提交选择 ]                           │
│                                                     │
│  ─── 或者 ───                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │ 输入其他想法...                               │    │
│  └─────────────────────────────────────────────┘    │
│  [ 发送 ]                                           │
└─────────────────────────────────────────────────────┘
```

**OpenUI Lang**：
```
root = Card([header, suggestions, actions, separator, chatEscape])
header = TextContent("发现以下优化建议：", "medium")
suggestions = CheckBoxGroup("accepted", [s1, s2, s3])
s1 = CheckBoxItem("n_plus_1", "N+1 查询问题 — src/api/users.py:45 — 使用 selectinload 预加载，减少 ~20 次查询")
s2 = CheckBoxItem("unused_index", "未使用的索引 — migrations/0023 — 删除 idx_legacy_status，节省 ~200MB")
s3 = CheckBoxItem("retry", "缺少错误重试 — src/clients/payment.py:78 — 添加 backoff，提升成功率 ~2%")
actions = Buttons([
  Button("全部采纳", Action([@ToAssistant("全部采纳")]), "primary"),
  Button("提交选择", Action([@ToAssistant("提交选择")]), "secondary")
])
separator = Separator()
chatEscape = Form("chat_escape", chatBtn, [chatField])
chatField = FormControl("或者，直接告诉我你的想法：", TextArea("chat_message", "输入其他想法...", 2))
chatBtn = Buttons([Button("发送", Action([@ToAssistant("发送")]), "secondary")])
```

**用户响应格式**：
- 结构化：`{ "accepted": ["n_plus_1", "retry"] }` + 按钮 "提交选择"
- 全选：按钮 "全部采纳"（Agent 视为全部勾选）
- 逃逸：`{ "chat_message": "第一个问题能展开说说影响范围吗？" }`

---

## 交互类型对照表

| # | 类型 | 触发条件 | 复杂度 | 阻塞性 | OpenUI 核心组件 |
|---|------|----------|--------|--------|----------------|
| 1 | 方案选择 | Agent 识别多条路径 | 中 | 阻塞 | RadioGroup + Button |
| 2 | 信息补全 | 缺少必要参数 | 中 | 阻塞 | Form + Input/Select/TextArea |
| 3 | 风险确认/审阅批准 | 高风险操作或阶段成果 | 中-高 | 阻塞 | Alert/CodeBlock + Button |
| 4 | 多步引导 | 复杂初始化/配置 | 高 | 阻塞 | Progress + Form (per step) |
| 5 | 建议采纳 | Agent 主动发现问题 | 中 | 半阻塞 | CheckBoxGroup + Button |

所有类型共享：`Separator` + `Form("chat_escape", ...)` 作为逃逸出口。

---

## 前后端联调流程

```
                    Backend                              Frontend
                    ──────                              ────────
                       │                                    │
  Agent 需要用户输入    │                                    │
         │             │                                    │
         ▼             │                                    │
  调用 ask_clarification(                                   │
    type="approach_choice",                                 │
    ui_schema="root = Card([...])\n..."                     │
  )                    │                                    │
         │             │                                    │
         ▼             │                                    │
  ClarificationMiddleware 拦截                              │
  → 包装为 ToolMessage                                      │
  → Command(goto=END)                                       │
         │             │                                    │
         ▼             │                                    │
  StreamBridge 推送    ─┼──── SSE stream ────────────────▶  │
                       │                                    │
                       │                     检测到 clarification msg
                       │                     解析 ui_schema (OpenUI Lang)
                       │                     Renderer 渲染交互组件
                       │                                    │
                       │                          用户交互   │
                       │                            │       │
                       │  ◀──── thread.submit() ────┘       │
                       │   { messages: [HumanMessage(       │
                       │       content: structured_response  │
                       │   )] }                             │
         │             │                                    │
         ▼             │                                    │
  新 Run 启动          │                                    │
  Agent 拿到结构化回答  │                                    │
  继续执行             │                                    │
```

---

## 关于 Checkpointer 的结论

**不需要额外依赖 checkpointer 的 interrupt/resume 特性**。

原因：
1. 现有的 `Command(goto=END)` 模式天然将状态持久化到 checkpoint
2. 用户回答通过 `thread.submit()` 触发新 run，不需要 `Command(resume=...)`
3. 浏览器关闭后重新打开，thread 状态已经在 PostgreSQL checkpoint 中
4. 多步引导（Wizard）通过 message history 维持上下文，不需要额外状态存储
5. 这个设计比 LangGraph 的 `interrupt()` 模式更简单，且与现有架构完全兼容

---

## 需要的 OpenUI 组件子集

基于 5 种交互类型，实际需要的组件（共 ~20 个）：

**布局**：`Card`, `CardHeader`, `Stack`, `Separator`, `Progress`
**内容**：`TextContent`, `Alert`, `CodeBlock`
**表单**：`Form`, `FormControl`, `Input`, `TextArea`, `Select`, `SelectItem`, `Slider`
**选择**：`RadioGroup`, `RadioItem`, `CheckBoxGroup`, `CheckBoxItem`, `SwitchGroup`, `SwitchItem`
**动作**：`Button`, `Buttons`, `Action`, `@ToAssistant`

---

## 下一步

- [ ] 扩展 `ask_clarification` tool 的参数，增加 `ui_schema` 字段
- [ ] 前端集成 OpenUI Renderer（`@openuidev/react-ui` 或自定义子集）
- [ ] System Prompt 约束规则：告诉 LLM 何时用哪种类型、如何生成 OpenUI Lang
- [ ] 用户响应序列化协议：结构化 JSON vs chat_escape 的区分逻辑
- [ ] E2E 测试：每种交互类型的 happy path + escape path
