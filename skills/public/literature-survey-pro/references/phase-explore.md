# Phase 2: Explore — 并行文献搜集

本文件在 Phase 2 开始时加载。目标：通过多源搜索和子智能体并行调度，搜集覆盖所有 RQ 的文献集。

> **门控条件**：(a) 论文数 ≥ 目标 80% (b) 每个 RQ 有 ≥5 篇相关论文 (c) 引用网络已遍历 ≥3 种子论文。三项全部通过才能进入 Phase 3。

---

## 1. 多源搜索策略

按优先级依次使用以下数据源，每个源有明确的职责分工：

| 优先级 | 数据源 | 工具 | 职责 | 预期产出 |
|--------|--------|------|------|---------|
| 1 | Semantic Scholar + OpenAlex | `academic_search_papers` | 主力搜索，覆盖绝大多数同行评审文献 | 每个子主题 15-25 篇候选 |
| 2 | 引用网络 | `academic_get_citation_network` | 从种子论文出发，发现关键词搜索遗漏的论文 | 每个种子扩展 10-30 篇 |
| 3 | 推荐系统 | `academic_recommend_papers` | 基于已收集的高质量论文发现相关工作 | 补充 5-15 篇 |
| 4 | arXiv | `arxiv_search.py` (via bash) | 补充最新预印本（尤其 CS/ML/Physics 领域） | 每个子主题 5-10 篇 |
| 5 | 作者追踪 | `academic_search_author` | 追踪关键作者的全部相关工作 | 按需 |
| 6 | 网络搜索 | `web_search` + `web_fetch` | 兜底：灰色文献、技术报告、白皮书 | 仅在前 5 源不足时使用 |

### 工具调用示例

```
# 主力搜索
academic_search_papers(query="transformer attention mechanism", limit=20, source="auto")

# 引用网络（双向遍历）
academic_get_citation_network(paper_id="DOI_OR_S2_ID", direction="both", max_nodes=50)

# 推荐扩展
academic_recommend_papers(paper_ids=["id1","id2","id3"], limit=15)

# arXiv 补充
bash: python /mnt/skills/public/systematic-literature-review/scripts/arxiv_search.py \
  "transformer attention" --max-results 15 --sort-by relevance --category cs.CL

# BibTeX 导出（Write 阶段使用，但 Explore 阶段可预取）
academic_get_bibtex(paper_ids=["id1","id2",...])
```

---

## 2. 搜索执行协议

按以下步骤执行，严格遵循顺序：

### Step 1: 关键词扩展
从 Scope Card 的每个子主题和 RQ 中提取 2-3 组关键词变体：
- 同义词扩展（如 "attention mechanism" → "self-attention", "cross-attention"）
- 缩写展开（如 "NLP" → "natural language processing"）
- 上下位词（如 "BERT" → "pre-trained language model"）

### Step 2: 跨库搜索
对每组关键词执行 `academic_search_papers`，参数：
- `limit`: 20（每组）
- `source`: "auto"（自动选择 Semantic Scholar 或 OpenAlex）
- 如果 Scope Card 指定了时间窗口，添加 `year_range` 过滤

同时对 CS/ML/Physics 相关主题执行 `arxiv_search.py` 补充。

### Step 3: 种子选择
从搜索结果中选择 3-5 篇种子论文，标准：
- 引用数最高的 2-3 篇（领域奠基性工作）
- 最近 2 年内引用增长最快的 1-2 篇（新兴热点）
- Scope Card 中用户指定的种子论文（如有）

### Step 4: 引用网络遍历
对每个种子论文执行 `academic_get_citation_network(direction="both", max_nodes=50)`：
- 前向引用（citing）：发现后续工作
- 后向引用（cited by）：发现理论基础
- 从网络中筛选与 RQ 相关的论文加入候选集

### Step 5: 推荐扩展
将已收集的高质量论文（引用数 top 5）作为输入，执行 `academic_recommend_papers`，发现关键词搜索和引用网络都遗漏的相关工作。

### Step 6: 去重与筛选
- 按 DOI 去重（无 DOI 时按标题模糊匹配）
- 按 Scope Card 的排除条件过滤
- 按时间窗口过滤
- 按与 RQ 的相关性排序（每篇论文标注与哪些 RQ 相关）

---

## 3. 子智能体调度策略

将 Scope Card 中的子主题分配给子智能体并行执行。

### 调度规则

- 子智能体类型：`general-purpose`（需要访问 academic 工具）
- 最大并发数：**3**（硬限制，超过会被静默丢弃）
- 每个子智能体负责 1-2 个子主题

### 轮次表

| 子主题数 | 子智能体数 | 轮次 | 每轮调度 |
|---------|-----------|------|---------|
| 1-3 | 1-3 | 1 轮 | 全部 |
| 4-5 | 3+2 或 3+1 | 2 轮 | 第 1 轮 3 个，第 2 轮剩余 |
| 6 | 3+3 | 2 轮 | 每轮 3 个 |
| 7-9 | 3+3+N | 3 轮 | 每轮最多 3 个 |

### 子智能体 Prompt 模板

```
你是文献搜集专家。请为以下子主题搜集学术文献：

子主题：[TOPIC_NAME]
相关研究问题：[RQ1, RQ2]
搜索关键词：[KEYWORD_SET]
时间窗口：[YEAR_RANGE]
目标论文数：[N] 篇

执行步骤：
1. 使用 academic_search_papers 搜索每组关键词（limit=20）
2. 从结果中选择 2-3 篇高引用论文作为种子
3. 对种子执行 academic_get_citation_network(direction="both", max_nodes=30)
4. 去重后，为每篇论文提取结构化元数据

输出格式（JSON 数组）：
[{
  "paper_id": "DOI 或 S2 ID",
  "title": "...",
  "authors": ["..."],
  "year": 2024,
  "venue": "...",
  "abstract_summary": "1-2 句摘要",
  "methodology": "方法简述",
  "key_findings": ["发现1", "发现2", "发现3"],
  "limitations": "局限性简述",
  "relevance_to_RQ": {"RQ1": 4, "RQ2": 2},
  "citation_count": 123,
  "classification_tags": ["tag1", "tag2"]
}]

注意：
- 仅记录 API 返回的真实元数据，禁止猜测或捏造
- abstract_summary 限制在 2 句以内（节省 token）
- relevance_to_RQ 评分 1-5（5=高度相关）
```

### 结果合并

所有子智能体返回后：
1. 合并所有论文列表
2. 按 DOI/paper_id 去重
3. 统计每个 RQ 的覆盖度
4. 检查门控条件

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
| key_findings | string[] | ✅ | 3-5 条关键发现 |
| limitations | string | ⚠️ | 局限性简述 |
| relevance_to_RQ | dict | ✅ | 每个 RQ 的相关性评分 (1-5) |
| citation_count | int | ⚠️ | 引用数 |
| classification_tags | string[] | ✅ | 分类标签（用于 Write 阶段的主题组织） |

标注 ⚠️ 的字段：如果 API 未返回，标注为 "unknown"，**禁止猜测**。

---

## 5. 四节冷却规则

为防止上下文溢出（80-120 篇论文的元数据可能超过 token 预算），执行以下冷却策略：

### 处理完每批子智能体后：
1. **保留**：结构化元数据 JSON（每篇约 200 token）
2. **丢弃**：原始搜索结果、完整摘要文本、中间推理过程
3. **压缩**：将已处理的论文列表写入文件（`/mnt/user-data/outputs/survey-<slug>/explore/papers.json`），从上下文中移除

### 进入 Write 阶段前：
- 上下文中仅保留：Scope Card + 论文元数据摘要表（每篇 1 行：id, title, year, tags, RQ relevance）
- 完整元数据从文件中按需读取

---

## 6. 门控条件检查

Phase 2 完成后，逐项检查：

| 条件 | 检查方法 | 未通过时处理 |
|------|---------|------------|
| 论文数 ≥ 目标 80% | 统计去重后的论文总数 | 扩大搜索关键词或放宽时间窗口，启动补充搜索 |
| 每个 RQ ≥ 5 篇相关论文 | 检查 relevance_to_RQ ≥ 3 的论文数 | 针对覆盖不足的 RQ 启动定向搜索 |
| 引用网络 ≥ 3 种子 | 统计已执行 citation_network 的种子数 | 补充执行 |

**所有条件通过后**，向用户报告搜集结果摘要（论文总数、各 RQ 覆盖度、主要来源分布），然后进入 Phase 3。

**如果补充搜索后仍未通过**，向用户报告缺口，建议调整 Scope Card（缩小范围或修改 RQ），回退到 Phase 1。
