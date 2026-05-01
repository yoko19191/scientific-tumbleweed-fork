# 质量验收清单

本文件在 Phase 4 (Polish) 开始时加载，用于系统性验收综述质量。

---

## A. 结构完整性

- [ ] **摘要**：存在且 ≤ 250 词，涵盖目的、方法、主要发现、结论
- [ ] **Introduction**：遵循 7 段漏斗结构（Background → Field → Mini Review → Significance → RQs → Contribution → Overview）
- [ ] **However Test**：Introduction 的 mini lit review 部分有清晰的 "however" 转折
- [ ] **1大2小3个点**：大背景扎实、小领域+小综述清晰、出发点/独创点/贡献点完整
- [ ] **Methodology 章节**：记录了搜索策略（数据库、关键词、时间窗口、纳入/排除标准、论文数量）
- [ ] **Synthesis Blueprint**：`synthesis-blueprint.md` 存在，并包含核心机制、证据簇、矛盾解析、CER 链、反方压力测试和章节证据分配
- [ ] **主题章节**：每个主题章节有 ≥1 个对比表格
- [ ] **Discussion**：跨主题综合分析，识别共识/矛盾/空白/未来方向
- [ ] **Conclusion**：逐一回应每个 RQ
- [ ] **目录**：`\tableofcontents` 正确生成

## B. 引用完整性

- [ ] **引用总数**：≥ Article Outline + Writing Outline 中目标引用数的 80%
- [ ] **无孤立引用**：每个 `\cite{key}` / `\citep{key}` / `\citet{key}` 在 `.bib` 中有对应条目
- [ ] **无孤立条目**：`.bib` 中每个条目在 `.tex` 中至少被引用一次
- [ ] **无重复 key**：BibTeX key 全局唯一
- [ ] **Entry type 正确**：期刊论文用 `@article`，会议论文用 `@inproceedings`，预印本用 `@misc`
- [ ] **无捏造元数据**：所有 author/year/venue/doi 字段来自可信学术数据源或原始论文，未知字段省略而非编造
- [ ] **元数据验证**：至少对 50% 的条目通过可信学术数据源进行了交叉验证

## C. 写作质量

- [ ] **无列举反模式**：没有连续 3+ 句以作者名开头的段落
- [ ] **机制观点驱动**：每个主题章节围绕机制主张、因果链或解释框架组织，而不是按论文逐篇堆砌
- [ ] **CER 链完整**：每个主题章节至少对应 1 条 Claim-Evidence-Reasoning 链，且正文使用了该链
- [ ] **证据强度明确**：关键主张说明了证据类型、证据强度、分歧来源或边界条件
- [ ] **矛盾处理充分**：Contested 证据被解释为方法、样本、时间、场景或理论差异，而不是简单并列
- [ ] **反方压力测试已吸收**：正文至少回应一个 strongest counter-argument，并修正或限定可能过度推论的主张
- [ ] **However Test（全文）**：每个主题章节至少有一处清晰的批判性转折
- [ ] **Hedging 语言**：未完整阅读的论文用 "reportedly"/"according to the abstract"；无统计支撑的比较用 "appears to"/"suggests that"
- [ ] **无谄媚语言**：没有 "groundbreaking"/"revolutionary"/"clearly proves" 等绝对化表述
- [ ] **段落结构**：正文段落遵循 机制主张→证据簇→证据评估→边界条件→过渡 五层结构
- [ ] **过渡连贯**：章节之间和段落之间有逻辑连接词（however/furthermore/in contrast/building upon）
- [ ] **术语一致**：同一概念全文使用统一术语，首次出现时给出定义
- [ ] **无内部过程痕迹**：正文和 Methodology 不出现 agent、subagent、prompt、tool call、内部函数名等内部执行痕迹
- [ ] **作者正确**：默认作者为 `Scientific Tumbleweed`

## D. LaTeX 质量

- [ ] **编译通过**：`pdflatex → bibtex → pdflatex ×2` 无错误（或已提供编译说明）
- [ ] **表格规范**：所有表格使用 `booktabs` 风格（`\toprule`/`\midrule`/`\bottomrule`）
- [ ] **表格引用**：每个表格在正文中被 `Table~\ref{tab:...}` 引用
- [ ] **超链接**：`hyperref` 配置正确，链接可点击
- [ ] **无 overfull/underfull 警告**：检查 `.log` 文件中的排版警告
- [ ] **编码正确**：特殊字符（重音符号、非 ASCII 字符）正确转义

## E. 综合评分（三重质检 Gate C）

由三个审阅视角分别评分（0-100），总分取平均值，**≥ 80 分方可通过**：

### 领域专家视角
- 主题覆盖是否全面？是否遗漏了重要方向？
- 分类体系是否合理？
- 对各方法/理论的描述是否准确？

### 方法论批评者视角
- 搜索策略是否可复现？
- 纳入/排除标准是否清晰？
- 综合分析是否有逻辑支撑？

### 写作质量审阅者视角
- 行文是否流畅？
- 论证层次是否清晰？
- 是否有冗余或遗漏？

### 评分与处置

| 总分 | 处置 |
|------|------|
| ≥ 80 | 通过，进入 Deliver |
| 60-79 | 识别最弱维度，针对性修订后重新评分 |
| < 60 | 回退到 Write 阶段，重写最弱章节 |

**退化检测**：如果修订后某维度分数反而下降，标记为退化，优先修复该维度。

## F. 协作质量与独立验证

- [ ] **Scope 文件完整**：`scope/article-outline.md` 和 `scope/writing-plan.md` 存在，且内容与用户确认的 Article Outline + Writing Outline 一致
- [ ] **Outline 一致性**：最终论文回应了 `scope/article-outline.md` 和 `scope/writing-plan.md` 中确认后的 RQ、章节结构、时间窗口、排除条件和写作策略
- [ ] **背景预调研使用充分**：Introduction、Background 和 Discussion 吸收了 `explore/explore.tex` 中 Background Brief 章节的领域脉络、机制线索和证据张力
- [ ] **Explore offload 完整**：`explore/` 下存在 `explore.tex`、`references.bib` 和全局 `papers.json`；`explore.tex` 包含 Background Brief、Search Log、Topic Notes、Literature Matrix、Evidence Convergence Summary 和 Knowledge Gaps 等章节
- [ ] **Explore 引用完整**：Explore `.tex` 文件中的每个 citation key 都在 `explore/references.bib` 中有对应条目，并能被后续主 `references.bib` 合并复用
- [ ] **证据综合链路完整**：`explore/explore.tex` 中的 Literature Matrix 和 Evidence Convergence Summary → `synthesis-blueprint.md` → `survey.tex` 的论证链可追溯
- [ ] **写作约束一致**：最终论文遵守默认英文、机制观点驱动、证据强度明确、无内部过程痕迹、默认作者正确等约束
- [ ] **修订闭环清晰**：Scope 文件、Gate A-C、`paper-review` 或独立子智能体发现的问题均已修复或明确记录为不影响交付的 Minor issue
- [ ] **paper-review 通过**：文章完成后由 `paper-review` 完成学术审阅，结论为通过或仅有不阻塞交付的 Minor issues
- [ ] **独立子智能体评估通过**：文章完成后由独立子智能体基于本清单完成评估，结论为 `PASS`，且无 Critical issues
