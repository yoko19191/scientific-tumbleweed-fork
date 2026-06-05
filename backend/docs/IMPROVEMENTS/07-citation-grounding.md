# Phase 7 - Citation Grounding and Source Evidence

## Context

当前智能体几乎不在最终回答中带引用，但排查结果显示问题不是单点故障：

- Lead agent 的真实 system prompt 已经包含 `<citations>` 规则。
- Chat agent 默认绑定 `web` 与 `academic_search` 工具组。
- `web_search` 返回 `title`、`url`、`snippet`，academic 工具返回 `paperId`、`title`、`authors`、`year`、`citationCount`、`openAccessPdfUrl` 等字段。
- 但引用仍然只是工具 JSON 里的普通文本字段，没有统一的、模型必须消费的 citation contract。
- Prompt 目前把学术引用写得更强，把普通网页事实写得较弱。
- Academic prompt 与前端工具卡片默认把 `paperId` 拼成 Semantic Scholar URL，但当前 academic 聚合器默认走 OpenAlex，`paperId` 可能是 `W...`，不能可靠拼成 Semantic Scholar 链接。
- 当前 `config.yaml` 中 `web_fetch` 是注释状态，普通网页问题只能引用搜索摘要，缺少正文级证据。

目标不是让模型“更听话”这么简单，而是让工具、prompt、前端显示共同形成可验证的引用链路。

## Change 1 - Canonical Citation Fields for Tool Outputs

### Outcome

所有会产生外部证据的工具结果都暴露统一引用字段，同时保留现有字段以免破坏调用方：

- `citationUrl`: 最终回答可直接引用的 URL。
- `citationTitle`: 人类可读的引用标题。
- `citationProvider`: `web`、`tavily`、`firecrawl`、`openalex`、`semantic_scholar`、`doi` 等来源。
- `citationType`: `web_page`、`academic_paper`、`pdf`、`image_source` 等类型。
- `evidenceSnippet`: 支持当前结果的短摘录或摘要。

完成时，模型不需要猜字段，也不需要根据 provider 手动拼 URL；任何工具结果中只要有可引用来源，就有 `citationUrl`。

### Verification surface

- Backend unit tests 覆盖 web search normalizer 和 academic paper normalizer。
- 针对 Tavily / Firecrawl / academic_search 的 fixture 测试断言 `citationUrl`、`citationTitle`、`citationProvider` 存在且不为空。
- 现有工具结果 shape 的兼容测试断言旧字段仍存在，例如 `title`、`url`、`paperId`、`openAccessPdfUrl`。
- `PYTHONPATH=. uv run pytest tests/test_semantic_scholar_tools.py tests/test_bibtex.py -q`
- 新增 citation normalizer 测试文件后，将其加入同一测试命令。

### Constraints

- 不删除或重命名现有工具返回字段。
- 不把 provider 缺失的字段伪造成看似真实的 URL。
- 不为了统一格式牺牲具体来源信息，例如 DOI、OpenAlex、Semantic Scholar ID 仍应保留。
- 不让 harness 层导入 `app.*`。

### Boundaries

允许修改：

- `backend/packages/harness/deerflow/community/tavily/tools.py`
- `backend/packages/harness/deerflow/community/firecrawl/tools.py`
- `backend/packages/harness/deerflow/community/academic_search/`
- `backend/packages/harness/deerflow/community/semantic_scholar/`
- `backend/tests/test_semantic_scholar_tools.py`
- 新增 backend citation normalizer 单测。

不在本改动中修改：

- LangGraph runtime、checkpoint、RunManager。
- Gateway API response models。
- 前端 UI 展示逻辑。

### Iteration policy

先写纯函数或 fixture 测试定义 canonical citation shape，再改一个工具族。每次只让一个工具族通过测试；如果 web 和 academic 的需求冲突，以最小公共字段为 contract，把 provider-specific 字段留在 `metadata` 或原字段里。

### Blocked stop condition

如果某个 provider 的返回中确实没有可验证 URL，停止扩展该 provider 的 `citationUrl`，报告具体 provider、缺失字段和原始 fixture；该工具只能返回 `citationUrl: null` 并要求最终回答说明证据不足。

## Change 2 - Provider-Correct Academic Citation URLs

### Outcome

Academic 工具不再默认把所有 `paperId` 拼成 Semantic Scholar URL。完成时：

- Semantic Scholar 结果使用 `https://www.semanticscholar.org/paper/<paperId>`。
- OpenAlex 结果使用 OpenAlex work URL，例如 `https://openalex.org/W...`。
- DOI 优先提供 `https://doi.org/<doi>`，同时保留 OpenAlex 或 Semantic Scholar 详情链接。
- `openAccessPdfUrl` 作为 `pdfUrl` 或原字段保留，不替代主引用 URL。
- `academic_get_citation_network` 的 nodes 也有可点击、provider-correct 的引用 URL。

### Verification surface

- OpenAlex fixture 中 `paperId=W...` 时，断言 `citationUrl` 是 OpenAlex URL，而不是 Semantic Scholar URL。
- Semantic Scholar fixture 中 40 字符 `paperId` 时，断言 `citationUrl` 是 Semantic Scholar URL。
- DOI fixture 中存在 DOI 时，断言 DOI URL 可被选为 primary citation 或至少存在于 `externalIds` / `metadata`。
- Frontend 工具卡片 fixture 断言 academic card 使用 `citationUrl` 而不是硬编码 Semantic Scholar URL。

### Constraints

- 不改变 academic search 的 source fallback 策略。
- 不要求 OpenAlex 结果强行查一次 Semantic Scholar 才能生成引用。
- 不把 `openAccessPdfUrl` 当作论文记录页；PDF 链接只能作为补充。
- 不破坏 BibTeX 生成逻辑。

### Boundaries

允许修改：

- `backend/packages/harness/deerflow/community/academic_search/openalex_client.py`
- `backend/packages/harness/deerflow/community/semantic_scholar/client.py`
- `backend/packages/harness/deerflow/community/academic_search/bibtex.py`，仅当 BibTeX URL 字段需要同步 canonical URL。
- `frontend/src/components/workspace/messages/message-group.tsx`
- 对应 backend/frontend tests。

不在本改动中修改：

- Provider API credential 配置。
- Academic search cache backend。
- Citation network 的业务语义。

### Iteration policy

先修后端数据，再修前端消费。每次 fixture 中都保留一个 OpenAlex 和一个 Semantic Scholar 样本，防止再次把两者混为一谈。

### Blocked stop condition

如果某类 paper ID 无法可靠识别 provider，停止自动拼 URL，只返回 `citationUrl: null` 和 `citationProvider: unknown`，并在文档和测试中记录需要 `academic_get_paper` 或 provider enrichment 才能继续。

## Change 3 - Web Evidence Depth and Fetch Provenance

### Outcome

普通网页证据链至少有两层：

- `web_search` 提供候选来源和摘要级引用。
- `web_fetch` 在配置启用时提供正文级引用，并在返回内容头部包含 `citationUrl`、`citationTitle`、`fetchedAt`。

完成时，回答当前事实、产品信息、新闻、文档等非学术问题时，agent 能在必要时从搜索结果进入 fetch，并引用正文来源，而不只引用搜索摘要。

### Verification surface

- 工具列表测试证明启用 `web_fetch` 配置后 agent 绑定该工具。
- `web_fetch` fixture 测试证明返回内容包含原始 URL 作为 canonical citation。
- Prompt 测试证明 web research 流程要求“搜索发现来源，fetch 验证关键事实，最终引用 fetch/source URL”。
- 如果只更新示例配置，验证 `config.example.yaml` 与 `config.yaml` 的意图说明一致。

### Constraints

- 不默认依赖需要付费或不可用的 provider，除非配置明确启用。
- 不在没有正文抓取证据时声称已经验证页面内容。
- 不扩大网络权限；工具仍只 fetch 用户给出的 URL 或 search 返回的 URL。
- 不把认证墙、私有文档、登录页抓取失败伪装成证据。

### Boundaries

允许修改：

- `config.example.yaml`
- `config.yaml`，仅在需要同步本地运行配置且确认不会提交敏感值时。
- `backend/packages/harness/deerflow/community/jina_ai/tools.py`
- `backend/packages/harness/deerflow/community/tavily/tools.py`
- `backend/packages/harness/deerflow/community/firecrawl/tools.py`
- Web tool tests。

不在本改动中修改：

- 浏览器自动化或 MCP web tools。
- Gateway 网络代理。
- 前端设置页。

### Iteration policy

先让工具在不启用 fetch 的情况下仍能稳定引用 search URL；再增加 fetch provenance。若 provider 不稳定，保留 search-only 路径，不阻塞 academic citation 修复。

### Blocked stop condition

如果当前环境缺少可用 web fetch provider 或 API key，停止在运行配置中启用它，只提交 provider-agnostic 工具和 prompt 改动，并在结果中报告“search-level citations only”的限制。

## Change 4 - Prompt Citation Contract

### Outcome

Prompt 从“建议带引用”升级为“使用外部证据时必须按 claim 附引用”。完成时：

- `<citations>` 明确区分无需引用的协作/代码执行说明和必须引用的外部事实。
- 外部工具支持的事实使用 `[citation:显示文本](citationUrl)` 或 `[显示文本](citationUrl)` 紧跟在 claim 后。
- Academic 引用不再假设 `paperId` 一定是 Semantic Scholar ID，而是优先使用工具返回的 `citationUrl`。
- 长回答末尾可有 `Sources` 汇总，但正文 claim-level citation 仍是主要求。
- 找不到可验证引用时，模型必须说明“当前证据不足”，不能编造。

### Verification surface

- `tests/test_lead_agent_prompt.py` 断言真实 `apply_prompt_template()` 包含 citation contract。
- `tests/test_prompt_snapshot.py` 或 snapshots 更新后，断言 lead prompt 中包含 provider-correct citation wording。
- Prompt fixture 中覆盖 web、academic、本地文件三类引用格式。
- 手动只读探针可打印 `has_citations True` 并展示更新后的 `<citations>` 片段。

### Constraints

- 不降低现有 scientific method 对学术证据的要求。
- 不让普通闲聊、代码变更总结、执行状态更新被迫堆引用。
- 不让 prompt 鼓励模型编造 URL。
- 不绕开现有 Jinja2 prompt factory 和 cache boundary。

### Boundaries

允许修改：

- `backend/packages/harness/deerflow/prompts/templates/partials/citations.j2`
- `backend/packages/harness/deerflow/prompts/templates/partials/scientific_method.j2`
- `backend/packages/harness/deerflow/prompts/templates/partials/collaboration_mechanics.j2`
- `backend/tests/test_lead_agent_prompt.py`
- `backend/tests/test_prompt_snapshot.py`
- `backend/tests/snapshots/*.txt`，仅在 prompt 文案变更明确且 review diff 后。

不在本改动中修改：

- Agent personality、tone、git safety、tool permission prompt。
- Middleware order。
- Memory injection。

### Iteration policy

每次只收紧一种引用规则，先跑 prompt 单测，再看 snapshot diff。若 snapshot diff 混入无关 prompt 文案，回退该次文案改动并拆小。

### Blocked stop condition

如果模型在真实对话中仍系统性忽略 citation contract，但工具结果已提供 canonical fields，则停止继续堆 prompt，转为设计执行层约束，例如 response post-check、citation audit middleware 或 final-answer repair loop。

## Change 5 - Frontend Citation Consumption

### Outcome

前端显示与工具 canonical citation fields 对齐：

- Tool call cards 优先读取 `citationUrl`。
- Academic card 不再硬编码 Semantic Scholar URL。
- 普通 Markdown 链接继续可点击。
- `citation:` 前缀链接继续由 `CitationLink` 渲染为 citation badge。
- 若工具结果没有 `citationUrl`，前端显示标题但不制造链接。

### Verification surface

- Frontend unit tests 覆盖 `message-group.tsx` 的 academic search、academic get paper、web search cards。
- Markdown rendering tests 覆盖 `[citation:Title](https://example.com)` 渲染路径。
- `cd frontend && pnpm check`
- 如涉及视觉样式，补充一张工具卡片和最终回答 citation badge 的截图。

### Constraints

- 不改变消息流协议。
- 不改变 backend tool result 的旧字段消费能力。
- 不新增卡片内复杂信息架构；只替换链接来源与空值处理。
- 不把不存在的 citation URL 展示为可点击链接。

### Boundaries

允许修改：

- `frontend/src/components/workspace/messages/message-group.tsx`
- `frontend/src/components/workspace/messages/markdown-content.tsx`，仅当 citation prefix 行为需要补测或微调。
- `frontend/src/components/workspace/citations/citation-link.tsx`，仅当展示空 URL 或标题 fallback 有 bug。
- 对应 frontend tests。

不在本改动中修改：

- SSE stream parser。
- Message storage model。
- Workspace navigation。

### Iteration policy

先让已有 UI 使用 canonical 字段，不做视觉改版。每次 UI 改动后跑 focused test，再跑 `pnpm check`；如果样式调整引入截图差异，单独拆成后续 UI polish。

### Blocked stop condition

如果工具结果在前端链路中被序列化为字符串导致 canonical fields 丢失，停止 UI 层修补，先回到 backend/frontend message serialization 边界确认结果解析位置。

## Change 6 - Regression Harness and Live Citation Probe

### Outcome

最终交付不仅靠 prompt 文案，而有一条可重复的验证链：

- Model-free tests 证明工具结果含 canonical citation fields。
- Prompt tests 证明引用 contract 已进入真实 lead prompt。
- Frontend tests 证明 citation fields 被显示为链接或 badge。
- 一个最小 live probe 文档化：给 agent 一个需要 web 或 academic evidence 的问题，检查最终回答是否有 claim-level citation。

### Verification surface

必须记录至少以下结果：

```bash
cd backend && PYTHONPATH=. uv run pytest tests/test_lead_agent_prompt.py tests/test_semantic_scholar_tools.py -q
```

```bash
cd frontend && pnpm check
```

如果进行了 prompt snapshot 更新，还必须记录：

```bash
cd backend && PYTHONPATH=. uv run pytest tests/test_prompt_snapshot.py -q
```

如果进行了 live probe，保存问题、工具调用摘要、最终回答片段和引用链接检查结果。

### Constraints

- 不把 live probe 当作唯一通过标准；它只能补充 model-free tests。
- 不把 provider 网络失败误判为 citation contract 失败。
- 不提交 API key、缓存数据库、`.env`、`config.yaml` 中的本地敏感值。
- 不把无关本地脏文件纳入提交。

### Boundaries

允许使用：

- Backend pytest。
- Frontend `pnpm check`。
- 只读 prompt construction probe。
- 必要时最小 agent 对话 probe。

不允许使用：

- 大范围生产构建作为唯一验证面。
- 未授权网络抓取。
- 会修改用户数据或 memory 的非必要 live conversation。

### Iteration policy

每轮变更后按从便宜到昂贵的顺序验证：

1. Pure unit tests。
2. Prompt tests / snapshot。
3. Frontend check。
4. Optional live probe。

任何一层失败，先修该层，不继续叠加后续改动。

### Blocked stop condition

如果 unit tests 和 prompt/frontend tests 均通过，但 live probe 因 provider 网络、API key、模型不可用或外部服务限流无法完成，停止继续尝试，报告已通过的 deterministic evidence、未验证的 live surface、失败原因和恢复后应运行的命令。

## Done when

Phase 7 完成时必须同时满足：

1. Web 和 academic 工具结果存在 canonical citation fields，且旧字段兼容。
2. Academic citation URL 不再错误假设所有 `paperId` 都属于 Semantic Scholar。
3. Prompt 明确要求外部证据 claim-level citation，并引用工具返回的 `citationUrl`。
4. 前端工具卡片使用 canonical citation URL。
5. Backend 和 frontend 的 deterministic tests 通过。
6. 若环境允许，至少完成一次最小 live citation probe；若不允许，明确记录阻塞原因。

## Stop if

满足以下任一条件时暂停实现并重新确认方案：

- 需要引入新的外部 provider 或付费 API 才能继续。
- Citation contract 需要改变 LangGraph message schema 或 SSE wire format。
- 工具返回字段修改会破坏现有 frontend 或 channel 展示。
- OpenAlex、Semantic Scholar、DOI 之间的 URL 归一化无法在不额外联网的情况下可靠完成。
- 模型持续忽略 prompt 约束，表明需要执行层 citation audit，而不是继续改 prompt。
