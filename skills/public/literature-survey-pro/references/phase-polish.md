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

对至少 50% 的 BibTeX 条目，使用 `academic_get_bibtex` 进行交叉验证：
- 比对 title、authors、year、venue 是否与 API 返回一致
- 发现不一致时以 API 数据为准进行修正
- 对于 API 无法验证的条目（如灰色文献），保留但标注来源

### Step 4: Entry type 检查

- 有 `journal` 字段 → 应为 `@article`
- 有 `booktitle` 字段 → 应为 `@inproceedings`
- 有 `eprint` + `archivePrefix=arXiv` → 应为 `@misc`
- 类型不匹配时修正

---

## 2. LaTeX 编译

### 编译命令（英文输出）

```bash
cd /mnt/user-data/outputs/survey-<slug>-<date>/ && \
pdflatex -interaction=nonstopmode survey.tex && \
bibtex survey && \
pdflatex -interaction=nonstopmode survey.tex && \
pdflatex -interaction=nonstopmode survey.tex
```

### 编译命令（中文输出）

```bash
cd /mnt/user-data/outputs/survey-<slug>-<date>/ && \
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
- 唯一引用数 ≥ Scope Card 目标的 80%
- 表格数 ≥ 2
- 每个 RQ 在 Introduction 和 Conclusion 中都被提及

### Gate B: 学术诚信

逐项检查：

1. **无捏造元数据**：抽查 10 个 BibTeX 条目，验证 title/year 与 `academic_get_bibtex` 返回一致
2. **无孤立引用/条目**：Step 1-2 的交叉比对已通过
3. **无重复 key**：`.bib` 中无重复条目
4. **引用诚实**：搜索 `reportedly`、`according to` 等 hedging 标记，确认用于正确场景
5. **无 [需补充] 残留**：搜索 LaTeX 注释中的 `[需补充]` 标记，全部处理完毕

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
- 评分标准：流畅度(30%) + 结构(30%) + 无反模式(20%) + 过渡质量(20%)

**总分 = 三个视角的平均分**

| 总分 | 处置 |
|------|------|
| ≥ 80 | 通过，进入 Deliver |
| 60-79 | 识别最弱维度，针对性修订后重新评分（最多 2 轮） |
| < 60 | 回退到 Phase 3，重写最弱章节 |

**退化检测**：如果修订后某维度分数反而下降，优先修复该维度，禁止忽略。

---

## 4. 编译降级方案

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

2. 仍然通过 `present_files` 呈现 `.tex` + `.bib` 文件

---

## 5. 门控条件总检

Phase 4 完成的最终检查清单：

- [ ] 引用交叉验证通过（无孤立引用/条目）
- [ ] BibTeX 元数据验证通过（≥50% 条目经 API 验证）
- [ ] LaTeX 编译通过（或已提供降级方案）
- [ ] Gate A 物理计数通过
- [ ] Gate B 学术诚信通过
- [ ] Gate C 多视角审阅总分 ≥ 80

**全部通过后**，进入 Phase 5 (Deliver)。
