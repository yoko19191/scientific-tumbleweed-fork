# Phase 2: Explore — 并行文献搜集

本文件在 Phase 2 开始时加载。目标：通过多源搜索和子智能体并行调度，搜集覆盖所有 RQ 的文献集，并积极将 Explore 内容 offload 到本地 LaTeX 资料包。每批搜索结果、子主题调研、证据矩阵和证据收敛摘要都必须尽早写入输出目录的 `explore/` 文件夹。Phase 2 的最终产物不只是论文列表，还必须包括可直接引用和复用的 `explore/explore.tex` + `explore/references.bib`。

> **门控条件**：(a) 论文数 ≥ 目标 80% (b) 每个 RQ 有 ≥5 篇相关论文 (c) 引用网络已遍历 ≥3 种子论文 (d) `explore.tex` 和 `references.bib` 已生成，且 `explore.tex` 包含 Literature Matrix 与 Evidence Convergence 两个 LaTeX 章节。四项全部通过才能进入 Phase 3。

---

## 1. 多源搜索策略

按优先级依次使用以下数据源，每个源有明确的职责分工：

| 优先级 | 数据源/能力 | 说明 | 职责 | 预期产出 |
|--------|--------|------|------|---------|
| 1 | 学术搜索工具 | 使用当前环境可用的学术数据库检索能力 | 主力搜索，覆盖绝大多数同行评审文献 | 每个子主题 15-25 篇候选 |
| 2 | 引用网络分析 | 使用可用的前向/后向引用扩展能力 | 从种子论文出发，发现关键词搜索遗漏的论文 | 每个种子扩展 10-30 篇 |
| 3 | 相关论文推荐 | 使用可用的相似论文或推荐能力 | 基于已收集的高质量论文发现相关工作 | 补充 5-15 篇 |
| 4 | 预印本检索 | 使用可用预印本数据库检索能力 | 补充最新预印本（尤其 CS/ML/Physics 领域） | 每个子主题 5-10 篇 |
| 5 | 作者追踪 | 使用可用作者检索能力 | 追踪关键作者的全部相关工作 | 按需 |
| 6 | 互联网搜索 | 使用可用网络搜索和网页读取能力 | 兜底：灰色文献、技术报告、白皮书 | 仅在前 5 源不足时使用 |

### 能力调用原则

不要在本 Skill 中硬编码具体工具函数名。执行时按运行环境可用能力选择对应实现，并在 `explore/explore.tex` 的 Search Log 章节中记录数据源类型、检索式、时间窗口、返回数量和筛选原因。

---

## 2. 搜索执行协议

按以下步骤执行，严格遵循顺序：

### Step 0: 初始化 explore 文件夹

在输出目录下创建 `explore/`，并保存 Phase 1 的背景预调研摘要：

```text
explore/
  explore.tex
  papers.json
  references.bib
  topics/
```

- Explore 阶段开始前必须读取 `scope/article-outline.md` 和 `scope/writing-plan.md`，以其中的 Article Structure Outline、Explore Task Map、目标引用数、时间窗口、纳入/排除标准和写作策略作为检索与证据组织依据。
- `explore.tex`：Explore 阶段主 LaTeX 文件，必须包含 Background Brief、Search Log、Topic Notes、Literature Matrix、Evidence Convergence 和 Knowledge Gaps 等章节，便于后续主文引用或 `\input{}`。
- `topics/`：可选中间目录；每个子主题可以先写一个 `.tex` 分片，但最终必须汇入 `explore.tex`。
- `papers.json`：最终去重后的全局论文清单。
- `references.bib`：Explore 阶段所有候选论文的 BibTeX 条目；后续 Write 阶段从这里合并到主 `references.bib`。

**本地 offload 要求**：
- Explore 阶段不得把原始搜索结果、完整摘要和子主题长报告长期保留在对话上下文中。
- 每完成一组关键词搜索、一次引用网络遍历、一次推荐扩展或一个子智能体任务，都要立即把结构化结果追加或写入 `explore/explore.tex` 和 `explore/references.bib`。
- 对话上下文中只保留当前决策所需的摘要、计数、缺口和文件路径。
- 如果某批结果尚未完成证据矩阵综合，也要先写入 `explore/topics/[TOPIC_SLUG].tex` 或临时批次 `.tex` 文件，但后续必须合并回 `explore/explore.tex`，并同步更新 `papers.json` 和 `references.bib`。

### Step 1: 关键词扩展
从 `scope/article-outline.md` 和 `scope/writing-plan.md` 中的 Explore Task Map、主题章节和 RQ 提取 2-3 组关键词变体：
- 同义词扩展（如 "attention mechanism" → "self-attention", "cross-attention"）
- 缩写展开（如 "NLP" → "natural language processing"）
- 上下位词（如 "BERT" → "pre-trained language model"）

### Step 2: 跨库搜索
对每组关键词使用学术搜索工具检索：
- 每组关键词目标返回 20 篇左右候选
- 优先使用覆盖同行评审文献的数据源
- 如果 `scope/article-outline.md` 指定了时间窗口，添加年份过滤

同时对 CS/ML/Physics 相关主题使用预印本检索能力补充。

### Step 3: 种子选择
从搜索结果中选择 3-5 篇种子论文，标准：
- 引用数最高的 2-3 篇（领域奠基性工作）
- 最近 2 年内引用增长最快的 1-2 篇（新兴热点）
- `scope/article-outline.md` 中用户指定的种子论文（如有）

### Step 4: 引用网络遍历
对每个种子论文执行双向引用网络遍历：
- 前向引用（citing）：发现后续工作
- 后向引用（cited by）：发现理论基础
- 从网络中筛选与 RQ 相关的论文加入候选集

### Step 5: 推荐扩展
将已收集的高质量论文（引用数 top 5）作为输入，使用相关论文推荐能力发现关键词搜索和引用网络都遗漏的相关工作。

### Step 6: 去重与筛选
- 按 DOI 去重（无 DOI 时按标题模糊匹配）
- 按 `scope/article-outline.md` 的排除条件过滤
- 按时间窗口过滤
- 按与 RQ 的相关性排序（每篇论文标注与哪些 RQ 相关）

### Step 7: 构建证据矩阵

基于 `explore/papers.json` 在 `explore/explore.tex` 中生成 `Literature Matrix` 章节。矩阵用于写作前综合，禁止只作为附录摆设。表格中的代表性来源必须使用 `\citep{...}` 或 `\citet{...}` 引用 `explore/references.bib` 中的 BibTeX key。

基础结构：

```latex
\section{Literature Matrix}
\label{sec:explore_literature_matrix}

\begin{table}[H]
\centering
\caption{Evidence matrix across mechanisms and themes.}
\label{tab:explore_literature_matrix}
\begin{tabularx}{\textwidth}{l l l l X X X X}
\toprule
\textbf{Source} & \textbf{Year} & \textbf{Evidence Type} & \textbf{Evidence Strength} & \textbf{Mechanism A} & \textbf{Mechanism B} & \textbf{Mechanism C} & \textbf{Boundary Conditions} \\
\midrule
Author1 \citep{author2024key} & 2024 & experiment & strong & Supports & Partial & -- & Large-scale setting only \\
Author2 \citep{author2023key} & 2023 & observational & moderate & Contradicts & Supports & -- & Confounded by X \\
\bottomrule
\end{tabularx}
\end{table}
```

标注规则：
- `Supports`：该论文提供支持该机制观点的证据
- `Contradicts`：该论文提供相反证据或挑战该机制观点
- `Partial`：该论文仅在特定边界条件下支持
- `--`：该论文未涉及该机制观点

### Step 8: 生成证据收敛摘要

基于 `explore.tex` 中的 Literature Matrix 章节继续生成 `Evidence Convergence Summary` 章节：

```latex
\section{Evidence Convergence Summary}
\label{sec:explore_evidence_convergence}

\begin{table}[H]
\centering
\caption{Evidence convergence by mechanism view.}
\label{tab:explore_evidence_convergence}
\begin{tabularx}{\textwidth}{X l l l l X}
\toprule
\textbf{Mechanism View} & \textbf{Supporting Sources} & \textbf{Contradicting Sources} & \textbf{Net Status} & \textbf{Confidence} & \textbf{Boundary Conditions} \\
\midrule
Mechanism A & 6 strong/moderate & 1 weak & Strong & High & Applies under ... \\
Mechanism B & 3 moderate & 2 strong & Contested & Medium & Depends on ... \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Contradictions and Resolutions}
\begin{itemize}
  \item Claim A vs Claim B: likely explained by [method/context/time/population].
\end{itemize}

\subsection{Knowledge Gaps}
\begin{itemize}
  \item Empirical gap:
  \item Methodological gap:
  \item Theoretical gap:
  \item Boundary-condition gap:
\end{itemize}
```

证据状态定义：
- **Strong**：3+ 个中高质量来源一致支持，且反方证据弱或可解释
- **Moderate**：2-3 个来源支持，但证据类型或场景有限
- **Weak**：只有少量或低质量证据支持
- **Contested**：支持与反驳证据都存在，且分歧无法简单消解
- **Gap**：该机制观点重要但缺少直接证据

### Step 9: 搜索饱和判断

满足以下至少 3 项后，才能认为 Phase 2 搜索可以停止：

| 条件 | 判断方法 |
|------|---------|
| Source count meets target | 去重后论文数达到 `scope/article-outline.md` 中目标引用数的 80% 以上 |
| No new additions | 最新一轮搜索新增论文数 < 已收集论文数的 10% |
| Theme saturation | 每个核心机制/主题在 `explore.tex` 的 Literature Matrix 章节中至少有 3 篇相关来源 |
| Citation loop closure | 引用链扩展不再发现未收集的关键文献 |
| Temporal coverage | 同时包含奠基性文献和近 3 年代表性研究 |

如果已执行 4 轮补充搜索仍不满足 3 项，记录为 search limitation，并在 `explore.tex` 的 Evidence Convergence Summary 章节中标出受影响的机制观点。

---

## 3. 子智能体调度策略

将 `scope/article-outline.md` 的 Explore Task Map 中的子主题分配给子智能体并行执行。

### 调度规则

- 子智能体职责：只做搜索、整理和结构化输出；不要硬编码具体子智能体类型名称
- 最大并发数：**5**；如果当前运行环境有更低并发限制，按环境限制分批执行
- 每个子智能体负责 1-2 个子主题

### 轮次表

| 子主题数 | 子智能体数 | 轮次 | 每轮调度 |
|---------|-----------|------|---------|
| 1-5 | 1-5 | 1 轮 | 全部 |
| 6-10 | 5+N | 2 轮 | 每轮最多 5 个 |
| 11-15 | 5+5+N | 3 轮 | 每轮最多 5 个 |

### 子智能体 Prompt 模板

~~~text
你是文献搜集专家。请为以下子主题搜集学术文献：

子主题：[TOPIC_NAME]
相关研究问题：[RQ1, RQ2]
搜索关键词：[KEYWORD_SET]
时间窗口：[YEAR_RANGE]
目标论文数：[N] 篇

执行步骤：
1. 使用学术搜索工具搜索每组关键词（每组目标 20 篇左右）
2. 从结果中选择 2-3 篇高引用论文作为种子
3. 对种子执行双向引用网络遍历
4. 去重后，为每篇论文提取结构化元数据
5. 将该子主题的完整调研结果追加到 `explore/explore.tex`（可先暂存到 `explore/topics/[TOPIC_SLUG].tex`），并将引用条目追加到 `explore/references.bib`

输出格式（LaTeX 片段 + BibTeX）：
LaTeX 片段：

```latex
\section{[TOPIC_NAME]}
\label{sec:explore_[TOPIC_SLUG]}

\subsection{Search Summary}
\begin{itemize}
  \item Keywords: [KEYWORD_SET]
  \item Time window: [YEAR_RANGE]
  \item Retrieved: [N] candidates; retained: [M] papers
\end{itemize}

\subsection{Structured Paper Notes}
\begin{table}[H]
\centering
\caption{Structured evidence notes for [TOPIC_NAME].}
\label{tab:explore_[TOPIC_SLUG]_papers}
\begin{tabularx}{\textwidth}{l l X X X X}
\toprule
\textbf{Source} & \textbf{Year} & \textbf{Method} & \textbf{Mechanism View} & \textbf{Evidence Strength} & \textbf{RQ Relevance} \\
\midrule
\citet{bibkey2024example} & 2024 & ... & ... & moderate & RQ1: 4; RQ2: 2 \\
\bottomrule
\end{tabularx}
\end{table}

\subsection{Key Findings and Limitations}
\begin{itemize}
  \item ...
\end{itemize}
```

BibTeX 条目：

```bibtex
@article{bibkey2024example,
  author = {...},
  title = {...},
  year = {2024}
}
```

注意：
- 仅记录学术数据源返回的真实元数据，禁止猜测或捏造
- LaTeX 表格和条目中的摘要性描述限制在 1-2 句以内（节省 token）
- relevance_to_RQ 评分 1-5（5=高度相关）
- mechanism_stance 必须可追溯到 LaTeX 调研笔记中的方法、机制观点、关键发现或局限性；没有依据时标注 not_addressed
- 每个在 `.tex` 中出现的 citation key 必须在 `explore/references.bib` 中存在
~~~

### 结果合并

所有子智能体返回后：
1. 合并所有论文列表
2. 按 DOI/paper_id 去重
3. 统计每个 RQ 的覆盖度
4. 将合并结果写入 `explore/papers.json`（机器可读索引）和 `explore/explore.tex`（可读 LaTeX 主资料包）
5. 将检索过程追加到 `explore/explore.tex` 的 Search Log 章节
6. 在 `explore/explore.tex` 中生成或更新 Literature Matrix 章节
7. 在 `explore/explore.tex` 中生成或更新 Evidence Convergence Summary 章节
8. 合并并去重 `explore/references.bib`
9. 检查门控条件

---

## 4. 元数据提取 Schema

每篇论文的结构化记录必须包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| paper_id | string | ✅ | DOI 优先，无 DOI 时用 S2 ID 或 arXiv ID |
| title | string | ✅ | 论文标题 |
| authors | string[] | ✅ | 作者列表 |
| year | int | ✅ | 发表年份 |
| venue | string | ⚠️ | 期刊/会议名称（预印本标注 "arXiv"） |
| abstract_summary | string | ✅ | 1-2 句摘要（非全文摘要） |
| methodology | string | ⚠️ | 方法简述 |
| mechanism_view | string | ✅ | 该论文支持、反驳或修正的机制观点 |
| mechanism_stance | dict | ✅ | 对每个机制观点的立场：supports/contradicts/partial/not_addressed |
| evidence_type | string | ✅ | 证据类型：experiment/observational/theoretical/review/benchmark/case-study/unknown |
| evidence_strength | string | ✅ | 证据强度：strong/moderate/weak/unknown，需基于研究设计和样本/评估质量 |
| boundary_conditions | string | ⚠️ | 适用范围、前提条件或外推限制 |
| key_findings | string[] | ✅ | 3-5 条关键发现 |
| limitations | string | ⚠️ | 局限性简述 |
| relevance_to_RQ | dict | ✅ | 每个 RQ 的相关性评分 (1-5) |
| citation_count | int | ⚠️ | 引用数 |
| classification_tags | string[] | ✅ | 分类标签（用于 Write 阶段的主题组织） |

标注 ⚠️ 的字段：如果数据源未返回，标注为 "unknown"，**禁止猜测**。

---

## 5. 积极 offload 与冷却规则

为防止上下文溢出（80-120 篇论文的元数据可能超过 token 预算），执行以下冷却策略：

### 处理完每批搜索或子智能体后：
1. **保留**：结构化元数据 JSON（每篇约 250 token）
2. **丢弃**：原始搜索结果、完整摘要文本、中间推理过程
3. **立即落盘**：将每个子主题追加到 `explore/explore.tex`（或先写入 `explore/topics/[TOPIC_SLUG].tex` 后合并），将引用写入 `explore/references.bib`，将全局去重清单写入 `explore/papers.json`，从上下文中移除
4. **记录**：将检索式、来源、返回数、筛选数和缺口写入 `explore/explore.tex` 的 Search Log 章节
5. **综合**：每批合并后更新 `explore/explore.tex` 中的 Literature Matrix 和 Evidence Convergence Summary 章节
6. **路径回填**：在对话上下文中只保留文件路径、论文计数、RQ 覆盖度和当前缺口，不保留长摘要或原始列表

### 进入 Write 阶段前：
- 上下文中仅保留：`scope/article-outline.md` 和 `scope/writing-plan.md` 的摘要 + Background Brief + 论文元数据摘要表 + evidence-convergence 摘要（每篇 1 行：id, title, year, tags, mechanism_view, mechanism_stance, evidence_strength, RQ relevance）
- 完整 Explore 内容从 `.tex + .bib` 文件中按需读取；`papers.json` 仅作索引和计数使用

---

## 6. 门控条件检查

Phase 2 完成后，逐项检查：

| 条件 | 检查方法 | 未通过时处理 |
|------|---------|------------|
| 论文数 ≥ 目标 80% | 统计去重后的论文总数 | 扩大搜索关键词或放宽时间窗口，启动补充搜索 |
| 每个 RQ ≥ 5 篇相关论文 | 检查 relevance_to_RQ ≥ 3 的论文数 | 针对覆盖不足的 RQ 启动定向搜索 |
| 引用网络 ≥ 3 种子 | 统计已完成双向引用网络遍历的种子数 | 补充执行 |
| 证据矩阵已生成 | 检查 `explore/explore.tex` 的 Literature Matrix 章节覆盖所有核心机制观点，并且引用 key 存在于 `explore/references.bib` | 补齐 stance 标注、引用或调整机制观点 |
| 证据收敛已生成 | 检查 `explore/explore.tex` 的 Evidence Convergence Summary 章节至少包含 Strong/Moderate/Weak/Contested/Gap 状态之一 | 重新综合证据矩阵 |
| Explore BibTeX 已生成 | 检查 `explore/references.bib` 存在，且覆盖 Explore `.tex` 文件中所有引用 key | 补充或修复 BibTeX 条目 |

**所有条件通过后**，向用户报告搜集结果摘要（论文总数、各 RQ 覆盖度、主要来源分布），然后进入 Phase 3。

**如果补充搜索后仍未通过**，向用户报告缺口，建议调整 Article Outline + Writing Outline（缩小范围、重排章节或修改 RQ），回退到 Phase 1，并同步更新 `scope/article-outline.md` 和 `scope/writing-plan.md`。
