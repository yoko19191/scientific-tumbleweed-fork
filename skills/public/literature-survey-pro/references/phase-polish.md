# Phase 4: Polish — 质检与编译

本文件在 Phase 4 开始时加载。目标：验证文档质量，修复问题，编译 PDF，呈现给用户。

> **门控条件**：质量清单（`quality-checklist.md`）全部通过后才能进入 Deliver。

---

## 1. 引用交叉验证

### Step 1: 提取所有引用 key

从 `survey.tex` 中提取所有 `\cite{}`、`\citep{}`、`\citet{}` 中的 key：

```bash
grep -oP '\\cite[pt]?\{[^}]+\}' survey.tex | \
  grep -oP '[a-zA-Z0-9_]+' | sort -u > cite_keys.txt
```

从 `references.bib` 中提取所有条目 key：

```bash
grep -oP '@\w+\{([^,]+),' references.bib | \
  grep -oP '\{(.+),' | sed 's/[{,]//g' | sort -u > bib_keys.txt
```

### Step 2: 交叉比对

- **孤立引用**（.tex 中有但 .bib 中无）：必须补充 .bib 条目
- **孤立条目**（.bib 中有但 .tex 中未引用）：删除或在正文中补充引用
- **重复 key**：修复为唯一 key

### Step 3: 元数据验证

对至少 50% 的 BibTeX 条目，使用可用的学术元数据来源进行交叉验证：
- 比对 title、authors、year、venue 是否与数据源返回一致
- 发现不一致时以可信学术数据源或论文原始页面为准进行修正
- 对于无法验证的条目（如灰色文献），保留但标注来源

### Step 4: Entry type 检查

- 有 `journal` 字段 → 应为 `@article`
- 有 `booktitle` 字段 → 应为 `@inproceedings`
- 有 `eprint` + `archivePrefix=arXiv` → 应为 `@misc`
- 类型不匹配时修正

---

## 2. LaTeX 编译

### 编译命令（英文输出）

```bash
cd "survey+{title}+{version}/" && \
pdflatex -interaction=nonstopmode survey.tex && \
bibtex survey && \
pdflatex -interaction=nonstopmode survey.tex && \
pdflatex -interaction=nonstopmode survey.tex
```

### 编译命令（中文输出）

```bash
cd "survey+{title}+{version}/" && \
xelatex -interaction=nonstopmode survey.tex && \
bibtex survey && \
xelatex -interaction=nonstopmode survey.tex && \
xelatex -interaction=nonstopmode survey.tex
```

### 编译结果处理

| 情况 | 处理 |
|------|------|
| 编译成功，无错误 | 继续质检 |
| 编译成功，有警告 | 检查 `.log` 中的 overfull/underfull 警告，尝试修复严重的排版问题 |
| 编译失败，错误可修复 | 解析 `.log` 中的错误信息，修复 `.tex` 后重新编译（最多重试 3 次） |
| 编译失败，pdflatex/xelatex 不可用 | 优雅降级：跳过 PDF 生成，在 Deliver 阶段提供编译说明 |
| bibtex 失败 | 检查 `.blg` 文件，修复 `.bib` 中的语法错误后重试 |

### 常见编译错误修复

| 错误 | 原因 | 修复 |
|------|------|------|
| `Undefined control sequence` | 缺少宏包或拼写错误 | 检查 `\usepackage` 列表 |
| `Missing $ inserted` | 正文中出现未转义的 `_` 或 `%` | 转义为 `\_` 或 `\%` |
| `Citation undefined` | .bib 中缺少条目 | 回到 Step 1 补充 |
| `I found no \bibstyle command` | 缺少 `\bibliographystyle` | 检查模板完整性 |
| `Package inputenc Error` | 非 UTF-8 字符 | 转义特殊字符 |

---

## 3. 三重质检

加载 `quality-checklist.md`，依次执行三道质检门禁。

### Gate A: 物理计数

使用 bash 命令进行客观计量，**禁止目测估算**：

```bash
# 统计引用数
grep -oP '\\cite[pt]?\{[^}]+\}' survey.tex | wc -l

# 统计唯一引用 key 数
grep -oP '\\cite[pt]?\{[^}]+\}' survey.tex | \
  grep -oP '[a-zA-Z0-9_]+' | sort -u | wc -l

# 统计表格数
grep -c '\\begin{table}' survey.tex

# 统计章节数
grep -c '\\section{' survey.tex

# 统计总字数（近似）
detex survey.tex 2>/dev/null | wc -w || \
  sed 's/\\[a-zA-Z]*{[^}]*}//g; s/\\[a-zA-Z]*//g' survey.tex | wc -w
```

**检查项**：
- 唯一引用数 ≥ Article Outline + Writing Outline 中目标引用数的 80%
- 表格数 ≥ 2
- 每个 RQ 在 Introduction 和 Conclusion 中都被提及

### Gate B: 学术诚信

逐项检查：

1. **无捏造元数据**：抽查 10 个 BibTeX 条目，验证 title/year 与可信学术数据源或论文原始页面一致
2. **无孤立引用/条目**：Step 1-2 的交叉比对已通过
3. **无重复 key**：`.bib` 中无重复条目
4. **引用诚实**：搜索 `reportedly`、`according to` 等 hedging 标记，确认用于正确场景
5. **无 [需补充] 残留**：搜索 LaTeX 注释中的 `[需补充]` 标记，全部处理完毕
6. **无内部过程痕迹**：正文和 Methodology 不出现 agent、subagent、prompt、tool call 或内部工具函数名

### Gate C: 多视角审阅

切换为三种审阅视角，分别评分（0-100）：

**视角 1 — 领域专家**：
- 主题覆盖是否全面？是否遗漏重要方向？
- 分类体系是否合理？
- 对各方法/理论的描述是否准确？
- 评分标准：覆盖度(40%) + 准确性(30%) + 分类合理性(30%)

**视角 2 — 方法论批评者**：
- 搜索策略是否可复现？
- 纳入/排除标准是否清晰？
- 综合分析是否有逻辑支撑？
- 评分标准：可复现性(40%) + 逻辑严密性(40%) + 透明度(20%)

**视角 3 — 写作质量审阅者**：
- 行文是否流畅？
- 论证层次是否清晰？
- 是否有冗余或遗漏？
- 反模式检测是否通过？
- 是否围绕机制观点和证据强度展开，而不是内容堆砌？
- 评分标准：流畅度(25%) + 结构(25%) + 机制/证据综合(25%) + 无反模式(15%) + 过渡质量(10%)

**总分 = 三个视角的平均分**

| 总分 | 处置 |
|------|------|
| ≥ 80 | 通过，进入 Deliver |
| 60-79 | 识别最弱维度，针对性修订后重新评分（最多 2 轮） |
| < 60 | 回退到 Phase 3，重写最弱章节 |

**退化检测**：如果修订后某维度分数反而下降，优先修复该维度，禁止忽略。

---

## 4. Gate D: paper-review + 独立子智能体评估

文章完成、Gate A-C 自检通过后，必须完成两类外部评估。主写作上下文不得替代这些评估。

### 调度要求

- 评估 1：使用 `paper-review` 对成稿进行学术论文审阅，重点检查论证质量、贡献表述、结构、写作质量和潜在学术风险。
- 评估 2：派发一个独立子智能体进行质量清单复核。不要硬编码具体子智能体类型名称，只要求其独立读取文件、独立评估并输出结论。
- 输入文件：`survey.tex`、`references.bib`、`scope/article-outline.md`、`scope/writing-plan.md`、`synthesis-blueprint.md`、`explore/explore.tex`、`explore/papers.json`、`explore/references.bib`、`quality-checklist.md`
- `paper-review` 评估依据：成稿学术质量、论证完整性、文献覆盖、贡献清晰度和投稿风险。
- 独立子智能体评估依据：完整执行 `quality-checklist.md` 的 A-F 部分。
- 综合评估目标：综述质量、证据质量、机制观点综合、引用诚信、LaTeX 质量，以及协作质量。

### 独立子智能体 Prompt 模板

```text
你是独立质量审阅者。请不要延续写作者的自评结论。

请读取 survey.tex、references.bib、scope/article-outline.md、scope/writing-plan.md、
synthesis-blueprint.md、explore/explore.tex、explore/papers.json、explore/references.bib
和 quality-checklist.md，基于 checklist 的 A-F 部分独立评估：

1. 每个 checklist 项是否通过，并给出证据位置或失败原因。
2. 文章是否围绕机制观点和证据强度组织，而不是论文内容堆砌。
3. `explore/explore.tex`、`explore/references.bib`、`synthesis-blueprint.md` 与正文之间是否可追溯，尤其是 Literature Matrix 和 Evidence Convergence Summary 两个章节。
4. `synthesis-blueprint.md` 的 Devil's Advocate Stress Test 是否被正文吸收，尤其是 strongest counter-argument 和过度推论风险。
5. Methodology 是否像研究者的文献筛选说明，且无 agent/tool/prompt 等内部过程痕迹。
6. 引用、BibTeX、RQ 覆盖和表格是否满足门控。
7. 协作质量：`scope/article-outline.md`、`scope/writing-plan.md`、Background Brief、explore offload、写作约束和最终输出是否一致。

输出：
- Verdict: PASS 或 FAIL
- Checklist summary: A-F 各部分通过率
- Critical issues: 必须修复的问题
- Minor issues: 可选改进
- Evidence notes: 支撑结论的简短证据
```

### 通过条件

- `paper-review` 结论为通过或仅有不阻塞交付的 Minor issues
- 独立子智能体输出 `Verdict: PASS`
- 两类评估均无 Critical issues
- `quality-checklist.md` 的 A-F 部分全部通过，或只有明确说明不影响交付的 Minor issues

若任一外部评估返回 `FAIL`：
1. 修复 Critical issues。
2. 重新运行相关 Gate A-C。
3. 再次运行 `paper-review` 或独立子智能体复评（只重跑失败的评估即可）。
4. 最多复评 2 轮；仍失败则停止交付并向用户报告阻塞原因。

---

## 5. 编译降级方案

如果 sandbox 环境中 `pdflatex`/`xelatex` 不可用：

1. 在 Deliver 阶段的聊天消息中附上编译说明：

```
本综述已生成为 LaTeX 源文件。编译 PDF 的方法：

方法 1 — Overleaf（推荐）：
  1. 上传 survey.tex 和 references.bib 到 Overleaf
  2. 设置编译器为 pdflatex（英文）或 XeLaTeX（中文）
  3. 点击 Compile

方法 2 — 本地编译：
  pdflatex survey.tex && bibtex survey && pdflatex survey.tex && pdflatex survey.tex

方法 3 — Docker：
  docker run --rm -v $(pwd):/work texlive/texlive:latest \
    sh -c "cd /work && pdflatex survey.tex && bibtex survey && pdflatex survey.tex && pdflatex survey.tex"
```

2. 在交付消息中呈现 `.tex` + `.bib` 文件路径

---

## 6. 门控条件总检

Phase 4 完成的最终检查清单：

- [ ] 引用交叉验证通过（无孤立引用/条目）
- [ ] BibTeX 元数据验证通过（≥50% 条目经可信学术数据源验证）
- [ ] LaTeX 编译通过（或已提供降级方案）
- [ ] Gate A 物理计数通过
- [ ] Gate B 学术诚信通过
- [ ] Gate C 多视角审阅总分 ≥ 80
- [ ] Gate D 的 `paper-review` 评估通过（无 Critical issues）
- [ ] Gate D 的独立子智能体评估通过（Verdict: PASS，无 Critical issues）
- [ ] `scope/article-outline.md` 和 `scope/writing-plan.md` 已生成并被用于 Explore、Write 和独立评估
- [ ] `explore/explore.tex`、`explore/references.bib` 和 `synthesis-blueprint.md` 均已生成并被独立子智能体检查
- [ ] 正文无智能体、prompt、内部工具调用等过程痕迹
- [ ] 默认作者为 `Scientific Tumbleweed`

**全部通过后**，进入 Phase 5 (Deliver)。
