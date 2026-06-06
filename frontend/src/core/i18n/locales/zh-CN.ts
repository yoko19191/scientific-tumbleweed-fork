import {
  CompassIcon,
  GraduationCapIcon,
  ImageIcon,
  MicroscopeIcon,
  PenLineIcon,
  ShapesIcon,
  SparklesIcon,
  VideoIcon,
} from "lucide-react";

import type { Translations } from "./types";

export const zhCN: Translations = {
  // Locale meta
  locale: {
    localName: "中文",
  },

  // Common
  common: {
    home: "首页",
    settings: "设置",
    delete: "删除",
    edit: "编辑",
    rename: "重命名",
    openInNewWindow: "在新窗口打开",
    close: "关闭",
    back: "返回",
    backToFiles: "返回文件列表",
    more: "更多",
    search: "搜索",
    download: "下载",
    thinking: "思考",
    artifacts: "文件",
    public: "公共",
    custom: "自定义",
    notAvailableInDemoMode: "在演示模式下不可用",
    loading: "加载中...",
    version: "版本",
    lastUpdated: "最后更新",
    code: "代码",
    preview: "预览",
    cancel: "取消",
    save: "保存",
    install: "安装",
    create: "创建",
    import: "导入",
    export: "导出",
    exportAsHTML: "导出为 HTML",
    exportAsJSON: "导出为 JSON",
    exportSuccess: "对话已导出",
    noPreviewTitle: "此类文件不支持预览",
    noPreviewDescription: "请下载后查看",
    yesterday: "昨天",
  },

  // Home
  home: {
    docs: "文档",
    blog: "博客",
  },

  marketing: {
    nav: {
      product: "Product",
      useCase: "Use Case",
      research: "Research",
      blog: "Blog",
      pricing: "Pricing",
      about: "About",
      tryNow: "立即试用",
      talkToUs: "联系我们",
      readVision: "了解方法论",
    },
    footer: {
      note:
        "面向生物学团队的智能体研究平台：自动化生信分析，保留真实引用，让每一步研究都可追溯。",
      columns: [
        { title: "产品", links: ["工作台", "技能", "沙箱"] },
        { title: "公司", links: ["关于", "Research", "Blog"] },
        { title: "可信赖", links: ["有记录", "默认私有", "可扩展"] },
      ],
    },
    landing: {
      toc: [
        { href: "#hero", label: "概览" },
        { href: "#workbench", label: "工作台" },
        { href: "#scenario", label: "场景层" },
        { href: "#capability", label: "能力层" },
        { href: "#compute", label: "计算层" },
        { href: "#different", label: "差异化" },
        { href: "#method", label: "方法论" },
        { href: "#trusted", label: "可信赖" },
        { href: "#cta", label: "立即开始" },
      ],
      hero: {
        badge: "AI Native",
        headline: "Agentic Labbench\nfor Biologist\nin One",
        subhead:
          "从问题定义、假设生成，到生信分析与实验结果解读\n用自然语言驱动你的研究。",
      },
      workbench: {
        headline: "用自然语言驱动研究流程",
        body:
          "科学风滚草把生物学问题、智能体协作、生信自动化和引用追溯放在同一个工作台里。研究者提出问题，系统拆解任务、执行分析、核对证据，并把结果组织成可继续审阅的交付物。",
        items: [
          {
            title: "智能体驱动生物学研究",
            body: "从问题定义到假设生成，智能体负责拆解路径、分配任务并汇总结果。",
          },
          {
            title: "自动化生信工作流",
            body: "把重复的分析步骤交给沙箱执行，减少手工脚本、环境切换和结果搬运。",
          },
          {
            title: "引用真实可追溯",
            body: "结论必须带来源。数据库返回、文献依据和运行记录都能回看。",
          },
        ],
      },
      scenario: {
        headline: "从研究问题到可审阅结果。",
        subhead:
          "围绕智能体驱动研究、自动化生信和真实引用，覆盖生物学团队最常见的分析链路。",
        cards: [
          {
            title: "定义问题与生成假设",
            quote:
              '"我有一个疾病表型和一组初步线索，帮我整理可检验的研究假设。"',
            result:
              "系统会把问题拆成可执行的研究路径，标出证据缺口，并给出后续分析优先级。",
          },
          {
            title: "自动化公共数据分析",
            quote:
              '"帮我复盘一个公共组学数据集，给出质量控制、分群、差异信号和可解释结果。"',
            result:
              "智能体会规划生信流程并在沙箱中执行，返回图表、分析文件和可复查的运行记录。",
          },
          {
            title: "评估靶点与机制证据",
            quote:
              '"这个靶点是否值得继续推进？请把支持、反对和不确定证据分开。"',
            result:
              "系统会整合多类证据，输出结构化判断，并保留每条结论对应的真实来源。",
          },
          {
            title: "把证据写成报告",
            quote: '"请把这轮分析整理成可以发给 PI 或项目组讨论的报告。"',
            result:
              "系统会生成带引用的研究说明，区分事实、推断和待验证问题，方便团队继续决策。",
          },
        ],
        note:
          "这里强调的是工作方式：智能体负责推进流程，沙箱负责执行分析，所有结论都要回到真实引用。",
      },
      capability: {
        headline: "能力层——真实工具与真实数据源。",
        subhead:
          "这一层展示系统实际接入的数据库、文献源和生信分析能力。其他页面讲工作方式，这里讲可调用的底层能力。",
        columns: [
          {
            metric: "50+",
            title: "生命科学数据库原生接入。",
            body:
              "人类遗传、变异、表达、蛋白、结构、化合物、药物、通路、临床试验，都可以从同一个对话里调出来。",
            chips: [
              "GWAS Catalog",
              "gnomAD",
              "ClinVar",
              "Open Targets",
              "GTEx",
              "UniProt",
              "AlphaFold DB",
              "ChEMBL",
              "ClinicalTrials.gov",
            ],
          },
          {
            metric: "40M+",
            title: "文献、检索、阅读和引用。",
            body:
              "PubMed、PMC Open Access、bioRxiv、medRxiv、Semantic Scholar citation graph，再加上能带引用写综述的 agents。",
            chips: [
              "PubMed",
              "PMC OA",
              "bioRxiv",
              "Semantic Scholar",
              "deep-research",
              "LaTeX + BibTeX",
            ],
          },
          {
            metric: "8",
            title: "端到端组学分析模态。",
            body:
              "从原始文件到论文图，按问题选择数据库、CLI 和分析流程。",
            chips: [
              "Bulk RNA-seq",
              "single-cell RNA-seq",
              "spatial",
              "ChIP / ATAC",
              "variants",
              "proteomics",
              "metabolomics",
              "microbiome",
            ],
          },
        ],
        workflows: [
          { label: "Bulk RNA-seq", text: "QC ➡️ align ➡️ quantify ➡️ DE ➡️ enrichment" },
          { label: "scRNA-seq", text: "matrix ➡️ QC ➡️ cluster ➡️ annotate ➡️ marker" },
          { label: "Variant calling", text: "align ➡️ call ➡️ filter ➡️ annotate" },
          { label: "Proteomics", text: "search ➡️ quantify ➡️ DE ➡️ pathway" },
        ],
        note:
          "你不用先想清楚该调哪个库、跑哪个命令。Agent 会组合这些能力，结果里的 accession、peak、p-value 也能回溯。",
      },
      compute: {
        headline: "自动化生信，从对话进入执行。",
        subhead:
          "智能体将研究意图转化为可执行任务，沙箱负责运行分析，验证环节负责检查结果和引用。",
        sandboxTitle: "面向生信分析的可执行沙箱。",
        sandboxBody:
          "沙箱保存运行状态、输入输出和生成文件，使分析过程可以继续、可以复查，也可以交给团队成员审阅。",
        intelligenceTitle: "智能体协作层。",
        agents: [
          { title: "Lead", body: "拆解研究目标，安排执行路径，整合最终结果。" },
          { title: "Explore", body: "检索证据和背景信息，只读不改动分析环境。" },
          { title: "Plan", body: "生成分析方案，明确输入、输出和验证标准。" },
          { title: "General", body: "在沙箱中执行分析任务，生成文件和图表。" },
          { title: "Verify", body: "检查结果一致性、引用来源和潜在错误。" },
        ],
        note:
          "对研究者来说，入口仍然是自然语言；对系统来说，背后是可审计的任务执行链。",
      },
      different: {
        headline: "不是通用聊天助手，而是研究工作台。",
        rows: [
          {
            label: "研究推进方式",
            generic: "一次性回答",
            tumbleweed: "智能体拆解任务、执行分析并汇总证据",
          },
          {
            label: "生信分析",
            generic: "需要用户自行准备环境和脚本",
            tumbleweed: "从自然语言生成分析任务，并在沙箱中自动执行",
          },
          {
            label: "引用来源",
            generic: "容易混入不可验证结论",
            tumbleweed: "结论绑定真实来源和原始记录",
          },
          {
            label: "结果验证",
            generic: "主要依赖用户自行判断",
            tumbleweed: "验证智能体先检查一致性与证据链",
          },
          {
            label: "团队协作",
            generic: "对话结果难以沉淀",
            tumbleweed: "分析文件、引用和运行记录可复查、可交接",
          },
        ],
        note:
          "Scientific Tumbleweed 的重点不是生成一段漂亮回答，而是把研究过程推进到可验证、可复现、可协作的状态。",
      },
      method: {
        headline:
          "面向跨模态、跨组学的复杂系统分析。",
        subhead:
          "现代生物学问题往往同时涉及遗传、表达、表型、文献、实验结果和计算模型。难点不只是获取数据，而是把不同模态、不同组学层次放在同一套分析框架里解释。",
        trigger: "展开看看",
        acts: [
          {
            title: "Act I · 问题建模",
            body:
              "从自然语言问题出发，系统先明确研究对象、假设边界、可用证据和需要补齐的数据类型。",
          },
          {
            title: "Act II · 跨组学整合",
            body:
              "将遗传、转录组、空间组学、蛋白、代谢、微生物组等信号纳入同一条分析链，减少单一证据造成的偏差。",
          },
          {
            title: "Act III · 跨模态解释",
            body:
              "把结构化数据、文献证据、实验结果和计算输出放在同一份报告中解释，区分事实、推断和待验证假设。",
          },
          {
            title: "Act IV · 系统级验证",
            body:
              "智能体反复检查证据链、分析步骤和引用来源，帮助团队在复杂系统层面形成可审阅的研究判断。",
          },
        ],
        quote:
          "复杂生物系统不能靠单次回答理解。它需要能持续整合证据、执行分析并接受审阅的工作台。",
      },
      trusted: {
        headline: "面向真实研究流程的可信基础。",
        cards: [
          { title: "智能体驱动", body: "任务拆解、分析执行、结果汇总和验证由分工明确的智能体协作完成。" },
          { title: "自动化生信", body: "将自然语言问题转化为可执行分析流程，沉淀文件、图表和运行记录。" },
          { title: "真实引用", body: "所有关键结论都需要绑定来源，便于团队审阅、复查和继续推进。" },
        ],
        badges: ["OpenAI", "Anthropic", "DeepSeek", "Qwen", "local vLLM", "Claude Code", "Cursor", "Windsurf", "Zed"],
      },
      finalCta: {
        headline: "用自然语言启动下一次研究",
        subhead:
          "从假设生成到生信分析，再到结果解读与引用核查，让智能体把研究流程真正跑起来",
      },
    },
    pages: {
      product: {
        eyebrow: "Product",
        headline: "产品能力总览。",
        subhead:
          "了解智能体协作、生信自动化、真实引用、沙箱执行、数据源接入和企业部署选项。",
        cards: [
          { title: "Integrated Biology Environment", body: "把问题定义、数据调用、分析执行、结果解释和引用追溯放在同一工作环境中。" },
          { title: "Sandbox", body: "面向可复现分析的执行环境，保留输入、输出、生成文件和运行记录。" },
          { title: "Skill System", body: "面向生命科学数据源和研究任务的 typed skills，支持持续扩展。" },
          { title: "Agent Behavior", body: "Lead、Explore、Plan、General、Verify 分工协作，避免单一模型承担全部步骤。" },
          { title: "Memory & Session", body: "项目上下文、原始 payload、生成文件和 run history 都可以沉淀到 workspace。" },
          { title: "Deployment", body: "Enterprise 可讨论私有 workspace、VPC、本地模型、SSO 和私有数据源接入。" },
        ],
      },
      useCase: {
        eyebrow: "Use Case",
        headline: "面向真实生物学问题的工作流。",
        subhead:
          "从自然语言问题开始，由智能体拆解任务、自动化执行生信分析，并输出带真实引用的结果。",
        cards: [
          { title: "候选靶点优先级", body: "整合多层证据，形成可讨论、可追溯的候选靶点排序。" },
          { title: "药物再利用评估", body: "区分支持、反对和不确定证据，辅助团队决定是否继续推进。" },
          { title: "公共组学数据复盘", body: "自动化完成质量控制、主要分析步骤和结果解释，输出文件与图表。" },
          { title: "蛋白靶点评估", body: "从机制、表达、通路和安全性等维度组织证据。" },
          { title: "因果推断分析", body: "整理假设、输入条件和分析结果，生成可复查的因果判断。" },
          { title: "文献综述与报告", body: "检索、阅读、交叉检查并形成带引用的研究报告。" },
        ],
      },
      research: {
        eyebrow: "Research",
        headline: "Research，敬请期待。",
        subhead:
          "我们在写一些更长的文章：agent behavior、skill system design，还有真实生物学任务上的 benchmark。",
        subscribe: "上线提醒",
        footer: "如果你正在用 Scientific Tumbleweed 做研究，欢迎来聊。真实问题比 demo 更重要。",
        cards: [
          { title: "占位研究札记", meta: "准备中", body: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer posuere erat a ante venenatis dapibus." },
          { title: "占位 benchmark", meta: "准备中", body: "Sed posuere consectetur est at lobortis. Donec ullamcorper nulla non metus auctor fringilla." },
          { title: "占位方法文章", meta: "准备中", body: "Aenean lacinia bibendum nulla sed consectetur. Cras mattis consectetur purus sit amet fermentum." },
        ],
      },
      blog: {
        eyebrow: "Blog",
        headline: "Blog，敬请期待。",
        subhead:
          "产品更新、教程和一些使用记录会放在这里。第一批文章还在写。",
        subscribe: "订阅提醒",
        cards: [
          { title: "占位文章标题一", meta: "栏目：Release", body: "Lorem ipsum dolor sit amet, consectetur adipiscing elit." },
          { title: "占位文章标题二", meta: "栏目：Community", body: "Ut enim ad minim veniam, quis nostrud exercitation." },
          { title: "占位文章标题三", meta: "栏目：Tutorial", body: "Duis aute irure dolor in reprehenderit in voluptate." },
        ],
      },
      pricing: {
        eyebrow: "Pricing",
        headline: "Pricing，敬请期待。",
        subhead:
          "个人、课题组和企业方案还在确认。现在先联系我们，我们按你的场景来谈。",
        cards: [
          { title: "Starter", meta: "Contact us", body: "给个人研究者预留。正式价格和条款还没有发布。" },
          { title: "Team", meta: "Contact us", body: "给实验室和课题组预留。适合多人共享项目、文件和运行记录。" },
          { title: "Enterprise", meta: "Contact us", body: "给生物医药企业和平台团队预留。可讨论私有 / VPC 部署、SSO、SLA、定制 skill 和私有数据源接入。" },
        ],
      },
      about: {
        eyebrow: "About",
        headline: "生物学家值得更好的工具。",
        subhead:
          "今天的生物医学研究跨越多种组学、实验模态、数据库和证据类型。研究者需要的是能执行、能追溯、能协作的研究工作台。",
        cards: [
          { title: "Manifesto", body: "好的研究工作台应该能执行分析、保留来源，并让团队复查每一步。" },
          { title: "Integrated Biology Environment", body: "对话、skills、沙箱执行、artifacts、memory 和 verification 共同构成研究闭环。" },
          { title: "Origin", body: "我们关注 agentic work 在生物学研究中的落地，同时坚持科学可追溯性。" },
          { title: "Contact", body: "试点、部署和研究合作，请联系团队。" },
        ],
      },
    },
  },

  // Welcome
  welcome: {
    greeting: "你好，欢迎回来！",
    description:
      "欢迎使用科学风滚草，一个由良渚实验室出品的科研场景 AI 智能体。通过内置和自定义的 Skills，\n科学风滚草可以帮你搜索网络、分析数据，还能为你生成幻灯片、\n图片、视频、播客及网页等，几乎可以做任何事情。",

    createYourOwnSkill: "创建你自己的 Agent SKill",
    createYourOwnSkillDescription:
      "创建你的 Agent Skill 来释放科学风滚草的潜力。通过自定义技能，科学风滚草\n可以帮你搜索网络、分析数据，还能为你生成幻灯片、\n网页等作品，几乎可以做任何事情。",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "复制到剪贴板",
    copiedToClipboard: "已复制到剪贴板",
    failedToCopyToClipboard: "复制到剪贴板失败",
  },

  // Input Box
  inputBox: {
    placeholder: "今天我能为你做些什么？",
    createSkillPrompt:
      "我们一起用 skill-creator 技能来创建一个技能吧。先问问我希望这个技能能做什么。",
    addAttachments: "添加附件",
    mode: "模式",
    chatMode: "Chat",
    chatModeDescription: "Chat 响应更快，适合查阅文献、简单问答和轻量对话。",
    computerMode: "Computer",
    computerModeDescription:
      "Computer 适合需要大量代码编写、生信数据分析、PPT 或表格制作的场景。",
    reasoningEffort: "推理深度",
    reasoningEffortNone: "关闭",
    reasoningEffortNoneDescription:
      "不额外分配推理预算 — 适合直接提示和最快响应",
    reasoningEffortMinimal: "最低",
    reasoningEffortMinimalDescription:
      "快速检索、直接回答 — 事实查询、名词解释、简单问答",
    reasoningEffortLow: "低",
    reasoningEffortLowDescription:
      "轻度推理 — 论文摘要、概念解释、参考文献整理",
    reasoningEffortMedium: "中",
    reasoningEffortMediumDescription:
      "结构化分析 — 方法对比、实验设计审查、章节起草",
    reasoningEffortHigh: "高",
    reasoningEffortHighDescription:
      "深度推理 — 多文献综合、统计验证、端到端研究工作流",
    reasoningEffortMax: "最大",
    reasoningEffortMaxDescription:
      "最大深度 — 复杂智能体任务、穷尽式多步推理、无预算限制",
    reasoningEffortXhigh: "超高",
    reasoningEffortXhighDescription:
      "超高推理 — 高于高档的供应商特定档位",
    searchModels: "搜索模型...",
    surpriseMe: "小惊喜",
    surpriseMePrompt: "给我一个小惊喜吧",
    followupLoading: "正在生成可能的后续问题...",
    followupHeader: "建议后续提问",
    followupConfirmTitle: "发送建议问题？",
    followupConfirmDescription: "当前输入框已有内容，选择发送方式。",
    followupConfirmAppend: "追加并发送",
    followupConfirmReplace: "替换并发送",
    aiDisclaimer: "AI可能会产生幻觉，请交叉验证回复",
    toneStyle: "语气",
    toneStyleNormal: "默认",
    toneStyleNormalDescription: "平衡、专业",
    toneStyleFormal: "正式",
    toneStyleFormalDescription: "结构化、学术语体",
    toneStyleConcise: "简洁",
    toneStyleConciseDescription: "更短、直奔主题",
    toneStyleExplanatory: "详细解释",
    toneStyleExplanatoryDescription: "深入、分步骤",
    toneStyleEncouraging: "鼓励",
    toneStyleEncouragingDescription: "更温暖、更支持",
    suggestions: [
      {
        suggestion: "写作",
        prompt: "撰写一篇关于[主题]的博客文章",
        icon: PenLineIcon,
      },
      {
        suggestion: "研究",
        prompt: "深入浅出的研究一下[主题]，并总结发现。",
        icon: MicroscopeIcon,
      },
      {
        suggestion: "收集",
        prompt: "从[来源]收集数据并创建报告。",
        icon: ShapesIcon,
      },
      {
        suggestion: "学习",
        prompt: "学习关于[主题]并创建教程。",
        icon: GraduationCapIcon,
      },
    ],
    suggestionsCreate: [
      {
        suggestion: "网页",
        prompt: "生成一个关于[主题]的网页",
        icon: CompassIcon,
      },
      {
        suggestion: "图片",
        prompt: "生成一个关于[主题]的图片",
        icon: ImageIcon,
      },
      {
        suggestion: "视频",
        prompt: "生成一个关于[主题]的视频",
        icon: VideoIcon,
      },
      {
        type: "separator",
      },
      {
        suggestion: "技能",
        prompt:
          "我们一起用 skill-creator 技能来创建一个技能吧。先问问我希望这个技能能做什么。",
        icon: SparklesIcon,
      },
    ],
  },

  // Sidebar
  sidebar: {
    newChat: "新对话",
    chats: "对话",
    recentChats: "最近的对话",
    demoChats: "演示对话",
    agents: "智能体",
    apps: "Apps",
  },

  // Agents
  agents: {
    title: "智能体",
    description: "创建和管理具有专属 Prompt 与能力的自定义智能体。",
    newAgent: "新建智能体",
    emptyTitle: "还没有自定义智能体",
    emptyDescription: "创建你的第一个自定义智能体，设置专属系统提示词。",
    chat: "对话",
    delete: "删除",
    deleteConfirm: "确定要删除该智能体吗？此操作不可撤销。",
    deleteSuccess: "智能体已删除",
    newChat: "新对话",
    createPageTitle: "设计你的智能体",
    createPageSubtitle: "描述你想要的智能体，我来帮你通过对话创建。",
    nameStepTitle: "给新智能体起个名字",
    nameStepHint:
      "只允许字母、数字和连字符，存储时自动转为小写（例如 code-reviewer）",
    nameStepPlaceholder: "例如 code-reviewer",
    nameStepContinue: "继续",
    nameStepInvalidError: "名称无效，只允许字母、数字和连字符",
    nameStepAlreadyExistsError: "已存在同名智能体",
    nameStepNetworkError: "网络请求失败，请检查网络或后端连接",
    nameStepCheckError: "无法验证名称可用性，请稍后重试",
    nameStepApiDisabledError:
      "服务器未开启自定义智能体管理功能，请联系管理员。",
    nameStepBootstrapMessage:
      "新智能体的名称是 {name}，现在开始为它生成 **SOUL**。",
    save: "保存智能体",
    saving: "正在保存智能体...",
    saveRequested:
      "已提交保存请求，科学风滚草正在根据当前对话生成并保存初版智能体。",
    saveHint:
      "你可以在右上角的菜单里随时保存这个智能体，就算目前还只是初稿也可以。",
    saveCommandMessage:
      "请现在根据我们目前已经讨论的全部内容保存这个自定义智能体。这就是我明确的保存确认。如果仍有少量细节缺失，请根据上下文做出合理假设，生成一份简洁的英文初始 SOUL.md，并直接调用 setup_agent，不要再向我索要额外确认。",
    agentCreatedPendingRefresh:
      "智能体已创建，但科学风滚草暂时还无法读取到它。请稍后刷新当前页面。",
    more: "更多操作",
    agentCreated: "智能体已创建！",
    startChatting: "开始对话",
    backToGallery: "返回 Gallery",
  },

  // Apps
  apps: {
    title: "Apps",
    description:
      "这里会展示后端注册的真实工作流 Apps。每个 App 都应由独立模块提供元数据和启动方式。",
    searchPlaceholder: "搜索 Apps",
    categoryFilterLabel: "Apps 分类",
    allCategories: "全部",
    featured: "精选",
    comingSoon: "即将推出",
    openApp: "打开",
    emptyTitle: "还没有注册 Apps",
    emptyDescription:
      "当前没有真实 App 模块可展示。新增 App 时，请在后端注册模块，并由前端通过 /api/apps 自动读取。",
    noResultsTitle: "没有匹配的 App",
    noResultsDescription: "换一个关键词或分类试试。",
    errorTitle: "无法加载 Apps",
    errorDescription: "请确认 Gateway API 已启动，并且 /api/apps 可以访问。",
    stats: {
      registered: "已注册",
      categories: "分类",
      featured: "精选",
    },
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "工作区",
    chats: "对话",
  },

  // Workspace
  workspace: {
    officialWebsite: "良渚实验室",
    githubTooltip: "访问 Scientific Tumbleweed 的 Github 仓库",
    settingsAndMore: "设置和更多",
    visitGithub: "在 Github 上查看 Scientific Tumbleweed",
    reportIssue: "反馈问题",
    contactUs: "联系我们",
    about: "关于",
    threadInaccessible: "此对话不可访问。",
    startNewChat: "开始新对话",
  },

  // Conversation
  conversation: {
    noMessages: "还没有消息",
    startConversation: "开始新的对话以查看消息",
  },

  // Chats
  chats: {
    description: "查看、搜索和继续你在工作区中的历史对话。",
    searchChats: "搜索对话",
  },

  // Page titles (document title)
  pages: {
    appName: "科学风滚草",
    chats: "对话",
    newChat: "新对话",
    untitled: "未命名",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `查看其他 ${count} 个步骤`,
    lessSteps: "隐藏步骤",
    executeCommand: "执行命令",
    presentFiles: "展示文件",
    needYourHelp: "需要你的协助",
    useTool: (toolName: string) => `使用 “${toolName}” 工具`,
    searchFor: (query: string) => `搜索 “${query}”`,
    searchForRelatedInfo: "搜索相关信息",
    searchForRelatedImages: "搜索相关图片",
    searchForRelatedImagesFor: (query: string) => `搜索相关图片 “${query}”`,
    searchOnWebFor: (query: string) => `在网络上搜索 “${query}”`,
    viewWebPage: "查看网页",
    listFolder: "列出文件夹",
    readFile: "读取文件",
    writeFile: "写入文件",
    clickToViewContent: "点击查看文件内容",
    writeTodos: "更新 To-do 列表",
    skillInstallTooltip: "安装技能并使其可在科学风滚草中使用",
    searchAcademicPapers: "搜索学术论文",
    searchAcademicPapersFor: (query: string) => `搜索学术论文 "${query}"`,
    academicPaperCitations: (count: number) => `${count} 次引用`,
    exportBibtex: "导出 BibTeX 引用",
    getCitationNetwork: "构建引用网络",
  },

  // Citations
  citations: {
    source: "来源",
    visitSource: "查看来源",
    citationsCount: (count: number) => `${count} 次引用`,
  },

  uploads: {
    uploading: "上传中...",
    uploadingFiles: "文件上传中，请稍候...",
    fileTooLargeWarning: (count: number, limit: string) =>
      count === 1
        ? `这个文件超过上传限制（${limit}），没有加入附件。`
        : `${count} 个文件超过上传限制（${limit}），没有加入附件。`,
  },

  subtasks: {
    subtask: "子任务",
    executing: (count: number) =>
      `${count > 1 ? "并行" : ""}执行 ${count} 个子任务`,
    in_progress: "子任务运行中",
    completed: "子任务已完成",
    failed: "子任务失败",
  },

  // Token Usage
  tokenUsage: {
    title: "Token 用量",
    label: "Tokens",
    input: "输入",
    output: "输出",
    total: "总计",
    view: "视图",
    note:
      "线程总量来自后端 run 记录；运行中的任务会叠加少量实时增量，完成后以落库结果为准。",
    finalAnswer: "最终回答",
    stepTotal: "步骤总计",
    sharedAttribution: "由下列动作共享",
    startTodo: (content: string) => `开始待办：${content}`,
    completeTodo: (content: string) => `完成待办：${content}`,
    updateTodo: (content: string) => `更新待办：${content}`,
    removeTodo: (content: string) => `移除待办：${content}`,
    subagent: (description: string) => `子任务：${description}`,
    presets: {
      off: "off",
      per_run: "per_run",
      per_turn: "per_turn",
      step_debug: "step_debug",
    },
    presetDescriptions: {
      off: "隐藏 Token 用量。",
      per_run: "仅在顶部展示线程 run 总量。",
      per_turn: "展示顶部总量，并在每轮对话末尾展示一次汇总。",
      step_debug: "展示顶部总量，并按归因步骤展开每轮明细。",
    },
    unavailable:
      "暂无 Token 用量。只有模型成功返回且供应商提供 usage_metadata 时才会显示。",
    unavailableShort: "未返回用量",
  },

  // Shortcuts
  shortcuts: {
    searchActions: "搜索操作...",
    noResults: "未找到结果。",
    actions: "操作",
    keyboardShortcuts: "键盘快捷键",
    keyboardShortcutsDescription: "使用键盘快捷键更快地操作。",
    openCommandPalette: "打开命令面板",
    toggleSidebar: "切换侧边栏",
  },

  // Settings
  settings: {
    title: "设置",
    description: "根据你的偏好调整界面和行为。",
    sections: {
      appearance: "外观",
      memory: "记忆",
      tools: "工具",
      skills: "技能",
      notification: "通知",
      about: "关于",
    },
    memory: {
      title: "记忆",
      description:
        "平台会在后台不断从你的对话中自动学习。这些记忆能帮助更好地理解你，并提供更个性化的体验。",
      empty: "暂无可展示的记忆数据。",
      rawJson: "原始 JSON",
      exportButton: "导出记忆",
      exportSuccess: "记忆已导出",
      importButton: "导入记忆",
      importConfirmTitle: "导入记忆？",
      importConfirmDescription: "这会用选中的 JSON 备份覆盖当前记忆。",
      importFileLabel: "已选择文件",
      importInvalidFile: "读取记忆文件失败，请选择有效的 JSON 导出文件。",
      importSuccess: "记忆已导入",
      manualFactSource: "手动添加",
      addFact: "添加事实",
      addFactTitle: "添加记忆事实",
      editFactTitle: "编辑记忆事实",
      addFactSuccess: "事实已创建",
      editFactSuccess: "事实已更新",
      clearAll: "清空全部记忆",
      clearAllConfirmTitle: "要清空全部记忆吗？",
      clearAllConfirmDescription:
        "这会删除所有已保存的摘要和事实。此操作无法撤销。",
      clearAllSuccess: "已清空全部记忆",
      factDeleteConfirmTitle: "要删除这条事实吗？",
      factDeleteConfirmDescription:
        "这条事实会立即从记忆中删除。此操作无法撤销。",
      factDeleteSuccess: "事实已删除",
      factContentLabel: "内容",
      factCategoryLabel: "类别",
      factConfidenceLabel: "置信度",
      factContentPlaceholder: "描述你想保存的记忆事实",
      factCategoryPlaceholder: "context",
      factConfidenceHint: "请输入 0 到 1 之间的数字。",
      factSave: "保存事实",
      factValidationContent: "事实内容不能为空。",
      factValidationConfidence: "置信度必须是 0 到 1 之间的数字。",
      noFacts: "还没有保存的事实。",
      summaryReadOnly:
        "摘要分区当前仍为只读。现在你可以清空全部记忆或删除单条事实。",
      memoryFullyEmpty: "还没有保存任何记忆。",
      factPreviewLabel: "即将删除的事实",
      searchPlaceholder: "搜索记忆",
      filterAll: "全部",
      filterFacts: "事实",
      filterSummaries: "摘要",
      noMatches: "没有找到匹配的记忆。",
      markdown: {
        overview: "概览",
        userContext: "用户上下文",
        work: "工作",
        personal: "个人",
        topOfMind: "近期关注（Top of mind）",
        historyBackground: "历史背景",
        recentMonths: "近几个月",
        earlierContext: "更早上下文",
        longTermBackground: "长期背景",
        updatedAt: "更新于",
        facts: "事实",
        empty: "（空）",
        table: {
          category: "类别",
          confidence: "置信度",
          confidenceLevel: {
            veryHigh: "极高",
            high: "较高",
            normal: "一般",
            unknown: "未知",
          },
          content: "内容",
          source: "来源",
          createdAt: "创建时间",
          view: "查看",
        },
      },
    },
    appearance: {
      themeTitle: "主题",
      themeDescription: "跟随系统或选择固定的界面模式。",
      system: "系统",
      light: "浅色",
      dark: "深色",
      systemDescription: "自动跟随系统主题。",
      lightDescription: "更明亮的配色，适合日间使用。",
      darkDescription: "更暗的配色，减少眩光方便专注。",
      languageTitle: "语言",
      languageDescription: "在不同语言之间切换。",
    },
    tools: {
      title: "工具",
      description: "管理 MCP 工具的配置和启用状态。",
    },
    skills: {
      title: "技能",
      description: "管理 Agent Skill 配置和启用状态。",
      createSkill: "新建技能",
      emptyTitle: "还没有技能",
      emptyDescription:
        "将你的 Agent Skill 文件夹放在科学风滚草根目录下的 `/skills/custom` 文件夹中。",
      emptyButton: "创建你的第一个技能",
    },
    notification: {
      title: "通知",
      description:
        "平台只会在窗口不活跃时发送完成通知，特别适合长时间任务：你可以先去做别的事，完成后会收到提醒。",
      requestPermission: "请求通知权限",
      deniedHint:
        "通知权限已被拒绝。可在浏览器的网站设置中重新开启，以接收完成提醒。",
      testButton: "发送测试通知",
      testTitle: "科学风滚草",
      testBody: "这是一条测试通知。",
      notSupported: "当前浏览器不支持通知功能。",
      disableNotification: "关闭通知",
    },
    acknowledge: {
      emptyTitle: "致谢",
      emptyDescription: "相关的致谢信息会展示在这里。",
    },
  },

  // Auth
  auth: {
    login: "登录",
    register: "注册",
    email: "邮箱",
    password: "密码",
    confirmPassword: "确认密码",
    username: "用户名",
    displayName: "昵称",
    usernamePlaceholder: "如 john_doe（字母、数字、下划线）",
    displayNamePlaceholder: "如 张三",
    usernameRequired: "请输入用户名",
    usernameInvalid: "用户名须为 3-30 位字母、数字或下划线",
    displayNameRequired: "请输入昵称",
    usernameAlreadyExists: "该用户名已被占用",
    loginButton: "登录",
    registerButton: "注册",
    noAccount: "还没有账号？",
    hasAccount: "已有账号？",
    loginSuccess: "登录成功",
    registerSuccess: "注册成功",
    emailRequired: "请输入邮箱",
    passwordRequired: "请输入密码",
    passwordTooShort: "密码至少 8 位",
    passwordMismatch: "两次密码不一致",
    emailAlreadyExists: "该邮箱已注册",
    invalidCredentials: "邮箱或密码错误",
    tooManyAttempts: "登录尝试次数过多，请稍后再试",
    logout: "退出登录",
    loggingOut: "正在退出...",
  },

  preferences: {
    title: "个性化",
    description: "管理记忆、工具和技能设置，让工作区更贴合你的研究习惯。",
    tabs: {
      memory: "记忆",
      tools: "工具",
      skills: "技能",
    },
  },

  account: {
    title: "账号",
    username: "用户名",
    displayName: "昵称",
    email: "邮箱",
    logout: "退出登录",
  },
};
