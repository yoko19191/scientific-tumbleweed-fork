# 合并记录: AntFlow 架构改造模块

## 基本信息

| 项目 | 内容 |
|---|---|
| 日期 | 2026-04-06 |
| 合并来源 | `git@github.com:fang503/antflow.git` (antflow/main) |
| 合并目标 | `custom/main` (scientific-tumbleweed-fork) |
| 合并方式 | 手动选择性应用（两分支无公共祖先，无法 git merge） |
| 涉及 commit 数 | 5 个 |

## 合并的 Commit 范围

| Commit | 日期 | 说明 |
|---|---|---|
| `2eefbc02` | 2026-04-02 | init: fork from deer-flow with Claude Code architecture renovation |
| `7e0ed83e` | 2026-04-02 | docs: rewrite README for AntFlow |
| `e7eac778` | 2026-04-02 | fix: resolve all ruff lint errors in renovation modules |
| `dea812f4` | 2026-04-02 | style: apply ruff format to all renovation modules |
| `78f8f39b` | 2026-04-02 | docs: add enhancement summary table to README |

## 新增模块清单

以下模块全部位于 `backend/packages/harness/deerflow/` 下：

### 1. 权限系统 (`permissions/`) — 5 个文件
5 级权限模型 (READ_ONLY → WORKSPACE_WRITE → DANGER_FULL_ACCESS → PROMPT → ALLOW)，每次工具调用前经过策略引擎检查。

### 2. Hook 治理层 (`hooks/`) — 6 个文件
借鉴 Claude Code 的 PreToolUse/PostToolUse 协议，支持外部 shell 脚本和 Python callable 两种 hook 形式。

### 3. 上下文压缩引擎 (`context/`) — 4 个文件
零 LLM 调用成本的确定性对话压缩，Python 重写 Claude Code 的 compact.rs。

### 4. 插件系统 (`plugins/`) — 5 个文件
通过 plugin.json 清单文件声明式注册工具、Hook 和权限。

### 5. 模块化 Prompt 组装 (`prompts/`) — 3 个文件
SystemPromptBuilder 运行时组装，支持静态/动态 cache boundary，~88% 缓存命中率。

### 6. 专用子代理 (`subagents/builtins/`) — 3 个文件
- `explore_agent.py` — 只读代码探索
- `plan_agent.py` — 策略规划
- `verification_agent.py` — 对抗性验证

### 7. 工具执行管道 (`tools/execution.py`) — 1 个文件
5 阶段流水线: Permission Check → Pre-Hook → Execute → Post-Hook → Merge Feedback

### 8. 中间件构建器 (`agents/middleware_builder.py`) — 1 个文件
统一的中间件链构建器，单一来源管理中间件顺序。

### 9. 新配置文件 — 3 个文件
- `config/hooks_config.py`
- `config/permissions_config.py`
- `config/plugins_config.py`

### 10. 新测试文件 — 6 个文件
覆盖权限、Hook、上下文压缩、插件、Prompt 构建器、工具管道。

### 11. 新文档 — 2 个文件
- `docs/RENOVATION_DESIGN.md` — 改造设计文档
- `docs/RENOVATION_SUMMARY.md` — 改造总结

## 修改的已有文件

| 文件 | 改动说明 |
|---|---|
| `config/app_config.py` | 添加 permissions/hooks/plugins 配置加载 |
| `agents/features.py` | 添加 permissions/hooks/compaction 特性标志 |
| `agents/factory.py` | 插入治理中间件槽位 + 3 个辅助函数 |
| `agents/lead_agent/agent.py` | 添加治理中间件工厂 + 集成到中间件链 |
| `agents/lead_agent/prompt.py` | 添加 SystemPromptBuilder 路径 + legacy fallback |
| `subagents/builtins/__init__.py` | 注册 explore/plan/verification 子代理 |
| `tools/tools.py` | 添加插件工具加载 |
| `app/gateway/services.py` | 简化 build_run_config 逻辑 |
| `app/channels/manager.py` | 移除 KNOWN_CHANNEL_COMMANDS 依赖 |
| `app/channels/feishu.py` | 简化命令检测逻辑 |
| `skills/parser.py` | 简化 YAML front matter 解析 |
| `runtime/runs/worker.py` | 移除 context key 的 thread_id 注入 |
| `config/agents_config.py` | 移除 per-agent skills 字段 |
| `config.example.yaml` | 添加 permissions/hooks/compaction/plugins 配置段 |
| `backend/CLAUDE.md` | 更新项目结构文档 |

## 删除的文件

| 文件 | 原因 |
|---|---|
| `app/channels/commands.py` | 引用已从 manager.py 和 feishu.py 中移除 |

## 保留的 custom/main 功能（未被 antflow 覆盖）

- 前端品牌定制（科学风滚草 / 良渚实验室）
- AI 免责声明 + 滚动到底部按钮
- Langfuse 多 provider 追踪
- LLMErrorHandlingMiddleware（LLM 重试/退避）
- 工具输出截断功能（bash_output_max_chars / read_file_output_max_chars）
- 容器前缀 `scientific-tumbleweed-sandbox`
- 自定义登录页面和 i18n 翻译

## 跳过的 antflow 改动

- 所有前端文件（品牌冲突）
- README.md / README_zh.md（品牌冲突）
- tracing_config.py 简化（保留 Langfuse）
- models/factory.py Langfuse 回调移除
- tracing/ 目录删除
- pyproject.toml langfuse 依赖移除
- llm_error_handling_middleware.py 删除
- sandbox/tools.py 截断逻辑移除
- sandbox_config.py 截断字段移除
- 容器前缀回退到 deer-flow-sandbox
- Makefile / scripts / docker 改动
- tmp/ 目录下的临时文件
