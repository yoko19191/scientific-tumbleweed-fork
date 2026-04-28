# 质量验收清单

本文件在 Phase 4 (Polish) 开始时加载，用于系统性验收综述质量。

---

## A. 结构完整性

- [ ] **摘要**：存在且 ≤ 250 词，涵盖目的、方法、主要发现、结论
- [ ] **Introduction**：遵循 7 段漏斗结构（Background → Field → Mini Review → Significance → RQs → Contribution → Overview）
- [ ] **However Test**：Introduction 的 mini lit review 部分有清晰的 "however" 转折
- [ ] **1大2小3个点**：大背景扎实、小领域+小综述清晰、出发点/独创点/贡献点完整
- [ ] **Methodology 章节**：记录了搜索策略（数据库、关键词、时间窗口、纳入/排除标准、论文数量）
- [ ] **主题章节**：每个主题章节有 ≥1 个对比表格
- [ ] **Discussion**：跨主题综合分析，识别共识/矛盾/空白/未来方向
- [ ] **Conclusion**：逐一回应每个 RQ
- [ ] **目录**：`\tableofcontents` 正确生成

## B. 引用完整性

- [ ] **引用总数**：≥ Scope Card 中目标数量的 80%
- [ ] **无孤立引用**：每个 `\cite{key}` / `\citep{key}` / `\citet{key}` 在 `.bib` 中有对应条目
- [ ] **无孤立条目**：`.bib` 中每个条目在 `.tex` 中至少被引用一次
- [ ] **无重复 key**：BibTeX key 全局唯一
- [ ] **Entry type 正确**：期刊论文用 `@article`，会议论文用 `@inproceedings`，预印本用 `@misc`
- [ ] **无捏造元数据**：所有 author/year/venue/doi 字段来自 API 返回或原始论文，未知字段省略而非编造
- [ ] **API 验证**：至少对 50% 的条目通过 `academic_get_bibtex` 进行了交叉验证

## C. 写作质量

- [ ] **无列举反模式**：没有连续 3+ 句以作者名开头的段落
- [ ] **However Test（全文）**：每个主题章节至少有一处清晰的批判性转折
- [ ] **Hedging 语言**：未完整阅读的论文用 "reportedly"/"according to the abstract"；无统计支撑的比较用 "appears to"/"suggests that"
- [ ] **无谄媚语言**：没有 "groundbreaking"/"revolutionary"/"clearly proves" 等绝对化表述
- [ ] **段落结构**：正文段落遵循 主题句→证据→分析→过渡 四层结构
- [ ] **过渡连贯**：章节之间和段落之间有逻辑连接词（however/furthermore/in contrast/building upon）
- [ ] **术语一致**：同一概念全文使用统一术语，首次出现时给出定义

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
