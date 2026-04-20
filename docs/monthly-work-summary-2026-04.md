# 近期工作纪要（基于 Git 提交）

> 生成说明：依据仓库 `git log --since="1 month ago"` 归纳，统计口径为「最近约一个月」的提交（截至 2026-04-20 附近），**包含合并进主线的上游与社区提交**，不等同于单人工作量。

## 统计概览

| 项目 | 数值 |
|------|------|
| 提交总数（约一月） | ~318 |
| 主要贡献者（按提交数） | yoko19191、Admire、SHIYAO ZHANG 等（多人协作） |

## 一、多租户与用户级隔离（主线）

围绕 **用户资源前缀** 与 **线程/数据归属** 做了一轮完整闭环，用户故事覆盖约 **US-001～US-020**（PRD/进度日志中有对应记录）：

- **认证上下文**：Authenticated user context、canonical user resource prefix、thread ownership 服务。
- **Gateway / API**：线程 CRUD、state、runs 等路由的 **owner 校验**；`bindUser`、`listByUser`、DELETE 时 mapping 清理等。
- **路径与中间件**：线程目录、上传、artifact、虚拟路径解析、sandbox / thread-data 中间件传入 `user_id`；memory API、memory middleware、skill CRUD、agents / user profile 等 **严格按用户隔离**。
- **前端**：`useThreads` 走 Gateway `listByUser`、创建线程时注册归属、侧边栏展示用户信息与登出、线程视图与缓存按用户隔离；主 LangGraph 流量走 **已认证的 Gateway 路径**。
- **收尾**：修复剩余资源隔离缺口（US-020），并标记多段用户故事完成。

## 二、认证与账号体验

- **Phase 0**：JWT 认证模块与前端登录/注册；RFC 实现文档中 Phase 0 标记完成。
- **个性化**：注册用户名/昵称、个性化页面、侧边栏底部与智能体入口调整；品牌与登录页等 rebranding 相关提交。

## 三、上游同步与架构合并

- **2026-04-11**：合并 `upstream/main`（约 103 个提交），并补充 merge 记录文档；处理合并引入的重复路由等问题。
- **AntFlow 架构**：合并权限、Hook、压缩、插件、Prompt、子代理等模块。
- **Ralph Loop**：为项目配置 Ralph Loop（`docs/RALPH_LOOP.md` 等已有相关说明时可交叉查阅）。
- **基础设施命名**：容器/网络前缀由 `deer-flow` 调整为 `scientific-tumbleweed`。

## 四、Gateway、LangGraph 与客户端

- Gateway 侧 LangGraph 兼容、run 配置、`recursion_limit` 文档、流式与 DeerFlowClient 行为修复等。
- 客户端增加 `list_threads` / `get_thread`、线程查询能力；取消时 **checkpoint 全量回滚** 等。

## 五、沙箱、Docker 与运维

- 沙箱：审计中间件、bash 命令审计加强、容器泄漏与锁内存泄漏修复、路径/线程 workspace 锚定、工具输出截断等。
- Docker / nginx：无 IPv6 环境 nginx 启动、macOS dev 缓存挂载、上游 DNS/容器重启 **502**、gateway 环境变量与 langgraph 启动参数等修复。
- 可选 PVC（provisioner）、多阶段构建减小镜像体积等。

## 六、前端与产品体验

- Chat 布局（建议问题与输入区间距）、滚动到底按钮、免责声明、命令面板与快捷键、Markdown/HTML 预览与 hydration 类问题修复。
- 上传与文档：PDF 转换、大纲注入、企业微信/微信等渠道与飞书收文件等集成类提交。

## 七、技能、模型与开发者体验

- 新技能与评测：如 systematic-literature-review、smoke-test、学术/代码文档/newsletter 等技能。
- 模型侧：Ollama thinking、vLLM、配置项（如 `when_thinking_disabled`）等。
- DX：Setup Wizard、doctor 命令、配置文件模板中文化注释与默认模型/沙箱说明等。

## 八、其他

- 社区工具：Exa、DuckDuckGo 等搜索能力；博客结构、文档站、行为准则（Contributor Covenant）等杂项合并。

---

*若需按「仅本人提交」或「某条分支」重算，可改用：`git log --author="你的名字" --since="1 month ago"` 或限定分支后再归纳。*
