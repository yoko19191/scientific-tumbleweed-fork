# Phase 1: Scope — 背景预调研与访谈式需求收集

本文件在 Phase 1 开始时加载。目标：先用学术与互联网搜索对用户提问背景做轻量预调研，再通过结构化访谈补齐意图，生成 Article Outline + Writing Outline（文章结构与写作大纲）。

> **硬门控**：用户必须明确确认 Article Outline + Writing Outline 后才能进入 Phase 2。不得跳过、不得隐式确认。
> **文件门控**：进入 Phase 2 前，文章结构大纲和写作计划必须已写入本地文件系统，并且文件内容与用户看到的最新版本一致。

---

## 1. 背景预调研协议

在第一次向用户追问前，优先基于用户原始提问执行轻量背景调查。不要等待用户把领域背景讲完整。

### 调研目标

形成一个 **Background Brief**，用于提高后续提问质量：

- 该主题所属研究领域、常见术语和同义表达
- 近年主要研究分支和代表性问题
- 初步可见的机制、因果链或解释框架
- 已知争议、证据不足或相互矛盾的结论
- 可能适合的 2-4 个 RQ 候选和 3-7 个子主题候选

### 搜索顺序

1. 优先使用学术搜索工具查找高引用综述、近年综述和代表性论文。
2. 使用互联网搜索补充术语、应用背景、政策/技术报告或领域脉络。
3. 不做大规模论文搜集；Phase 1 只需要足够支撑提问和文章结构大纲的背景。

### Background Brief 输出

在生成文章结构大纲前先内部形成以下摘要，并将其要点写入 Article Outline + Writing Outline：

```markdown
Background Brief:
- Field framing:
- Key terms and synonyms:
- Initial mechanism hypotheses:
- Evidence tensions:
- Candidate RQs:
- Candidate subtopics:
```

禁止把 Background Brief 写成“我使用了某工具”的过程记录。它应当像研究者的初步阅读笔记。

---

## 2. Gap 质量阶梯

帮助用户评估和提升其研究空白的质量。在访谈中主动引导用户从低阶梯向高阶梯攀升：

| 阶梯 | 描述 | 示例 | 评价 |
|------|------|------|------|
| 🔴 Rung 1 | 「没人研究过 X」 | "There is no study on X" | 最弱——缺乏具体性，可能只是搜索不够 |
| 🟡 Rung 2 | 「已有研究存在方法局限 Y」 | "Existing methods for X have limitation Y" | 可接受——但需要证据支撑 |
| 🟢 Rung 3 | 「关于 X 的研究结论相互矛盾」 | "Studies disagree on whether X causes Y" | 强——张力驱动，有明确的综合价值 |
| 🟢 Rung 4 | 「现有框架无法解释新现象 X」 | "No existing framework accounts for the emergence of X" | 最强——理论贡献明确 |

**引导策略**：
- 如果用户给出 Rung 1 级别的 gap，追问：「能否具体说明现有研究在哪些方面不足？」
- 如果用户给出 Rung 2 级别的 gap，追问：「这些局限是否导致了研究结论的分歧？」
- 目标：将 gap 提升到 Rung 3 或 4

---

## 3. 八种叙事模板

向用户展示以下 8 种叙事模板，帮助选择综述的故事线：

| 编号 | 模板 | 一句话描述 | 典型场景 |
|------|------|-----------|---------|
| a | 新现象 | 现象 X 兴起但学术研究稀缺 | 新兴技术、新发现 |
| b | 新人群/新场景 | 现象 X 在特定人群/场景中尚待研究 | 跨地域/跨人群迁移 |
| c | 新发展 | 现象 X 发生质变，旧框架不再适用 | 范式转换 |
| d | 两面性 | 现象 X 的负面/风险面被忽视 | 有争议的技术/政策 |
| e | 矛盾性 | 关于 X 的研究结论相互矛盾 | 实验结果不一致 |
| f | 分支整合 | 多个研究分支各自独立，缺乏整合 | 多学科交叉 |
| g | 领域渗透 | 方法 X 在领域 A 成熟，可迁移到领域 B | 方法迁移 |
| h | 跨学科 | 领域 A 和 B 的交叉点出现新机会 | 学科融合 |

**选择指导**：
- 如果用户不确定，根据其描述的 gap 类型推荐：
  - Gap 是「没人做过」→ 推荐 a/b
  - Gap 是「方法有局限」→ 推荐 c/g
  - Gap 是「结论矛盾」→ 推荐 e
  - Gap 是「缺乏整合」→ 推荐 f/h
  - Gap 是「忽视负面」→ 推荐 d

---

## 4. 访谈协议

使用对话澄清进行**一次性 bundled 提问**，不逐个问。将以下问题合并为 1-2 轮对话：

### 第一轮（必问）

以下信息必须在第一轮收集完毕。提问时结合 Background Brief，主动给出候选项，而不是只问开放问题：

1. **研究主题**：你希望综述覆盖哪个研究领域/主题？
2. **研究空白**：你认为现有文献在这个主题上存在什么不足或空白？（引导用户使用 Gap 质量阶梯评估）
3. **叙事角度**：展示 8 种叙事模板，请用户选择最贴合的一种（或基于预调研推荐）
4. **研究问题**：基于主题、gap 和预调研结果，建议 2-4 个具体的研究问题（RQ），请用户确认或修改
5. **目标场景**：这篇综述用于什么？（期刊投稿 / 学位论文章节 / 研究提案 / 通用概述）

### 第二轮（仅在上下文不明确时追问）

以下信息如果从第一轮回答中无法推断，才需要追问：

6. **范围约束**：时间窗口（默认近 5 年）、子领域包含/排除、语言偏好
7. **目标引用数**：默认 60 篇，范围 40-120。超过 120 篇建议拆分子主题
8. **输出语言**：综述正文默认英文；仅当用户明确要求中文时改为中文（影响 LaTeX 模板选择）
9. **关键论文**：是否有必须包含的论文？（种子论文，用于引用网络扩展）

---

## 5. Article Outline + Writing Outline 模板

访谈完成后，生成以下文章结构与写作大纲并请用户确认。最终输出不是需求卡片；必须是可直接驱动 Explore 和 Write 的 outline。

### Scope 文件 offload 要求

在展示给用户确认前，必须先创建输出目录并写入两个 Scope 文件：

```text
survey+{title}+{version}/
  scope/
    article-outline.md
    writing-plan.md
```

- `scope/article-outline.md`：保存 Working Title、Background Framing、Review Thesis and Gap、Research Questions、Scope and Constraints、Article Structure Outline 和 Explore Task Map。
- `scope/writing-plan.md`：保存 Writing Strategy、章节写作顺序、每章 planned claim、证据需求、表格/图计划、需要强证据支持的主张、需要 hedging 或作为 gap 处理的主张。
- 两个文件必须在每次用户修改 outline 或 writing plan 后同步更新；不得只在聊天中更新。
- 请求用户确认时，必须同时展示 outline 摘要和这两个文件路径。
- 进入 Phase 2 时，后续阶段应从这两个文件读取最新文章结构和写作计划，而不是依赖聊天上下文。

```markdown
# Article Outline + Writing Outline

## Working Title
[拟定综述标题]

## Background Framing
- Field framing: [3-5 条领域脉络]
- Key terms and synonyms: [...]
- Initial mechanism hypotheses: [...]
- Evidence tensions: [...]

## Review Thesis and Gap
- Narrative template: [a-h 编号 + 名称]
- Research gap: [一句话描述，标注 Gap 阶梯等级]
- Central synthesis claim: [这篇综述预计要建立的核心综合观点]

## Research Questions
- RQ1: [...]
- RQ2: [...]
- RQ3: [...]（如有）

## Scope and Constraints
- Target venue/use case: [期刊/学位论文/提案/通用]
- Target citation count: [N] 篇
- Time window: [YYYY-YYYY]
- Output language: [英文/中文；默认英文]
- Inclusion criteria: [...]
- Exclusion criteria: [...]
- Seed papers: [如有]

## Article Structure Outline
1. Introduction
   - Purpose: [本章功能]
   - Funnel logic: Background → Field → Mini Review → Significance → RQs → Contribution → Overview
   - Key evidence needed: [...]
2. Background and Definitions
   - Core concepts: [...]
   - Boundaries: [...]
3. Survey Methodology
   - Databases/data sources: [...]
   - Search strategy: [...]
   - Inclusion/exclusion logic: [...]
4. Thematic Section 1: [章节标题]
   - Core mechanism/question: [...]
   - Planned claim: [...]
   - Related RQ(s): [...]
   - Evidence to collect in Explore: [...]
   - Required comparison table: [...]
5. Thematic Section 2: [...]
6. Thematic Section 3: [...]
7. Discussion
   - Cross-theme synthesis: [...]
   - Expected contradictions to resolve: [...]
   - Boundary conditions: [...]
   - Future directions: [...]
8. Conclusion
   - RQ-by-RQ answer plan: [...]
   - Contribution summary: [...]

## Explore Task Map
- Topic 1: [搜索子主题] → feeds Section [N], RQ [...]
- Topic 2: [...]
- Topic 3: [...]

## Writing Strategy
- Intended audience and tone: [...]
- Argument style: [机制驱动/矛盾整合/跨学科桥接等]
- Chapter drafting order: [...]
- Tables/figures planned: [...]
- Claims requiring strongest evidence: [...]
- Claims to hedge or treat as gaps: [...]
```

**子主题拆分规则**：
- 根据 RQ、叙事模板和文章章节结构，将主题拆分为 3-7 个 Explore 子主题
- 子主题优先围绕机制、证据链、边界条件和争议组织，而不是围绕论文列表组织
- 每个子主题对应 Explore 阶段的一个搜索任务，并明确喂给哪个主题章节
- 每个主题章节必须在 Article Structure Outline 中有 planned claim、相关 RQ 和证据需求

---

## 6. 门控条件

**DO NOT proceed to Phase 2 until ALL of the following are true:**
1. 用户已看到完整的 Article Outline + Writing Outline
2. 用户已明确回复确认（"确认"/"OK"/"proceed" 等肯定表达）
3. Outline 中的 RQ 数量 ≥ 2
4. Explore Task Map 中的子主题数量 ≥ 3
5. Outline 已包含基于预调研的背景脉络、初步机制/证据张力、文章章节结构和写作策略
6. 每个主题章节都映射到至少一个 RQ 和至少一个 Explore 子任务
7. `scope/article-outline.md` 和 `scope/writing-plan.md` 已写入本地文件系统，且内容与用户确认版本一致

如果用户要求修改，更新 Article Outline + Writing Outline，并同步更新 `scope/article-outline.md` 和 `scope/writing-plan.md` 后重新请求确认。
