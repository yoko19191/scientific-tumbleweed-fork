# LaTeX 模板说明

本文件在 Phase 3 (Write) 生成 `.tex` 文件时加载，提供 LaTeX 文档骨架和常用组件模板。基础模板只固定排版环境、作者和 Abstract 容器；除 Abstract 与作者外，不硬编码任何章节结构。

---

## 1. 模板文件位置

基础模板位于 `templates/survey-template.tex`，Write 阶段应：
1. 将模板复制到输出目录
2. 替换所有 `%PLACEHOLDER%` 占位符为实际内容
3. 同步生成 `references.bib`
4. 所有章节标题、章节顺序和正文内容都由 `scope/article-outline.md`、`scope/writing-plan.md` 与 Write 阶段生成，不在模板中预置。

## 2. 占位符替换规则

| 占位符 | 替换内容 | 来源 |
|--------|---------|------|
| `%SURVEY_TITLE%` | 综述标题 | Article Outline + Writing Outline |
| 作者行 | 固定为 `Scientific Tumbleweed` | 模板默认 |
| `%DATE%` | 生成日期 `\today` 或具体日期 | 系统日期 |
| `%ABSTRACT%` | 摘要（≤250 词） | Write 阶段生成 |
| `%BODY%` | Abstract 之后、bibliography 之前的全部正文，包括所有章节 | 按 `scope/article-outline.md` 和 `scope/writing-plan.md` 动态生成 |

模板不得包含硬编码的 `\section{Introduction}`、`\section{Survey Methodology}`、`\section{Discussion}` 等章节。若文章需要这些章节，由 `%BODY%` 的生成内容提供。

### 兼容性约定

- 模板优先使用 `newpxtext/newpxmath`；如果运行环境缺少该字体包，会自动回退到 `lmodern`。
- 已声明常见科学 Unicode 字符（如 α/β/γ/μ/Δ/λ/≤/≥/±/×），但正文仍优先使用 LaTeX 数学命令以保证可移植性。
- 已加载 `xurl` 并设置 `\urlstyle{same}`，长 URL/DOI 更容易换行。
- 已定义 `Y` 列类型：`>{\raggedright\arraybackslash}X`。复杂表格优先用 `Y` 代替裸 `X`，提升可读性并减少 overfull。
- 已设置 `\graphicspath{{figures/}{assets/}{images/}}`，图片默认放入这些目录之一。
- `%BODY%` 只能包含正文级 LaTeX（章节、段落、表格、图片、引用等），不要再次写入 `\documentclass`、`\usepackage`、`\bibliographystyle` 或 `\bibliography`。

## 3. 对比表格模板

所有表格使用 `booktabs` 风格，禁止使用竖线 `|`。默认优先比较机制观点和证据质量，而不是罗列论文内容：

```latex
\begin{table}[H]
\centering
\caption{Comparison of representative methods for [TOPIC].}
\label{tab:comparison_topic}
\begin{tabularx}{\textwidth}{lYllY}
\toprule
\textbf{Mechanism View} & \textbf{Evidence Type} & \textbf{Strength} & \textbf{Boundary Conditions} & \textbf{Representative Sources} \\
\midrule
X influences Y through Z & Experimental benchmark & Moderate & Strongest in large-scale settings & \citet{author2023method,author2024method} \\
\bottomrule
\end{tabularx}
\end{table}
```

### 表格设计原则
- 列数 ≤ 6（超过时拆分为多个表格或使用 landscape）
- 第一列为机制观点，最后一列为代表性来源
- 数值列右对齐，文本列左对齐
- 每个表格必须在正文中被 `Table~\ref{tab:...}` 引用

## 4. 总结框模板

每个主题章节末尾可选添加 Key Findings 框：

```latex
\begin{keyfindings}
\begin{itemize}[nosep]
  \item Finding 1: ...
  \item Finding 2: ...
  \item Research gap: ...
\end{itemize}
\end{keyfindings}
```

研究空白汇总使用 Research Gap 框：

```latex
\begin{researchgap}
\begin{itemize}[nosep]
  \item Gap 1: ...
  \item Gap 2: ...
\end{itemize}
\end{researchgap}
```

## 5. 引用命令使用规范

| 命令 | 渲染效果 | 使用场景 |
|------|---------|---------|
| `\citep{key}` | [1] 或 (Author, Year) | 括号引用，放在句末 |
| `\citet{key}` | Author [1] 或 Author (Year) | 文本引用，作者名作为句子成分 |
| `\citep{k1,k2,k3}` | [1-3] | 多篇引用，natbib 自动压缩 |
| `\citeauthor{key}` | Author | 仅作者名 |
| `\citeyear{key}` | Year | 仅年份 |

### 引用位置规则
- 句末引用：`...as demonstrated in recent work \citep{a2023,b2024}.`
- 句中引用：`\citet{vaswani2017} introduced the Transformer architecture.`
- 禁止：`[1] proposed...`（数字引用不能做主语，用 `\citet{}` 代替）

## 6. BibTeX 条目规范

### 期刊论文
```bibtex
@article{author2024title,
  author    = {LastName, FirstName and LastName2, FirstName2},
  title     = {Paper Title},
  journal   = {Journal Name},
  year      = {2024},
  volume    = {10},
  number    = {3},
  pages     = {100--115},
  doi       = {10.xxxx/xxxxx}
}
```

### 会议论文
```bibtex
@inproceedings{author2024title,
  author    = {LastName, FirstName and LastName2, FirstName2},
  title     = {Paper Title},
  booktitle = {Proceedings of Conference Name},
  year      = {2024},
  pages     = {100--115},
  doi       = {10.xxxx/xxxxx}
}
```

### 预印本（arXiv）
```bibtex
@misc{author2024title,
  author        = {LastName, FirstName and LastName2, FirstName2},
  title         = {Paper Title},
  year          = {2024},
  eprint        = {2401.12345},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  url           = {https://arxiv.org/abs/2401.12345}
}
```

### BibTeX Key 生成规则
- 格式：`<第一作者姓小写><年份><标题第一个实词小写>`
- 示例：`vaswani2017attention`、`devlin2019bert`
- 冲突时追加字母后缀：`smith2024deep`, `smith2024deepb`

## 7. 中文输出适配

如果用户在 Scope 阶段选择中文输出：

1. 将 `\documentclass[11pt,a4paper]{article}` 替换为 `\documentclass[11pt,a4paper]{ctexart}`
2. 删除 `\usepackage[english]{babel}` 行
3. 删除 `\usepackage[utf8]{inputenc}` 和 `\usepackage[T1]{fontenc}` 行（ctexart 自带）
4. 编译命令从 `pdflatex` 改为 `xelatex`
5. `\bibliographystyle` 可改为 `gbt7714-numerical`（如果安装了 gbt7714 包）

编译命令变为：
```bash
xelatex -interaction=nonstopmode survey.tex && \
bibtex survey && \
xelatex -interaction=nonstopmode survey.tex && \
xelatex -interaction=nonstopmode survey.tex
```
