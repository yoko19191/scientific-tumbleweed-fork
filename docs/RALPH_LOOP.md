# Ralph Loop 使用指南

Ralph 是一个自主 AI 编码循环系统。你用自然语言描述需求，它会自动生成 PRD、拆分成小任务，然后逐个实现，直到全部完成。

## 工作流程

```
/prd → 生成需求文档 → /ralph → 生成 prd.json → 运行 ralph.sh → 自动实现所有 Story
```

---

## 第一步：生成 PRD

在 Claude Code 中输入 `/prd`，然后描述你的功能需求。

**示例：**

```
/prd 为项目添加用户通知系统，支持站内消息提醒
```

Claude 会问你几个澄清问题（带字母选项），你可以快速回答：

```
1A, 2C, 3B
```

生成的 PRD 会保存到 `tasks/prd-user-notifications.md`。

---

## 第二步：转换为 Ralph JSON 格式

在 Claude Code 中输入 `/ralph`，让它把 PRD 转换成 `prd.json`。

**示例：**

```
/ralph 把 tasks/prd-user-notifications.md 转换成 prd.json
```

生成的 `scripts/ralph/prd.json` 大概长这样：

```json
{
  "project": "scientific-tumbleweed",
  "branchName": "ralph/user-notifications",
  "description": "用户通知系统",
  "userStories": [
    {
      "id": "US-001",
      "title": "添加 notifications 数据表",
      "description": "As a developer, I need to store notifications in the database.",
      "acceptanceCriteria": [
        "创建 notifications 表，包含 id, user_id, message, read, created_at 字段",
        "生成并运行 migration",
        "Typecheck passes"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    },
    {
      "id": "US-002",
      "title": "添加通知铃铛图标到导航栏",
      "description": "As a user, I want to see unread notification count at a glance.",
      "acceptanceCriteria": [
        "导航栏右上角显示铃铛图标",
        "有未读消息时显示红色数字角标",
        "Typecheck passes",
        "Verify in browser using dev-browser skill"
      ],
      "priority": 2,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## 第三步：运行 Ralph 自动实现

```bash
./scripts/ralph/ralph.sh --tool claude
```

Ralph 会循环执行，每次迭代处理一个 Story，直到所有 `passes` 都变成 `true`。

**指定最大迭代次数（默认 10）：**

```bash
./scripts/ralph/ralph.sh --tool claude 20
```

**运行过程中你会看到：**

```
Starting Ralph - Tool: claude - Max iterations: 10

===============================================================
  Ralph Iteration 1 of 10 (claude)
===============================================================
[Claude Code 正在实现 US-001...]

Iteration 1 complete. Continuing...

===============================================================
  Ralph Iteration 2 of 10 (claude)
===============================================================
[Claude Code 正在实现 US-002...]

Ralph completed all tasks!
Completed at iteration 2 of 10
```

---

## 关键文件说明

| 文件 | 用途 |
|------|------|
| `scripts/ralph/ralph.sh` | 主循环脚本 |
| `scripts/ralph/CLAUDE.md` | 每次迭代给 Claude 的指令模板 |
| `scripts/ralph/prd.json` | 当前任务列表（Ralph 读写这个文件） |
| `scripts/ralph/progress.txt` | 迭代日志，记录每次的实现内容和经验 |
| `tasks/prd-*.md` | 你的 PRD 原始文档 |

---

## 注意事项

**Story 要足够小** — 每个 Story 必须能在一个 Claude 上下文窗口内完成。太大的任务会导致实现不完整。

好的 Story 大小：
- 添加一个数据库字段和 migration
- 在现有页面添加一个 UI 组件
- 更新一个 API 接口的逻辑

太大（需要拆分）：
- "构建整个仪表盘"
- "添加用户认证"

**Story 顺序很重要** — 数据库 → 后端逻辑 → 前端 UI，后面的 Story 不能依赖还没实现的 Story。

**每次迭代是全新的 Claude 实例** — 上下文不会跨迭代保留，只有 git 历史、`progress.txt` 和 `prd.json` 会持久化。
