# Scientific Tumbleweed — Landing Page 内容与设计说明

> 本文档指导官方落地页（`/`）的内容与视觉。
> 读者：前端工程师、设计师、文案作者。
> 风格基准：[phylo.bio](https://phylo.bio/) 的克制与留白。
> 视觉系统：`docs/DESIGN.md` 的 Scientific Tumbleweed Lab。

---

## 一、落地页的一件事

> **在用户看完一屏之内，让他说得出："这东西能帮我做什么、为什么比 ChatGPT 强。"**

其它都是次要。落地页不是商业计划书，不是产品文档，不是综述。
它是一个销售：10 秒钟内把产品讲清楚。

---

## 二、顶部导航

固定顶部，横向排列：

```
[Logo  Scientific Tumbleweed]   Product   Use Case   Research   Blog   Pricing   About     [ Try it now → ]
```

- **Logo**：左上角。点击回到首页。
- **Product**：产品功能总览——沙箱、数据源、agent 行为、集成生态（指向 `/product`）。
- **Use Case**：真实使用场景集合（详见第六章）。
- **Research**：技术博客性质的长文、论文、对比评测、benchmark。
- **Blog**：产品更新、社区故事、版本说明。
- **Pricing**：套餐与计费（Starter / Team / Enterprise，**当前为占位**，具体由商务确认）。
- **About**：产品理念、团队、公司背景。
- **CTA 按钮**：右上角橙色实心按钮 `Try it now →`，始终可见。

导航项顺序的设计意图：`Product` 放在最左，让访问者第一眼就能跳进产品说明页；`Pricing` 与 `About` 放在靠右，作为"已经想清楚再看"的选项。

移动端折叠为汉堡菜单，CTA 独立保留在右上。

---

## 三、Hero（首屏）

**唯一任务**：让人在 3 秒看懂、在 10 秒决定继续滚动。

### 3.1 英文版（默认主版本）

**Headline（大字）**
> **Agentic Biomedical Research Workbench**  <sup class="badge">AI Native</sup>

**Subheadline（一行）**
> Collaborative AI for biologists to make more effective discovery.

**两枚 CTA**
- 主按钮（橙色实心）：`Try it now →`
- 次按钮（文字链）：`Read our vision`

### 3.2 中文版

**Headline**
> **智能体生物医学研究工作台**  <sup class="badge">AI Native</sup>

**Subheadline**
> 为生物学家而生的协作式 AI——让科学发现更有效率。

### 3.3 "AI Native" 徽章

- **位置**：Headline 右上角，与大字基线略上方对齐，视觉上像脚注。
- **尺寸**：远小于主标（≈10–11px），不压过大字。
- **样式**：
  - 圆角 `rounded.full`
  - 细边框 `1px solid currentColor`，透明度 60%
  - 字体 `IBM Plex Mono` / `JetBrains Mono`
  - `letter-spacing: 0.18em`，全大写：`AI NATIVE`
  - 不带背景色，保持 Hero 整体气质
- **行为**：非可点击装饰元素（不加链接、不加 tooltip）。
- **作用**：在不打断主标气势的前提下，给这句话加一层"技术立场声明"——这不是把 LLM 套在旧产品上的皮肤，而是原生为 agent 设计的工作台。

### 3.4 视觉

- 全屏背景：一张有机科学插画（植物 / 细胞 / 分子结构的素描风格，深森林墨绿或冷白背景，对应 DESIGN.md 的 `primary` / `success` 双色调）。
- 主视觉**不要**放产品截图。首屏只做氛围，不做演示。
- 文字居中或左对齐均可，但留白必须铺满两侧至少各 20vw。
- CTA 按钮沿用 `shadows.button` 多层阴影，可按。

### 3.5 不要做的事

- 不要放 "Revolutionary"、"Next-gen"、"AI-powered" 这类词。
- 不要放数字云（60+ 技能、200M 结构这些进后面 section）。
- 不要放三个 CTA。只有两个。
- 不要把 "super agent harness" 这种工程术语放在第一屏。

---

## 四、Section 排布总览

首屏之后，共 8 个 section，从上到下。信息流按"**场景层 → 能力层 → 计算层**"的三层叙事展开：读者先看到自己的工作被怎么解决（场景），再看到背后挂了多少数据与工具（能力），最后才看到跑它们的底层（计算）。差异化、方法论、信任与 CTA 分别收尾。

```
1. Hero                                 — 一句话 + CTA（含 AI Native 徽章）
2. The Workbench                        — 一段话定义（Integrated Biology Environment）
3. Scenario Layer    · 场景层           — 生物学家真正会问的问题
4. Capability Layer  · 能力层           — 数据源 / 文献 / 组学分析的规模
5. Compute Layer     · 计算层           — 沙箱 + 智能体协同（agent 层作为计算层的协作者）
6. How it's different                   — vs 通用 AI 的对照
7. The method                           — 四幕式行业叙事（默认折叠）
8. Trusted                              — 真实可信的社会证明
9. Final CTA                            — 再放一次 Try it now
```

**三层的语义分工（设计时请遵守，不要越层）**：

| 层 | 回答的问题 | 落地页句式 | 不该出现在这一层的东西 |
|---|---|---|---|
| Scenario Layer · 场景层 | "你能帮我做什么？" | 用户自己说的一句话 + agent 会做的事 | 数据源清单、工具名、参数 |
| Capability Layer · 能力层 | "你手上有多少家底？" | 数据库 / 文献 / 组学分析三组数字 | 用户故事、代码 |
| Compute Layer · 计算层 | "这些能力跑在什么上？" | 沙箱命令 + agent 角色协作 | 营销文案、比喻 |

每个 section 不超过一屏高（desktop）。滚动要有节奏，不能让人滚到第三屏还在看产品定义。

---

## 五、Section 逐块规范

### Section 2 — The Workbench（一段话定义）

**目标**：用一段话告诉访问者这是什么。承接 Hero 的 slogan，给整个页面一个锚。
这一节**不做小标题**，不展开产品功能，展开留给后面三层。

**Headline**
> **The Workbench, defined.**

中文版：
> **一句话说清这个工作台。**

**正文（一段，≤3 句）**
> One chat window. 50+ life-science databases wired up. A full bioinformatics sandbox you can run STAR, scanpy, or AlphaFold in. A team of AI agents that plans, runs, verifies, and writes it up for you.

**视觉**：三个水平排列的图形元素（简约线条风，不是 emoji）：
- `chat bubble` — One conversation
- `database stack` — 50+ data sources
- `terminal / flask` — Real sandbox

保持整段一气呵成。下面是三层分述。

---

### Section 3 — Scenario Layer · 场景层（**最重要的一节**）

**目标**：访问者最想知道的事——**我能拿它做什么**。
这一节的信息密度应该高于其他所有 section，并且**只讲用户视角**：一句话问题 + 一句话产出，不暴露任何工具名或参数。

**Headline**
> **Scenario Layer — the questions biologists actually ask.**

中文版：
> **场景层——生物学家真正会问的问题。**

**副标（一行）**
> Four conversations. Four results you can hand to your PI by tomorrow.

**四个卡片（2×2 或 4 横）**，每张写：一个任务 + 一句用户说的话 + 这背后 agent 会做的事（短，≤3 行）。

---

**Card 1 — Analyze a dataset, end to end**
> *"Pull GSE###### from GEO, run a clean scanpy pipeline, label the clusters, and tell me which look like exhausted T cells."*
>
> Downloads the data, runs the pipeline in the sandbox, annotates against CELLxGENE and Human Protein Atlas, hands back the AnnData and a PDF.

---

**Card 2 — Prioritize a GWAS locus**
> *"I've got a lead SNP at chr9:136155000–136165000 in a T2D meta-analysis. What are the most plausible causal genes?"*
>
> Fans out across GWAS Catalog, GTEx, Open Targets L2G, gnomAD constraint, and Genebass burden — returns a ranked candidate table with every source linked.

---

**Card 3 — Triage a drug-repurposing idea**
> *"Could metformin make sense in pancreatic cancer? Show me the evidence before I waste an afternoon."*
>
> Pulls ChEMBL, Open Targets, cBioPortal, ClinicalTrials.gov, PharmGKB, and the recent literature — produces an evidence-for / against / unknown briefing.

---

**Card 4 — Write the survey, not just search it**
> *"Write me a publication-grade review on CAR-T exhaustion mechanisms."*
>
> Searches Semantic Scholar and PubMed, builds the citation network, drafts the narrative, exports LaTeX + BibTeX, compiles the PDF.

---

**卡片设计**
- 白底卡片（`bg-elevated`），`shadows.card`，hover 时抬起。
- 引号部分用衬线字体，显眼地当"用户说话"。
- 下方解释用 sans。
- 每张卡片左上角有一个 monoline 图标，不用 emoji。

**卡片之外**
卡片下方一行小字（过渡到能力层）：
> Every step is logged. Every citation is clickable. Every run is reproducible — thanks to what's on the next layer down.

---

### Section 4 — Capability Layer · 能力层（**数据源 / 文献 / 组学分析的规模**）

**目标**：让访问者**一眼看到家底**——我们到底接了多少生物数据库、具备什么样的文献搜索能力、能跑多少种组学分析。
这一节是场景层的"资产负债表"：上一屏用户问的问题，全部靠这一屏里的家底兑现。

**Headline**
> **Capability Layer — what's wired into the biology you actually cite.**

中文版：
> **能力层——接进了你真正会引用的那部分生物学。**

**副标（一行）**
> Three columns. Three promises. Each one is a typed, audited interface to a real source — not a web-scrape.

**三列横排（desktop）/ 三段纵排（mobile）**，每列一个大数字 + 一行小标 + 一行解释。

---

**Column 1 — Databases**

> # **50+**
> **Life-science databases, natively integrated.**
>
> Human genetics, variants, expression, proteins, structures, compounds, drugs, pathways, clinical trials — all behind one chat. Each one is a typed, audited skill, not a web-scrape.

**底部徽章行（按领域分组，小号 chip）**：
- *Human genetics:* GWAS Catalog · gnomAD · ClinVar · Ensembl · EVA · Open Targets · eQTL Catalogue · GTEx · Genebass
- *Biobank PheWAS:* FinnGen · UK Biobank-TOPMed · BioBank Japan · TPMI
- *Proteins & structure:* UniProt · AlphaFold DB · RCSB PDB · Human Protein Atlas · STRING · Reactome · Rhea · QuickGO
- *Chemistry & drugs:* ChEMBL · PubChem · ChEBI · BindingDB · PharmGKB · CIViC · cBioPortal · ClinicalTrials.gov
- *Omics references:* CELLxGENE · Bgee · ENCODE · MGnify · PRIDE · ProteomeXchange · MetaboLights · HMDB · RNAcentral · IPD

---

**Column 2 — Literature**

> # **40M+**
> **Papers and preprints, reasoned over — not just searched.**
>
> PubMed, PMC Open Access, bioRxiv, medRxiv, Semantic Scholar citation graph, plus targeted review and survey agents that read, cross-check, and write with citations you can click.

**底部能力条（小号 chip）**：
- `pubmed / entrez search` — 结构化文献检索，按 MeSH / date / journal 过滤
- `pmc open-access fetch` — 取回全文做分段阅读
- `biorxiv / medrxiv` — preprint 与正式发表版本的链接解析
- `semantic-scholar graph` — 引用 / 被引 / 作者 / 推荐关系
- `deep-research` — 多角度循环调研，非单次搜索
- `literature-survey-pro` — 产出 LaTeX + BibTeX 的发表级综述，沙箱里编译 PDF
- `paper-review / academic-paper-review` — 审稿级手稿批阅

---

**Column 3 — Multi-Omics Analyses**

> # **8**
> **Omics modalities the sandbox runs end-to-end.**
>
> Bulk RNA-seq · single-cell RNA-seq · spatial transcriptomics · ChIP-seq / ATAC-seq · variant calling & annotation · proteomics · metabolomics · microbiome — from raw files to a figure you can put in a paper.

**底部可点击的组学工作流清单**（每条可点到 `/use-case/...`）：

| 组学 | 典型工作流 | 沙箱 / skill 组件 |
|------|------------|---------------------|
| Bulk RNA-seq | QC → trim → align → quant → DE → 富集 | `fastp`, `STAR`/`salmon`, `DESeq2`, `edgeR`, `clusterProfiler` |
| scRNA-seq | matrix → QC → cluster → annotate → marker | `alevin-fry`, `scanpy`, `Seurat`, `cellxgene-skill`, `human-protein-atlas-skill` |
| Spatial transcriptomics | tissue-aware cluster → domain → niche | `scanpy`, `squidpy`, `bgee-skill` |
| Epigenomics (ChIP / ATAC) | peak → annotate → motif → diff peak | `macs3`, `deeptools`, `ChIPseeker`, `encode-skill` |
| Variant calling & annotation | align → call → filter → annotate | `bwa-mem2`, `gatk`, `bcftools`, `snpEff`, `clinvar-variation-skill`, `gnomad-graphql-skill` |
| Proteomics | search → quant → DE → pathway | `pride-skill`, `proteomexchange-skill`, `uniprot-skill`, `reactome-skill` |
| Metabolomics | feature → identify → pathway | `metabolights-skill`, `hmdb-skill`, `chebi-skill`, `rhea-skill` |
| Microbiome | amplicon / shotgun → taxonomy → function | `mgnify-skill`, 沙箱 `seqkit`, `kraken`-兼容工作流 |

**section 结尾一行**：
> The agent picks the right combination for your question. You read the answer — with every accession, peak, and p-value linked back to the source.

**视觉建议**
- 三列用冷白底 + 细分隔线，主色数字（`primary` 实验蓝）。
- 数字字体用 `Playfair Display` 的 800 字重，字号 ≈ 6–7vw，紧凑 line-height。
- 每列底部徽章不要超过三行，超过就换成 `+ n more →` 折叠到 `/product`。
- 不要堆图表、不要 dashboard mock。这一节**只用排版说话**。

---

### Section 5 — Compute Layer · 计算层（沙箱 + 智能层协作）

**目标**：给上面的场景层与能力层一个"这真的是个工作台，不是个 demo"的落地层。
这一节是三层叙事的最后一层，也是唯一允许出现 terminal 样式、agent 角色图的地方。

**Headline**
> **Compute Layer — where the work actually runs.**

中文版：
> **计算层——这一切真正跑起来的地方。**

**副标（一行）**
> A Linux sandbox under an AI team. The sandbox executes. The agents decide, verify, and narrate.

**两块并排展示**（desktop 左右分栏，mobile 堆叠）：

---

**Left — The Sandbox**

标题：`A Linux workstation with the bio stack pre-installed.`

一个 terminal 样式的 mock（真实、非伪造路径）：

```
$ which STAR samtools scanpy Rscript xelatex
/opt/bioinfo/bin/STAR
/opt/bioinfo/bin/samtools
/usr/bin/scanpy
/usr/bin/Rscript
/usr/bin/xelatex
```

下方一行字：
> Python 3, R + Bioconductor, LaTeX (Chinese-ready), 20+ bioinformatics CLIs, all inside a session that persists across turns.

---

**Right — The Intelligence（智能层）**

标题：`A team of agents that plans, runs, and verifies.`

**五角色协作示意**（横向五列极简图标 + 短标签，不画流程图）：

- **Lead** — Breaks the task down, fans out to peers, integrates the answer.
- **Explore** — Read-only reconnaissance across the literature and the databases.
- **Plan** — Drafts the approach; no code, no side-effects.
- **General** — Writes and runs the code in the sandbox.
- **Verify** — Tries to break the result before it reaches you.

下方一行字：
> Not one model doing everything. A small team with fixed rules — including one whose job is to disagree.

**两块之间的关系（放在 section 底部一行收束）**：
> The sandbox is the body. The agents are the method. The conversation is your interface to both.

**设计提示**：
- 左右两栏视觉等重：terminal mock 与五角色图标组各占一屏 1/2。
- 五角色不要用 emoji，用描边图标；active 时边框主色。
- 这一节**允许**出现技术语汇（`Lead / Explore / Plan / General / Verify`、路径、CLI 名），但不要展开到命令行参数细节。

---

### Section 6 — How it's different（vs 通用 AI）

**目标**：在三层叙事之后，直接回答"这不就是 ChatGPT 吗？"

**Headline**
> **Not another chat assistant. A biology-native one.**

中文版：
> **不是又一个聊天助手，而是为生物学而生的那一个。**

**对照表（4–6 行，最多）**，左列留白，右列强调：

|                               | Generic chat assistants | **Scientific Tumbleweed** |
|-------------------------------|--------------------------|----------------------------|
| Life-science data sources     | Web search + guesswork   | 50+ curated skills hitting real APIs |
| Can run STAR / scanpy / AlphaFold on your data | No | Yes, in the sandbox |
| Hallucinated accessions       | Common                    | Typed skill contracts, raw payloads saved |
| Claims verification           | Trust the model           | A `verification` agent tries to break each result |
| Your data stays on your infra | Depends on vendor         | Private workspace, no training on your sessions |
| Add a new database            | Prompt it harder          | Request a skill; Enterprise can commission private ones |

**不要**在这里提竞品名字。"Generic chat assistants" 就够了。

**表下一行收束**：
> We chose the harder path: real tools, real code execution, real citations — not prompt tricks.

---

### Section 7 — The method（可折叠，可放可不放）

**目标**：给 PI、BD、投资人一个"他们看过文献"的信号。
**给谁看**：三类读者里的第二、三类。第一类实验生物学家大概率会滚过去。

**折叠形式建议**：默认只显示标题 + 一句话，用户点 "Read the argument" 展开。

**Headline**
> **Why target discovery is the single highest-ROI problem in pharma — and why AI agents are the right shape for it.**

**展开后四段小标题（不展开正文，只留引文与一组数字）**：

- **Act I · Context** — ~90% of drugs entering the clinic fail. ~50% of Phase II failures trace to the wrong target.
- **Act II · Data** — Six omics modalities. Five biobanks. AlphaFold's 200M structures. And a 2× jump in clinical success when the target has genetic support.
- **Act III · Assessment** — Causality. Druggability. Safety. Tissue specificity. Competition. Five axes, each needing a different database.
- **Act IV · What agents change** — The bottleneck is no longer compute or data — it's integration. That's what agents are for.

**收束金句**（大字）：
> "AI will not replace drug hunters. But drug hunters who don't use AI will be replaced."

**设计提示**：
这一节是落地页里唯一允许用幕封（full-bleed 深色背景 + 衬线金句）的地方。节奏上它是"低谷"——让读者稍作停顿，然后进入最后的 CTA。

---

### Section 8 — Trusted

**目标**：建立"可以放心用、可以放心装在自己公司"的信任。
Scientific Tumbleweed 是**专有产品**（proprietary），不是开源项目——本节文案不使用 "open source"、"MIT licensed" 等表述。

**横向三列**，每列一行小标题 + 一行副文：

- **Auditable** · `Every tool call logged. Every citation traceable.`
- **Private by default** · `Your data stays in your workspace. We don't train on your sessions.`
- **Extensible** · `New skills ship weekly. Request one or bring your own (Enterprise).`

下方放一排**真实的 logo / badge**（不允许占位）：
- 合作机构 / 早期用户 logo（须拿到明确授权）
- ISO / SOC 徽章（**仅在真实获得认证后**放）
- 已集成的模型 logo（OpenAI · Anthropic · DeepSeek · Qwen · 本地 vLLM）
- 已集成的编辑器 logo（Claude Code · Cursor · Windsurf · Zed — 仅 MCP 接过的）

---

### Section 9 — Final CTA

**目标**：离开前再推一次。

**Headline**
> **Start a conversation. Get a result.**

中文：
> **开一次对话，拿回一份结果。**

**副文（一行）**
> If it saves you one afternoon, it's done its job.

**按钮**
- 主：`Try it now →`
- 次：`Talk to us`

背景可以做成 Hero 的呼应——同一张插画但换一个角度或配色版本。

---

## 六、顶部导航六个子页面

落地页首页之外，导航里的六个页面各自独立。这里只给定位和第一屏骨架，内容之后单独写。

### `/product`

**定位**：产品功能总览——沙箱、数据源、agent 行为、集成生态。访问者想知道"它到底是什么、里面有什么"时跳这里。
**第一屏 headline**：`Every database, tool, and agent — on one page.`
**内容骨架**：
- Integrated Biology Environment 概念（承接首页 Section 2）
- Sandbox 细节：预装的 Python / R / Bioconductor / LaTeX / 15+ bioinformatics CLI 清单（可按类别折叠）
- Skill System：50+ skill 按领域分组展示，可搜索，可点到各 skill 的介绍页
- Agent Behavior：Lead / explore / plan / general-purpose / bash / verification 五角色分工，可折叠展开规则
- Memory & Session：长期记忆、跨会话持久化、可审计的工具调用日志
- Integration 矩阵：支持的模型（OpenAI / Anthropic / DeepSeek / Qwen / 本地 vLLM）、前端/编辑器（Claude Code / Cursor / Windsurf / Zed via MCP）、可观测性（LangSmith / Langfuse）
- Deployment（Enterprise tier）：私有 / VPC / 本地化部署选项

### `/use-case`

**定位**：把落地页 Section 3 的四张卡片**每一张展开成一页**，外加更多真实场景。
**结构**：左侧是用户的一句话（衬线大字），右侧是：
- Agent 的执行步骤
- 用到的 skills 清单（可点击到文档）
- 产出示例截图 / PDF / 表格
- 耗时对比（人工预估 vs Scientific Tumbleweed）
**数量**：起步 6 个，逐步补到 12 个。首批推荐：
1. GWAS locus → 候选基因优先级
2. Drug repurposing 快速尽职调查
3. 公共 scRNA-seq 数据端到端复盘
4. 蛋白靶点的可药性评估
5. Mendelian randomization 因果推断
6. 发表级文献综述（LaTeX + PDF）

### `/research`

> **占位页（Placeholder）**。正式上线前这一页只用随机占位内容与骨架 UI，不展示任何具体文章或未发布的研究结果。

**定位**：未来用作长文区，类似 Anthropic 的 Research 板块。
**当前状态**：占位 — 不要用编造的 benchmark 或未验证的数据充数。
**占位页内容（上线前保持如下即可）**：
- 页头 headline：`Research, coming soon.`
- 一段占位副文：`We're working on long-form writing about agent behavior, skill system design, and benchmarks on real biology tasks. Check back later, or subscribe below.`
- 一个邮件订阅框：`your@email.com → Notify me`
- 3 张灰色卡片用 Lorem ipsum 填充（每张卡片：假标题 + 日期 + 一段 ~40 字占位文本），hover 不可点击，视觉表示"将有 3 个栏目"
- 页脚一行：`If you're researching with Scientific Tumbleweed, we'd love to hear from you — reach out at research@…`

### `/blog`

> **占位页（Placeholder）**。正式上线前这一页只用随机占位内容与骨架 UI，不展示任何真实用户案例或未发布的功能。

**定位**：未来用作产品更新 / 故事 / 教程栏目。
**当前状态**：占位 — 不要放任何"虚构的用户引述"或编造的案例。
**占位页内容（上线前保持如下即可）**：
- 页头 headline：`Blog, coming soon.`
- 副文：`Product updates, community stories, and how-to posts will live here. We're writing the first few now.`
- 一排三张占位卡片（灰色背景，Lorem ipsum 占位）：
  - Card A — `[Category: Release]` · `Placeholder post title one` · `Lorem ipsum dolor sit amet, consectetur adipiscing elit.`
  - Card B — `[Category: Community]` · `Placeholder post title two` · `Ut enim ad minim veniam, quis nostrud exercitation.`
  - Card C — `[Category: Tutorial]` · `Placeholder post title three` · `Duis aute irure dolor in reprehenderit in voluptate.`
- 卡片全部 hover 不可点击；悬停时 cursor 保持默认、不显示链接样式
- 页脚一行：`Want to be the first to know when we ship? → Subscribe` 邮箱订阅框

### `/pricing`

> **占位页（Placeholder）**。正式上线前这一页不暴露任何具体价格数字，所有套餐都以"Contact us"收口，避免误导市场预期。

**定位**：未来用作套餐与计费。
**当前状态**：占位 — **禁止**写死月费、年费、试用期长度。
**第一屏 headline（占位）**：`Pricing, coming soon.`
**副文（占位）**：`We're finalizing plans for individuals, labs, and enterprises. Talk to us in the meantime — we'll match what you need.`

**占位三栏套餐卡（不标价）**：

- **Starter** · `Contact us`
  - 为个人研究者设计
  - Lorem ipsum dolor sit amet
  - Consectetur adipiscing elit
  - CTA：`Talk to us`

- **Team** · `Contact us`
  - 为实验室 / 课题组设计
  - Ut enim ad minim veniam
  - Quis nostrud exercitation ullamco
  - CTA：`Talk to us`

- **Enterprise** · `Contact us`
  - 为生物医药企业与平台团队设计
  - 私有 / VPC 部署、SSO、SLA
  - 定制 skill 与私有数据源接入
  - CTA：`Talk to sales`

**页面语气守则**：
- 这一页上线前**不要**写任何具体价格。
- **不要**用 "starter / pro / business" 这类 SaaS 套话之外的营销词，保留 `Starter / Team / Enterprise` 三档结构即可。
- **不要**写 "Free forever"、"No credit card needed" 这种隐含承诺。
- 等商务 / 增长团队定稿后，再把具体数字与条款换进来；在那之前 `Contact us` 是唯一入口。

### `/about`

**定位**：产品理念、团队、公司与开源背景。
**第一屏 headline**：`We think biologists deserve better tools.`
**内容骨架**：
- Manifesto（1 段）——为什么要做这个
- What is an Integrated Biology Environment?（1 段定义）
- Origin story / 团队 / 开源血脉
- 联系方式 & 加入我们

---

## 七、文案风格守则

1. **先给结论，再给细节。** 不要"在当今的生物医学研究中……"式开场。
2. **用可验证的动词。** `runs STAR`、`calls the ClinVar VCV endpoint` — 不是 `empowers`、`revolutionizes`。
3. **不吹数字。** 不写 "100% accurate"、"blazingly fast"。允许"从数小时到数分钟"这种有对照的表述。
4. **术语首次出现要展开。** 例："PheWAS——用一个变异扫一遍数十万人身上的所有疾病。"
5. **不煽情、不 emoji。** 产品名里没有感叹号。
6. **引用要能点。** 落地页上每一条具体声明要么有链接，要么不写。
7. **中英版风格同步。** 英文是默认主版本，中文在结构不变的前提下翻译，不做本地化改写。

---

## 八、视觉风格

严格对齐 `docs/DESIGN.md` 的 Scientific Tumbleweed Lab。色板、字重、阴影、圆角、间距均以 `docs/DESIGN.md` 为唯一来源——本文**不重复定义色彩变量**，避免两份文档出现分歧。

落地页层面的补充约束仅限以下几条：

- **Hero 与 Final CTA** 允许使用深色森林墨绿底（呼应 phylo.bio 的气质），中间 section 保持冷白留白。
- **节奏**：每个 section 上下至少 `3xl`（64px）间距；Hero 与 Final CTA 允许全屏背景；中间 section 严格遵守居中栅格，两侧留白 ≥20vw。
- **插画**：有机科学插画（植物、菌丝、细胞、分子线稿），避免硅谷风科技蓝渐变。允许淡淡的纸质纹理。
- **动效**：CTA hover 有阴影微抬；section 进入用轻微 opacity fade-in。不用横飞、弹跳、粒子背景。
- **不要**：不要粒子背景、不要分屏长镜头视频、不要 dashboard mock 图（首页不是产品截图页）。

---

## 九、多语言（i18n）

落地页支持 **English (EN)** 与 **简体中文 (ZH)** 两种语言，通过 i18n 方案切换，非分站。

### 9.1 技术与路由

- **推荐实现**：`next-intl`（推荐） 或 `next-i18next`，按路由前缀切换：`/` → EN（默认）、`/zh` → 简体中文。
- 初次访问按 `Accept-Language` 探测一次，之后以 cookie 记住用户选择。
- 所有文案**必须从 JSON / YAML 翻译文件读取**，禁止在组件里硬编码中英文字符串。翻译文件目录建议：
  ```
  locales/
    en/
      common.json     — 导航、按钮、页脚
      landing.json    — 首页各 section 文案
      product.json    — /product
      use-case.json   — /use-case
      research.json   — /research (占位)
      blog.json       — /blog (占位)
      pricing.json    — /pricing (占位)
      about.json      — /about
    zh/
      (同上)
  ```
- **不要**把两种语言的字符串拼在同一文件里（例如 `title_en` / `title_zh`）。必须按目录分开。

### 9.2 语言切换入口

- **位置**：顶部导航最右侧、`Try it now` CTA 的左边。
- **样式**：文字链而非下拉菜单，只有两个选项：`EN` 与 `中`，当前语言高亮。
- **示意**：
  ```
  … About   [ EN · 中 ]   [ Try it now → ]
  ```
- 移动端折进汉堡菜单的顶部。

### 9.3 翻译守则

- 英文是**主版本**，中文按英文版翻译，结构、section 顺序、段落数**必须保持一致**。
- **术语表（必须统一）**：

  | English | 简体中文 |
  |---------|---------|
  | Scientific Tumbleweed | Scientific Tumbleweed *（产品名不翻译）* |
  | Agentic Biomedical Research Workbench | 智能体生物医学研究工作台 |
  | AI Native | AI Native *（徽章英文保持）* |
  | Integrated Biology Environment | 集成式生物学工作环境 |
  | Scenario Layer | 场景层 |
  | Capability Layer | 能力层 |
  | Compute Layer | 计算层 |
  | Intelligence / Agent team | 智能层 / 智能体团队 |
  | Sandbox | 沙箱 |
  | Skill | 技能 |
  | Agent | 智能体 / agent *（可混用）* |
  | Verification agent | 审计智能体 / verification agent |
  | Workbench | 工作台 |

- 标题里的英文专有名词（`STAR`、`scanpy`、`AlphaFold`、`CELLxGENE` 等）**保持英文原文**，中文版不要把它们翻成"星号"或"scanpy 工具"。
- 中文长句必须断开，不要出现"并且……以及……从而……"这类翻译腔。
- 中英文混排遵守：中文与英文 / 数字之间留 1 个半角空格（通过 CSS `text-spacing-trim` 或手动加）。
- 引号：英文 `"…"`，中文 `"…"`；不要混用。

### 9.4 占位页在两种语言下都保持占位

`/research` `/blog` `/pricing` 目前是占位页，翻译文件中对应内容也必须是占位版本（Lorem ipsum 或简短占位句），不要翻译任何虚构的案例、日期、价格。

---

## 十、右侧快速定位栏（In-page TOC）

**目标**：落地页首页较长，访问者需要**不回到顶部**就能跳到关心的 section。
参考同类产品（Anthropic / Linear / Phylo）在长首页的做法，右侧固定一条极简定位栏。

### 10.1 位置与外观

- **位置**：桌面端固定在视口右侧，距右边缘约 `24px`，垂直居中。
- **尺寸**：宽度 ≤ 160px；每项单行高度约 28px。
- **样式**：
  - 没有外框、没有背景，只有一列左对齐的小标签
  - 每项前面一根 2px 宽的竖线（非 active 态透明度 20%，active 态 100% 且换为主色）
  - 字体 `IBM Plex Mono` / `JetBrains Mono`，字号 11–12px，`letter-spacing: 0.12em`，全大写
  - 悬停时整个条目向右位移 2px + 透明度 100%，仅此一处微动效
- **滚动联动**：使用 `IntersectionObserver` 监听每个 section，进入视口中段时对应条目切换为 active。
- **滚动行为**：点击条目用 `scroll-behavior: smooth` 平滑滚动到对应 section；URL hash 同步更新（`#hero` / `#workbench` / `#scenario` / `#capability` / `#compute` / ...）以便分享深链。

### 10.2 条目清单（EN / ZH 对照）

落地页的定位栏直接复用"三层架构"的命名，让访问者在任何一屏都能看清楚自己在**场景→能力→计算**的哪一层。

| # | Anchor | EN label | ZH label |
|---|--------|----------|----------|
| 01 | `#hero` | Overview | 概览 |
| 02 | `#workbench` | The Workbench | 工作台 |
| 03 | `#scenario` | Scenario Layer | 场景层 |
| 04 | `#capability` | Capability Layer | 能力层 |
| 05 | `#compute` | Compute Layer | 计算层 |
| 06 | `#different` | How it's different | 差异化 |
| 07 | `#method` | The method | 方法论 |
| 08 | `#trusted` | Trusted | 可信赖 |
| 09 | `#cta` | Try it now | 立即开始 |

**视觉细节**：03–05 三条为三层主叙事，允许在条目前加一个极小的竖线编号装饰（如 `L1 · L2 · L3`），或在其前后加 1px 横线分组，让用户一眼看到它们是同一组。其余条目保持常规样式。

### 10.3 响应式

- **Desktop (≥1280px)**：完整显示，9 个条目。
- **Tablet (768–1280px)**：保留，但只显示序号 `01…09`，悬停时弹出 tooltip 显示完整文字。
- **Mobile (<768px)**：**隐藏**，由顶部 sticky 导航的"Jump to section"折叠菜单替代。

### 10.4 无障碍

- `<nav aria-label="On this page">` 包裹整体。
- 每个条目是一个 `<a href="#section-id">`，不要用 `<button>` + JS 代替，保留原生锚点跳转。
- 动画遵守 `prefers-reduced-motion`：用户关闭动画时，滚动跳转立即到位，不做平滑过渡。

---

## 十一、待确认

- [ ] Hero 背景插画需要设计师出 3 版初稿选 1 版。
- [ ] `Section 4 — Capability Layer` 的三个大数字（50+ 数据库 / 40M+ 文献 / 8 种组学）在发布前由工程核一次，确保和实际 skill 数与沙箱能力一致。
- [ ] `Section 5 — Compute Layer` 右半部分的五角色图标组（`Lead / Explore / Plan / General / Verify`）由设计师出一版描边图标。
- [ ] `Section 8 — Trusted` 的 ISO / SOC 徽章，**只有在真实获得认证后**才放；合作机构 logo 须拿到明确授权。
- [ ] `/pricing` 页保持 "Contact us" 占位；具体套餐、数字、试用条款由商务 / 增长团队定稿后再替换。
- [ ] `/research` `/blog` 首批正式内容由谁产出，计划上线时间由市场 / 内容团队确认。
- [ ] i18n：确认采用 `next-intl` 还是 `next-i18next`；`/zh` 路由前缀的 SEO / hreflang 策略。
- [ ] i18n 术语表需由产品 + 科学顾问复核后冻结；冻结后的术语写入 `locales/*/glossary.json`，供翻译人员查询。
- [ ] 术语表补充：`Scenario Layer / Capability Layer / Compute Layer` 的最终中文定稿（当前为"场景层 / 能力层 / 计算层"）由产品经理复核一次。
- [ ] 右侧快速定位栏（In-page TOC）在 tablet 宽度下的 tooltip 触发区域，QA 验证一遍避免遮挡正文。
