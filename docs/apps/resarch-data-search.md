# 学术数据搜索 App 实施规格

## App 功能与界面形态

`学术数据搜索` 是 `/workspace/apps` 下的一个内嵌科研工具 App。它把论文、专利、机构、期刊这些学术数据检索能力收束到一个工作台里，用户从 Apps 启动器打开后，不需要理解底层数据服务、接口地址或认证方式，只看到一个直观的搜索与结果分析界面。

页面第一屏应当是工作型界面，而不是介绍页：

- 左侧仍保留 workspace 导航，`Apps` 处于当前状态。
- 主内容顶部显示标题 `学术数据搜索`、一句短说明、数据服务状态、最近一次查询耗时或结果数。
- 中间是四个固定 Tabs：`论文检索`、`论文推荐`、`专利检索`、`机构/期刊`。
- 每个 Tab 使用相同的信息结构：左侧为检索条件，右侧为结果列表，最右侧或抽屉为当前选中记录详情。
- 论文和专利结果支持从列表进入详情；机构/期刊 Tab 内用分段控制切换 `机构` 与 `期刊`。
- 页面文案必须中性、面向用户任务，例如“搜索论文”“查看详情”“加入文献库”，不能暴露上游服务品牌、接口路径、端口、Token 或任何供应商实现细节。

## 全局要求

- App 只注册为一个 `/workspace/apps` App，名称为 `学术数据搜索`，不得拆成多个 Apps。
- App 内部必须包含且只在主工作区层面展示四个 Tabs：`论文检索`、`论文推荐`、`专利检索`、`机构/期刊`。
- 前端 UI、前端 i18n、前端组件、前端类型和前端网络层不得出现 `AMiner`，也不得出现任何上游 API host、path、端口、认证 header、Token 字段名或供应商路由片段。
- 前端只允许调用本项目 Gateway 暴露的内部、用户鉴权后的 App API；所有上游请求、凭证、错误码归一化和字段映射都必须在后端完成。
- App 必须继承 workspace 鉴权边界；直接访问 App 路由或内部 API 时，未登录用户必须被拦截。
- 页面设计要直观、密度适中、可扫描。不要做营销 Hero，不要使用装饰性大卡片堆叠，不要把表单、结果和详情拆散到多个无关页面。
- 所有新增实现必须遵守 harness/app 依赖方向：`app.*` 可以 import `deerflow.*`，`deerflow.*` 不得 import `app.*`。

## Phase 0：范围确认与基线锁定

- **Outcome**：实现范围、现有 Apps 注册机制、鉴权边界、前后端目录边界全部明确；目标文件、目标路由、目标 API 命名和不可暴露信息清单已记录；开始编码前知道当前 worktree 是否存在无关改动。
- **Verification surface**：`git status --short` 输出已查看；`sed -n '1,160p' backend/app/gateway/routers/apps.py` 确认 `/api/apps` 有 `@require_auth`；`sed -n '1,120p' frontend/src/core/apps/types.ts` 确认前端通过注册 metadata 启动 App；本文件记录的全局要求覆盖“单 App + 四 Tabs + 前端不暴露上游细节”。
- **Constraints**：不得在此 Phase 写业务代码；不得因为目标文件名里 `resarch` 拼写不标准而自行改路径；不得重命名既有 `/workspace/apps` 入口；不得把上游服务名写入前端。
- **Boundaries**：只读查看 `backend/app/gateway/routers/apps.py`、`backend/packages/harness/deerflow/apps/*`、`frontend/src/core/apps/*`、`frontend/src/components/workspace/apps/*`、`frontend/src/app/workspace/*`、`git status`；允许编辑 `docs/apps/resarch-data-search.md`。
- **Iteration policy**：若现有 Apps 机制与本文预期不一致，先更新本文边界再实现；若发现已有未提交 App 改动，先判断是否相关，相关则沿用，不相关则隔离。
- **Blocked stop condition**：如果无法确认 Apps 注册或 workspace 鉴权机制，停止并报告已查看文件、缺失证据、需要用户确认的问题；不得凭猜测继续定义路由或鉴权策略。

## Phase 1：注册一个 App 与工作台路由

- **Outcome**：`/api/apps` 返回一个可用 App metadata：`id=research-data-search`、`title=学术数据搜索`、`category=科研工具`、`launch.href=/workspace/apps/research-data-search`；前端 Apps 页面点击该卡片进入工作台路由；不新增多个学术数据类 App 卡片。
- **Verification surface**：新增或更新后端 Apps 注册测试，断言返回列表中存在且只存在一个 `research-data-search` App；`GET /api/apps` 在登录态返回该 App；未登录态仍被拦截；前端 `pnpm check` 不出现路由或类型错误。
- **Constraints**：不得把 App metadata 写死在前端卡片数组；不得在 `deerflow.apps` 中 import `app.*`；不得让 App 卡片标题或描述出现上游品牌；不得改变已有 Apps 页面筛选、搜索、空状态语义。
- **Boundaries**：允许新增 `backend/packages/harness/deerflow/apps/research_data_search.py` 或等价注册模块；允许改 `backend/packages/harness/deerflow/apps/__init__.py` 的导入/导出；允许新增 `frontend/src/app/workspace/apps/research-data-search/page.tsx`；必要时新增 `frontend/src/components/workspace/apps/research-data-search/*`。
- **Iteration policy**：先让后端 registry 能稳定返回 metadata，再接前端路由；若注册模块导入时机导致列表为空，优先检查 Gateway 启动导入链，而不是在前端补假数据。
- **Blocked stop condition**：如果现有 registry 没有可靠的模块加载点，停止并报告可选方案：Gateway lifespan 显式导入、apps package side-effect import、或新增注册清单；等待确认后再继续。

## Phase 2：后端数据服务代理与字段归一化

- **Outcome**：后端提供统一的“学术数据搜索”服务层，封装论文搜索、论文推荐、论文详情、专利搜索、专利详情、机构搜索、期刊搜索；上游凭证只从后端配置读取；返回给前端的是项目自有 DTO，不透出上游字段噪声、错误码、host、path 或 Token 语义。
- **Verification surface**：后端单元测试覆盖每个能力的请求映射、响应归一化、上游错误归一化、缺凭证错误；测试使用 mock client 或 monkeypatch，不依赖真实网络；`rg -n "Authorization|open_platform|datacenter|paper/search|paper/rec|patent/search|patent/info|organization/search|venue/search" frontend/src` 无命中。
- **Constraints**：不得把上游 token、host、path、端口、API key 名称放入前端；不得把上游原始 JSON 直接透传给前端；不得在 harness 层依赖 FastAPI Request 或 `app.*`；不得让缺凭证时页面崩溃为 500。
- **Boundaries**：允许新增后端服务模块，例如 `backend/app/gateway/services/academic_data_search.py`、`backend/app/gateway/schemas/academic_data_search.py`、`backend/app/gateway/routers/academic_data_search.py`；允许在 `config.yaml` / env 读取后端私有配置；允许新增 `backend/tests/test_academic_data_search*.py`。
- **Iteration policy**：按能力逐个落地：先论文搜索 + 论文详情打通列表到详情，再论文推荐，再专利搜索 + 专利详情，最后机构/期刊；每落一个能力先写 mock 测试并固定 DTO，再接 UI。
- **Blocked stop condition**：如果没有上游凭证或网络不可用，不阻塞 mock 测试与 UI 实现；若字段含义无法从文档确认，停止并列出字段、样例、当前假设和需要用户确认的展示口径。

## Phase 3：Gateway API 与鉴权边界

- **Outcome**：Gateway 暴露一组内部 App API，供前端工作台调用；所有路由都要求登录；请求参数有 Pydantic 校验；响应错误被归一为用户可读、前端可处理的错误类型；接口路径命名使用项目内部语义，不暴露上游供应商路由。
- **Verification surface**：`PYTHONPATH=. uv run pytest tests/test_academic_data_search_router.py -q` 通过；未登录请求返回认证错误；非法参数返回 422 或统一业务错误；mock 上游超时、限流、缺凭证时返回稳定错误；OpenAPI 中内部路由 summary 不包含上游品牌或上游 path。
- **Constraints**：不得在前端拼接任意上游查询 URL；不得让 Gateway 直接返回上游错误码给 UI；不得绕过 `@require_auth`；不得让 App API 接受任意 URL 或任意 method 代理请求。
- **Boundaries**：允许新增或修改 `backend/app/gateway/routers/__init__.py`、`backend/app/gateway/app.py` 的 router 注册；允许新增 router/service/schema/test 文件；不允许改动线程、模型、MCP、skills、uploads 等无关 API。
- **Iteration policy**：每新增一个 endpoint，先写鉴权失败、参数失败、成功 mock 三类测试；若 router 注册引入循环 import，先拆 schema/service 层，而不是把逻辑塞进 router。
- **Blocked stop condition**：如果现有鉴权装饰器无法用于新 router，停止并报告失败堆栈、现有 `/api/apps` 的工作方式、候选替代方案；不得临时移除鉴权。

## Phase 4：前端工作台 UI 与四个 Tabs

- **Outcome**：`/workspace/apps/research-data-search` 呈现完整工作台：标题区、状态区、四个 Tabs、每个 Tab 的查询表单、结果列表、详情区、加载态、空状态、错误态；用户不需要理解任何 API 细节即可完成查询。
- **Verification surface**：`cd frontend && pnpm check` 通过；浏览器截图覆盖 `1440x900`、`1024x768`、`390x844`；截图中四个 Tabs 文案准确、无文本重叠、无横向滚动；`rg -n "AMiner|datacenter|open_platform|Authorization|Bearer|paper/search|paper/rec|patent/search|patent/info|organization/search|venue/search" frontend/src` 无命中。
- **Constraints**：不得在页面上显示上游品牌、接口地址、端口、Token、原始错误码；不得做 landing page 或大 Hero；不得把四个 Tabs 做成四张互相跳转的 App 卡片；不得把表格列做得过密导致移动端不可读。
- **Boundaries**：允许新增 `frontend/src/components/workspace/apps/research-data-search/*`、`frontend/src/core/apps/research-data-search/*`、必要的 i18n key；允许使用现有 UI 组件、lucide 图标、React Query/fetch wrapper；不新增重型表格库或状态管理库，除非现有代码已有明确依赖。
- **Iteration policy**：先实现静态布局和 Tab 状态，再接内部 API client，再补加载/错误/空状态，最后做响应式；每次 UI 调整后优先检查文字溢出和 Tab 可访问性。
- **Blocked stop condition**：如果现有 UI 组件无法承载结果表格和详情抽屉，停止并报告最小可用替代：简化列表 + 详情面板；不得临时引入大型 UI 依赖绕开设计问题。

## Phase 5：四个业务流的交互细节

- **Outcome**：四个 Tabs 都能完成各自核心任务：
  - `论文检索`：按标题/关键词、页码、条数检索论文；展示标题、作者、期刊/会议、年份、引用档位、DOI；点击结果加载论文详情。
  - `论文推荐`：按学者、机构、主题、年份范围、语言偏好推荐论文；展示推荐论文的标题、作者、年份、摘要、PDF/默认链接状态。
  - `专利检索`：按专利标题或关键词、页码、条数检索专利；展示标题、公开年份、申请年份、第一发明人；点击结果加载专利详情。
  - `机构/期刊`：Tab 内使用分段控制选择机构或期刊；机构展示标准名、别名、总数；期刊展示英文名、中文名、类型、别名。
- **Verification surface**：每个 Tab 至少有一条成功 mock fixture、一条空结果 fixture、一条错误 fixture；前端组件测试或手测记录覆盖字段展示；后端 DTO 测试确认缺失字段不会导致前端崩溃；截图能看出四个业务流入口和主要字段。
- **Constraints**：不得让详情查询依赖用户手动复制 ID；不得把内部 ID 作为主要展示内容，除非放在可折叠技术信息里；不得在同一 Tab 内混入其它 Tab 的表单字段；不得默认发起无条件大查询。
- **Boundaries**：允许新增 mock fixtures、前端 hooks、DTO 类型、表单状态 helper；允许添加轻量 URL query 同步以便刷新保留 Tab 和关键词；不允许把查询状态写入全局 workspace settings。
- **Iteration policy**：以用户闭环优先级排序：列表可查 > 详情可看 > 筛选增强 > 导出/收藏；如果某详情接口不可用，该 Tab 仍应保留列表能力并显示“详情暂不可用”的中性状态。
- **Blocked stop condition**：如果某一个业务流无法在 mock 与真实字段之间建立可靠映射，停止并报告该业务流，不阻塞其它 Tabs；文档化降级状态和后续需要的接口样例。

## Phase 6：安全、可观测性与失败体验

- **Outcome**：所有上游失败都被转成用户可理解的状态：未配置、认证失败、限流、参数错误、服务不可用、超时、无结果；后端日志包含 trace 信息但不记录 Token；前端错误提示不包含上游 host/path/端口。
- **Verification surface**：后端测试覆盖 400/401/403/429/500/timeout mock；日志测试或代码审查确认不会打印 credential；前端手测或组件状态覆盖错误、重试、清空条件；`rg -n "api_key|token|Authorization|Bearer" frontend/src` 无敏感实现命中。
- **Constraints**：不得把上游响应体完整写入前端错误提示；不得在日志中打印请求 header；不得在浏览器 localStorage/sessionStorage 存储上游凭证；不得因上游失败影响 `/workspace/apps` 启动器加载。
- **Boundaries**：允许新增后端错误类型、日志 helper、前端错误映射；允许为 App API 加超时与重试策略；不允许改动全局 fetch 行为导致其它 workspace 页面变化。
- **Iteration policy**：先保证失败可解释，再考虑自动重试；若限流频繁，优先加后端短缓存或禁用重复提交，而不是让前端直接打更多请求。
- **Blocked stop condition**：如果无法确认某错误码语义，停止并将其归类为“服务暂不可用”，同时记录原始样例到后端测试 fixture；不得把未知错误原样透出给用户。

## Phase 7：集成验证与验收收口

- **Outcome**：App 能从 `/workspace/apps` 启动，四个 Tabs 均可用，前端没有上游品牌和 API 细节，后端鉴权和代理测试通过，生产构建通过，关键截图已留存或可复现。
- **Verification surface**：
  - `cd backend && PYTHONPATH=. uv run pytest tests/test_apps_registry.py tests/test_academic_data_search*.py -q`
  - `cd backend && PYTHONPATH=. uv run ruff check app/gateway packages/harness/deerflow/apps tests/test_academic_data_search*.py`
  - `cd frontend && pnpm check`
  - `cd frontend && BETTER_AUTH_SECRET=local-dev-secret pnpm build`
  - `rg -n "AMiner|datacenter|open_platform|Authorization|Bearer|paper/search|paper/rec|patent/search|patent/info|organization/search|venue/search" frontend/src` 必须无命中
  - 浏览器截图覆盖桌面与移动端，确认四 Tabs、搜索区、结果区、详情区无重叠
- **Constraints**：不得为了验收通过删除有意义的类型检查或测试断言；不得提交无关本 App 的本地文件；不得把 mock 数据当成真实数据展示在默认生产态；不得让生产 build 依赖真实上游凭证。
- **Boundaries**：允许修改本 App 相关前后端文件、测试文件、文档文件；允许运行 backend pytest、ruff、frontend check/build；允许用 mock fixture 或本地 dev server 验证 UI；真实上游 smoke test 只有在凭证存在时才做。
- **Iteration policy**：按失败成本从低到高收敛：先 `rg` 泄漏检查，再类型/lint，再后端 mock 测试，再前端 build，再浏览器截图；每次失败只修对应 Phase 边界内的问题，除非定位证明根因跨层。
- **Blocked stop condition**：如果阻塞来自缺少真实上游凭证、网络不可达或外部服务限流，停止并报告：已通过的 mock/静态验证、未执行的 live smoke、所需环境变量或凭证；如果阻塞来自本任务代码，必须继续修到通过或明确列出失败测试、根因和下一步决策点。

## 最终验收清单

- `/workspace/apps` 中只有一个相关 App：`学术数据搜索`。
- App 路由为 `/workspace/apps/research-data-search`，未登录不可访问。
- 主工作台包含四个 Tabs：`论文检索`、`论文推荐`、`专利检索`、`机构/期刊`。
- 论文检索、论文推荐、专利检索、机构/期刊均有加载、空结果、错误、成功状态。
- 前端源码与 UI 不出现上游品牌、上游接口地址、端口、Token、认证 header 或供应商路由片段。
- 上游请求只发生在后端，且经过登录态 Gateway API。
- 后端服务层有 mock 测试覆盖参数映射、响应归一化和错误归一化。
- `pnpm check`、生产 build、后端 pytest、ruff、泄漏 `rg` 检查均通过或有明确环境型阻塞说明。
