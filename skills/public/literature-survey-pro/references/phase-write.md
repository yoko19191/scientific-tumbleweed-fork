# Phase 3: Write — LaTeX 生成

本文件在 Phase 3 开始时加载。目标：先将 Explore 阶段的 `explore/explore.tex` + `explore/references.bib` 资料包、论文索引、证据矩阵和证据收敛摘要综合为 `synthesis-blueprint.md`，再生成 LaTeX 格式的文献综述。

> **门控条件**：(a) `synthesis-blueprint.md` 已生成并被正文使用 (b) 所有 `\cite{}` 有对应 `.bib` 条目 (c) ≥2 个对比表格 (d) 无列举反模式 (e) Introduction 遵循漏斗结构。全部通过才能进入 Phase 4。
> 默认正文语言为英文；仅当 Article Outline + Writing Outline 明确要求中文时使用中文模板和中文正文。

---

## 1. 文件初始化

### Step 1: 创建输出目录
```bash
mkdir -p "survey+{title}+{version}/"
```

### Step 2: 复制模板
将 `templates/survey-template.tex` 复制到输出目录，命名为 `survey.tex`。模板只包含 preamble、作者、Abstract 容器、`%BODY%` 和 bibliography；除 Abstract 与作者外，不预置任何章节。

### Step 3: 创建空 BibTeX 文件
创建 `references.bib`，写入文件头注释：
```bibtex
% Bibliography for: <SURVEY_TITLE>
% Author: Scientific Tumbleweed
% Date: <YYYY-MM-DD>
```

### Step 4: 批量导出 BibTeX
使用可用的学术元数据或 BibTeX 导出能力批量导出所有已收集论文的 BibTeX 条目：
- 每次最多传入 20 个 paper_id
- 对于数据源未返回 BibTeX 的论文，根据真实元数据手动构建条目（遵循 `latex-template.md` 中的规范）
- arXiv 预印本必须使用 `@misc`，不得使用 `@article`
- 优先从 `explore/references.bib` 合并 Explore 阶段已验证的条目；合并时去重并保持 cite key 稳定，避免破坏 Explore `.tex` 文件中的引用。

---

## 2. Synthesis Blueprint — 写作前综合蓝图

正文写作前必须生成 `synthesis-blueprint.md`。这是从“论文列表”到“综述论证”的关键中间层。

### 输入文件

- `explore/explore.tex`
- `explore/papers.json`
- `explore/references.bib`
- `scope/article-outline.md`
- `scope/writing-plan.md`

### 输出结构

```markdown
# Synthesis Blueprint

## Core Mechanism Views
| Mechanism View | Evidence Status | Key Sources | Boundary Conditions | Planned Section |
|----------------|-----------------|-------------|---------------------|-----------------|
| ... | Strong/Moderate/Weak/Contested/Gap | ... | ... | ... |

## Evidence Clusters
### Cluster 1: [name]
- Claim:
- Supporting evidence:
- Contradicting evidence:
- Evidence strength:
- Boundary conditions:
- Use in sections:

## Contradictions and Resolutions
| Tension | Competing Claims | Likely Explanation | Writing Treatment |
|---------|------------------|--------------------|-------------------|

## Claim-Evidence-Reasoning Chains
### CER 1
- Claim:
- Evidence:
- Reasoning:
- Counter-argument:
- Rebuttal or limitation:
- Citation keys:

## Devil's Advocate Stress Test
- Strongest counter-argument to the central synthesis:
- Possible cherry-picking risk:
- Claims most likely to overreach the evidence:
- Alternative explanation for the same evidence:
- Required mitigation in the draft:

## Section Evidence Allocation
| Section | Core Claim | Evidence Clusters | Required Citations | Required Table |
|---------|------------|-------------------|--------------------|----------------|

## Gaps and Future Directions
- Empirical gaps:
- Methodological gaps:
- Theoretical gaps:
- Boundary-condition gaps:
```

### 蓝图规则

- 每个主题章节至少对应 1 条 CER 链。
- 每个核心机制观点必须有证据状态：Strong / Moderate / Weak / Contested / Gap。
- 所有 Contested 机制必须写入 “Contradictions and Resolutions”，不得在正文中只并列描述。
- Devil's Advocate Stress Test 必须指出 strongest counter-argument、cherry-picking 风险和可能过度推论的主张。
- Evidence Status 为 Weak 或 Gap 的观点只能作为研究空白或未来方向，不得写成确定结论。
- `synthesis-blueprint.md` 完成后，正文写作只能从该蓝图取核心论证结构。

---

## 3. 逐章生成协议

**核心原则**：一次只写一个章节，写完后执行冷却规则，再写下一个。

### 生成顺序

按以下固定顺序生成各章节：

1. **Synthesis Blueprint** — 写作前综合蓝图，先于所有正文
2. **Survey Methodology** — 搜索和筛选策略的客观记录
3. **Background** — 定义核心概念和术语
4. **Thematic Sections** — 按 `synthesis-blueprint.md` 的 Section Evidence Allocation 逐个生成
5. **Discussion** — 跨主题综合分析
6. **Introduction** — 倒数第二写（需要全文视角才能写好漏斗结构）
7. **Conclusion** — 最后写（回应 RQ，总结贡献）
8. **Abstract** — 最后生成（全文浓缩）

### 每章生成流程

对于每个章节：

1. **加载上下文**：从 `scope/article-outline.md`、`scope/writing-plan.md`、`synthesis-blueprint.md`、`explore/explore.tex`、`explore/references.bib` 和 `explore/papers.json` 中读取该章节相关的 planned claim、写作策略、机制观点、CER 链、BibTeX key 和论文元数据
2. **转场强化注入**：在内部重申以下约束——
   > 你正在撰写学术综述。事实来源是 `synthesis-blueprint.md` 和 `explore/` 中的 LaTeX 背景简报、证据矩阵、证据收敛摘要、BibTeX 条目和论文元数据索引。禁止使用训练数据中的记忆填充。如果某个细节在这些文件中找不到依据，标注 `[需补充]` 并继续。
3. **生成内容**：按 `synthesis-blueprint.md` 的 CER 链和 `writing-methodology.md` 中的机制观点、证据聚合和反模式规则撰写
4. **追加到 .tex**：将已完成章节按 `scope/article-outline.md` 与 `scope/writing-plan.md` 拼接成完整正文，替换 `survey.tex` 中的 `%BODY%`；不要依赖模板中预置章节
5. **同步 .bib**：确保该章节引用的所有论文都已在 `references.bib` 中
6. **冷却**：从上下文中丢弃该章节的详细论文元数据，仅保留章节摘要（1-2 句）

---

## 4. 各章节写作规范

### 4.1 Survey Methodology

记录文献筛选过程的客观事实，使综述可复现。写作口吻应像研究者的方法说明，不提及智能体、内部工具名、prompt、subagent 或自动化流程。

```latex
\section{Survey Methodology}
\label{sec:methodology}

This survey was conducted following a systematic search protocol.
We searched [数据源列表] using [关键词列表] for publications
between [时间窗口]. The search yielded [N] unique papers after
deduplication. Papers were included if [纳入标准] and excluded
if [排除标准]. Forward and backward citation tracing was conducted
from [M] seed papers to identify additional relevant work.

\begin{table}[H]
\centering
\caption{Search strategy summary.}
\label{tab:search_strategy}
\begin{tabularx}{\textwidth}{lX}
\toprule
\textbf{Parameter} & \textbf{Value} \\
\midrule
Databases & Semantic Scholar, OpenAlex, arXiv \\
Keywords & [关键词组] \\
Time window & [YYYY--YYYY] \\
Total retrieved & [N] papers \\
After deduplication & [M] papers \\
Inclusion criteria & [标准] \\
\bottomrule
\end{tabularx}
\end{table}
```

### 4.2 Background

- 定义核心术语和概念
- 提供必要的技术/理论背景
- 不超过全文的 10%
- 引用权威教科书或综述文章

### 4.3 Thematic Sections（主题章节）

每个主题章节必须包含以下 5 个组成部分：

**a. 开头段（1-2 段）**：
- 提出该主题的核心机制问题或解释框架
- 与前一章节的逻辑衔接
- 明确该章节使用 `synthesis-blueprint.md` 中哪几条 CER 链

**b. 机制/证据分组（主体）**：
- 按机制观点、因果链、证据类型和边界条件分组，**不按论文逐篇描述**
- 每组一个段落，遵循：机制主张 → 证据簇 → 证据强度评估 → 边界条件 → 过渡
- 使用 `\citet{}` 和 `\citep{}` 混合引用
- 对 Contested 证据必须解释分歧来源，不能只写 “some studies... while others...”

**c. 对比表格（≥1 个）**：
- 使用 `booktabs` 风格
- 列设计参考 `latex-template.md`，优先比较机制、证据类型、证据强度和边界条件
- 表格必须在正文中被引用

**d. 局限性段（1 段）**：
- 该主题方向的共性证据缺口、混杂因素和外推限制
- 使用 hedging 语言

**e. Key Findings 框（可选）**：
```latex
\begin{keyfindings}
\begin{itemize}[nosep]
  \item ...
\end{itemize}
\end{keyfindings}
```

### 4.4 Discussion

跨主题综合分析，必须覆盖：

1. **共识**：多个主题章节中一致的发现
2. **矛盾**：不同研究之间的分歧及可能原因
3. **机制图景**：主要机制观点、因果链和边界条件如何相互连接
4. **研究空白**：使用 Research Gap 框汇总
5. **未来方向**：具体、可操作的研究建议（不是空泛的 "future work is needed"）
6. **反方视角**：至少回应一个 strongest counter-argument，并说明其对结论边界的影响

### 4.5 Introduction（倒数第二写）

严格遵循 `writing-methodology.md` 中的 7 段漏斗结构。

**写作前检查**：
- 已完成所有主题章节和 Discussion
- 对全文内容有完整把握
- `scope/article-outline.md` 和 `scope/writing-plan.md` 中的叙事模板、文章结构和写作策略已确认

**写作后检查**：
- However Test 通过
- 1大2小3个点 完整
- 每个 RQ 在 Introduction 中被明确提出
- 引用策略正确（开头权威、中段近期、gap 处精准）

### 4.6 Conclusion

- 逐一回应每个 RQ（与 Introduction 中提出的 RQ 一一对应）
- 总结主要贡献（理论 + 实践）
- 承认局限性（搜索范围、方法论限制）
- 展望（与 Discussion 的未来方向呼应但不重复）

### 4.7 Abstract（最后生成）

- ≤ 250 词
- 结构：目的 → 方法 → 主要发现 → 结论
- 不包含引用
- 不包含缩写（首次出现时展开）

---

## 5. 引用诚实规则

贯穿整个 Write 阶段的铁律：

1. **禁止捏造**：所有 BibTeX 字段必须来自学术数据源返回或论文原始元数据。不确定的字段**省略**而非编造。
2. **Hedging 标注**：如果仅阅读了摘要而非全文，使用 "reportedly" 或 "according to the authors" 等限定语。
3. **[需补充] 标记**：如果某个论述需要引用但找不到合适的论文，标注 `% [需补充: 此处需要关于 X 的引用]` 作为 LaTeX 注释，在 Polish 阶段处理。
4. **Entry type 正确性**：
   - 期刊论文 → `@article`
   - 会议论文 → `@inproceedings`
   - arXiv 预印本 → `@misc`（**绝不**用 `@article`）
   - 技术报告/白皮书 → `@techreport` 或 `@misc`

---

## 6. 转场强化注入

每开始写一个新章节时，在内部重新注入以下提醒：

> **学术人设重申**：你是资深综述作者，行文客观、精确、有批判性。禁止口语化、第一人称情绪表达。
>
> **作者身份**：论文默认作者是“Scientific Tumbleweed”。论文正文不得提及智能体、模型、prompt、工具调用或内部执行过程。
>
> **反模式检测**：检查你即将写的内容是否存在以下问题：
> - 连续 3+ 句以作者名开头（列举反模式）
> - 与前序章节大段重复（用交叉引用 `Section~\ref{sec:...}` 替代）
> - 缺少过渡连接词
> - 缺少机制解释、证据强度评估或边界条件（纯描述）
> - 没有使用 `synthesis-blueprint.md` 的 CER 链，导致重新回到论文内容堆砌
>
> **事实来源重申**：你的事实来源是 `synthesis-blueprint.md` 与 `explore/` 中的 `.tex + .bib` 资料包、证据矩阵、证据收敛摘要和论文元数据索引。禁止使用训练数据填充。

---

## 7. 门控条件检查

Phase 3 完成后，逐项检查：

| 条件 | 检查方法 | 未通过时处理 |
|------|---------|------------|
| `synthesis-blueprint.md` 已生成 | 检查包含 Core Mechanism Views、Evidence Clusters、Contradictions、CER、Section Evidence Allocation | 补写蓝图后再写正文 |
| 蓝图被正文使用 | 随机抽查每个主题章节是否对应至少 1 条 CER 链 | 重写不符合蓝图的章节 |
| 所有 `\cite{}` 有 `.bib` 条目 | 提取 .tex 中所有 cite key，与 .bib 中的 key 交叉比对 | 补充缺失的 .bib 条目 |
| ≥2 个对比表格 | 统计 `\begin{table}` 的数量 | 为缺少表格的主题章节补充 |
| 无列举反模式 | 扫描连续 3+ 行以 `\citet{` 开头的段落 | 重写为主题驱动的段落 |
| 机制与证据驱动 | 检查每个主题章节是否包含机制主张、证据簇、证据强度和边界条件 | 补写机制分析或证据评估 |
| 无内部工具痕迹 | 搜索 agent/tool/subagent/prompt/API call 等内部过程词 | 改写为研究者视角的方法说明 |
| Introduction 漏斗结构 | 检查 7 段结构是否完整 | 补充缺失的段落 |
| 无 `[需补充]` 标记 | 搜索 LaTeX 注释中的标记 | 补充引用或删除相关论述 |
