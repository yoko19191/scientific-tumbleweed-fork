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

export const enUS: Translations = {
  // Locale meta
  locale: {
    localName: "English",
  },

  // Common
  common: {
    home: "Home",
    settings: "Settings",
    delete: "Delete",
    edit: "Edit",
    rename: "Rename",
    openInNewWindow: "Open in new window",
    close: "Close",
    back: "Back",
    backToFiles: "Back to files",
    more: "More",
    search: "Search",
    download: "Download",
    thinking: "Thinking",
    artifacts: "Artifacts",
    public: "Public",
    custom: "Custom",
    notAvailableInDemoMode: "Not available in demo mode",
    loading: "Loading...",
    version: "Version",
    lastUpdated: "Last updated",
    code: "Code",
    preview: "Preview",
    cancel: "Cancel",
    save: "Save",
    install: "Install",
    create: "Create",
    import: "Import",
    export: "Export",
    exportAsHTML: "Export as HTML",
    exportAsJSON: "Export as JSON",
    exportSuccess: "Conversation exported",
    noPreviewTitle: "No preview for this file type",
    noPreviewDescription: "Download it to view.",
    yesterday: "Yesterday",
  },

  // Home
  home: {
    docs: "Docs",
    blog: "Blog",
  },

  marketing: {
    nav: {
      product: "Product",
      useCase: "Use Case",
      research: "Research",
      blog: "Blog",
      pricing: "Pricing",
      about: "About",
      tryNow: "Try it now",
      talkToUs: "Talk to us",
      readVision: "Read our vision",
      workbench: "Workbench",
    },
    footer: {
      note:
        "Built for biomedical work that needs data, code, citations, and review in the same place.",
      columns: [
        { title: "Product", links: ["Workbench", "Skills", "Sandbox"] },
        { title: "Company", links: ["About", "Research", "Blog"] },
        { title: "Trust", links: ["Auditable", "Private", "Extensible"] },
      ],
    },
    landing: {
      toc: [
        { href: "#hero", label: "Overview" },
        { href: "#collaboration", label: "Collaboration" },
        { href: "#workflow", label: "Workflow" },
        { href: "#capability", label: "Capability" },
        { href: "#cta", label: "Try it now" },
      ],
      hero: {
        badge: "AI × Biology",
        headline: "Agent x Biologist\nCowork Lead Science Frontier.",
        subhead:
          "Scientific Tumbleweed puts research questions, data analysis, and evidence checks on one executable labbench.",
      },
      workbench: {
        headline: "A labbench that collaborates.",
        body:
          "Biology brings complex signals. The agent plans, executes, and checks the work. Between them is not a chat window, but a traceable research chain.",
        items: [
          {
            title: "Read biological signals",
            body: "Genes, omics, phenotypes, and papers become evidence the team can discuss.",
          },
          {
            title: "Create the next move",
            body: "The agent breaks questions into search, analysis, verification, and reporting tasks.",
          },
          {
            title: "Keep scientific boundaries",
            body: "Claims stay attached to sources, files, and run records for review.",
          },
        ],
      },
      scenario: {
        headline: "From one question to a reviewable research run.",
        subhead:
          "The page no longer explains every feature. It shows how scientific intent becomes the next action.",
        cards: [
          {
            title: "Raise a hypothesis",
            quote: '"What candidate mechanisms might explain this phenotype?"',
            result: "Organize evidence, gaps, and priority.",
          },
          {
            title: "Run the analysis",
            quote: '"Replay this public omics dataset."',
            result: "Plan the workflow and generate figures and files in the sandbox.",
          },
          {
            title: "Check the claim",
            quote: '"What is supported, and what is still uncertain?"',
            result: "Separate facts, inferences, and open questions.",
          },
          {
            title: "Write the evidence into a report",
            quote:
              '"Turn this analysis into a report I can send to the project team."',
            result:
              "The output separates facts, inferences, and open questions, with citations ready for review.",
          },
        ],
        note:
          "Agents move the work forward, the sandbox executes analyses, and every conclusion must trace back to real evidence.",
      },
      capability: {
        headline: "Real tools, fewer entry points.",
        subhead:
          "Databases, papers, CLIs, and models are organized as capabilities the agent can call.",
        columns: [
          {
            metric: "50+",
            title: "Life-science databases",
            body:
              "Genetics, variants, expression, proteins, structures, drugs, pathways, and trials from one question.",
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
            title: "Papers and citations",
            body:
              "Search, read, cross-check, and report while keeping clickable sources.",
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
            title: "Omics analysis modes",
            body:
              "From raw files to figures, with the database, CLI, and analysis path selected for the question.",
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
          "The agent picks the right combination for your question. You read the answer with every accession, peak, and p-value linked back to the source.",
      },
      compute: {
        headline: "The intelligence layer moves the work.",
        subhead:
          "The researcher states intent. Agents turn it into executable, checkable, shareable steps.",
        sandboxTitle: "An executable sandbox for bioinformatics analysis.",
        sandboxBody:
          "The sandbox preserves state, inputs, outputs, and generated files so work can continue, be reviewed, and be handed off.",
        intelligenceTitle: "A coordinated agent layer.",
        agents: [
          { title: "Lead", body: "Breaks down goals and keeps direction." },
          { title: "Explore", body: "Collects evidence and background." },
          { title: "Plan", body: "Defines inputs, outputs, and checks." },
          { title: "General", body: "Runs analysis and creates files." },
          { title: "Verify", body: "Checks results, citations, and uncertainty." },
        ],
        note:
          "The researcher works in natural language; the system maintains an auditable execution chain underneath.",
      },
      different: {
        headline: "Not a general chat assistant. A research labbench.",
        rows: [
          {
            label: "Research execution",
            generic: "One-off answers",
            tumbleweed: "Agents plan, execute, and synthesize evidence",
          },
          {
            label: "Bioinformatics",
            generic: "User prepares scripts and environments",
            tumbleweed: "Natural language drives executable analysis",
          },
          {
            label: "Citation grounding",
            generic: "Claims may be difficult to verify",
            tumbleweed: "Claims link back to real sources and records",
          },
          {
            label: "Claims verification",
            generic: "Trust the model",
            tumbleweed: "Verification checks consistency and evidence",
          },
          {
            label: "Team handoff",
            generic: "Conversation output is hard to operationalize",
            tumbleweed: "Files, citations, and run records are reviewable",
          },
        ],
        note:
          "The goal is not a polished paragraph. The goal is a research process that can be verified, reproduced, and shared.",
      },
      method: {
        headline:
          "Complex systems analysis across modalities and omics layers.",
        subhead:
          "Modern biology spans genetics, expression, phenotype, literature, experiments, and computational outputs. The bottleneck is interpreting them together.",
        trigger: "Read the argument",
        acts: [
          {
            title: "Act I · Problem modeling",
            body:
              "The system starts by defining the research object, hypothesis boundary, available evidence, and missing data types.",
          },
          {
            title: "Act II · Cross-omics integration",
            body:
              "Signals across genetics, transcriptomics, spatial biology, proteins, metabolism, and microbiome can be organized into one analysis chain.",
          },
          {
            title: "Act III · Cross-modal interpretation",
            body:
              "Structured data, literature evidence, experimental readouts, and computational results are interpreted in one report.",
          },
          {
            title: "Act IV · System-level verification",
            body:
              "Agents repeatedly check evidence chains, analysis steps, and citations so teams can review the judgment.",
          },
        ],
        quote:
          "Complex biology cannot be handled by a single answer. It needs a labbench that keeps integrating evidence, running analyses, and exposing its reasoning for review.",
      },
      trusted: {
        headline: "Built for real research workflows.",
        cards: [
          { title: "Agent-driven", body: "Task planning, analysis execution, synthesis, and verification are handled by coordinated agents." },
          { title: "Bioinformatics automation", body: "Natural language becomes executable workflows, files, figures, and run records." },
          { title: "Real citations", body: "Important claims stay attached to sources for team review and follow-up." },
        ],
        badges: ["OpenAI", "Anthropic", "DeepSeek", "Qwen", "local vLLM", "Claude Code", "Cursor", "Windsurf", "Zed"],
      },
      finalCta: {
        headline: "Start the next research workflow in natural language.",
        subhead:
          "From hypothesis generation to bioinformatics analysis, result interpretation, and citation checks.",
      },
    },
    pages: {
      product: {
        eyebrow: "Product",
        headline: "Every database, tool, and agent -- on one page.",
        subhead:
          "A compact map of the workbench: sandbox, skills, agent behavior, memory, integrations, and deployment options.",
        cards: [
          { title: "Integrated Biology Environment", body: "One conversation spanning data sources, code execution, artifacts, citations, and review." },
          { title: "Sandbox", body: "Python, R, Bioconductor, LaTeX, and bioinformatics CLIs for reproducible analysis." },
          { title: "Skill System", body: "50+ typed life-science skills grouped by genetics, proteins, drugs, omics, trials, and literature." },
          { title: "Agent Behavior", body: "Lead, Explore, Plan, General, and Verify roles with fixed rules and observable state." },
          { title: "Memory & Session", body: "Persistent context, saved raw payloads, generated artifacts, and auditable run history." },
          { title: "Deployment", body: "Enterprise paths for private workspace, VPC, local models, SSO, and private data sources." },
        ],
      },
      useCase: {
        eyebrow: "Use Case",
        headline: "Questions you can hand to the workbench.",
        subhead:
          "Each use case starts as one research sentence and ends as a structured result with sources and files.",
        cards: [
          { title: "GWAS locus -> candidate genes", body: "Rank causal genes across genetics, expression, constraint, and burden evidence." },
          { title: "Drug repurposing diligence", body: "Build a for / against / unknown evidence brief before spending the afternoon." },
          { title: "Public scRNA-seq replay", body: "Fetch a dataset, run QC, cluster, annotate, and return AnnData plus figures." },
          { title: "Protein target assessment", body: "Combine structure, interactions, tissue expression, pathways, and druggability evidence." },
          { title: "Mendelian randomization", body: "Map instruments, check assumptions, and produce a reproducible causal analysis." },
          { title: "Publication-grade literature survey", body: "Search, read, cross-check, draft, export BibTeX, and compile a PDF." },
        ],
      },
      research: {
        eyebrow: "Research",
        headline: "Research, coming soon.",
        subhead:
          "We are working on long-form writing about agent behavior, skill system design, and benchmarks on real biology tasks.",
        subscribe: "Notify me",
        footer:
          "If you are researching with Scientific Tumbleweed, we would love to hear from you.",
        cards: [
          { title: "Placeholder research note", meta: "Coming soon", body: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer posuere erat a ante venenatis dapibus." },
          { title: "Placeholder benchmark", meta: "Coming soon", body: "Sed posuere consectetur est at lobortis. Donec ullamcorper nulla non metus auctor fringilla." },
          { title: "Placeholder methods essay", meta: "Coming soon", body: "Aenean lacinia bibendum nulla sed consectetur. Cras mattis consectetur purus sit amet fermentum." },
        ],
      },
      blog: {
        eyebrow: "Blog",
        headline: "Blog, coming soon.",
        subhead:
          "Product updates, community stories, and how-to posts will live here. We are writing the first few now.",
        subscribe: "Subscribe",
        cards: [
          { title: "Placeholder post title one", meta: "Category: Release", body: "Lorem ipsum dolor sit amet, consectetur adipiscing elit." },
          { title: "Placeholder post title two", meta: "Category: Community", body: "Ut enim ad minim veniam, quis nostrud exercitation." },
          { title: "Placeholder post title three", meta: "Category: Tutorial", body: "Duis aute irure dolor in reprehenderit in voluptate." },
        ],
      },
      pricing: {
        eyebrow: "Pricing",
        headline: "Pricing, coming soon.",
        subhead:
          "We are finalizing plans for individuals, labs, and enterprises. Talk to us in the meantime; we will match what you need.",
        cards: [
          { title: "Starter", meta: "Contact us", body: "For individual researchers. Lorem ipsum dolor sit amet. Consectetur adipiscing elit." },
          { title: "Team", meta: "Contact us", body: "For labs and research groups. Ut enim ad minim veniam. Quis nostrud exercitation ullamco." },
          { title: "Enterprise", meta: "Contact us", body: "For biopharma and platform teams. Private / VPC deployment, SSO, SLA, custom skills, and private data sources." },
        ],
      },
      about: {
        eyebrow: "About",
        headline: "We think biologists deserve better tools.",
        subhead:
          "Scientific Tumbleweed exists because biomedical research now spans more databases, file formats, and evidence types than any one person should have to manually stitch together.",
        cards: [
          { title: "Manifesto", body: "A workbench should run the analysis, keep the sources, and make the evidence reviewable." },
          { title: "Integrated Biology Environment", body: "The product combines conversation, skills, sandbox execution, artifacts, memory, and verification." },
          { title: "Origin", body: "Built for research teams that need agentic work without losing scientific traceability." },
          { title: "Contact", body: "For pilots, deployment questions, and research collaborations, talk to the team." },
        ],
      },
    },
  },

  // Welcome
  welcome: {
    greeting: "Hello, again!",
    description:
      "Welcome to Scientific Tumbleweed, an AI-powered research agent by 良渚实验室. With built-in and custom skills, Scientific Tumbleweed helps you search on the web, analyze data, and generate artifacts like slides, web pages and do almost anything.",

    createYourOwnSkill: "Create Your Own Skill",
    createYourOwnSkillDescription:
      "Create your own skill to release the power of Scientific Tumbleweed. With customized skills,\nScientific Tumbleweed can help you search on the web, analyze data, and generate\n artifacts like slides, web pages and do almost anything.",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "Copy to clipboard",
    copiedToClipboard: "Copied to clipboard",
    failedToCopyToClipboard: "Failed to copy to clipboard",
  },

  // Input Box
  inputBox: {
    placeholder: "How can I assist you today?",
    createSkillPrompt:
      "We're going to build a new skill step by step with `skill-creator`. To start, what do you want this skill to do?",
    addAttachments: "Add attachments",
    mode: "Mode",
    chatMode: "Chat",
    chatModeDescription:
      "Chat responds faster and is best for literature lookup, simple Q&A, and lightweight conversation.",
    computerMode: "Computer",
    computerModeDescription:
      "Computer is best for substantial code writing, bioinformatics data analysis, slides, and spreadsheets.",
    reasoningEffort: "Reasoning Effort",
    reasoningEffortNone: "None",
    reasoningEffortNoneDescription:
      "No extra reasoning budget — fastest responses for direct prompts",
    reasoningEffortMinimal: "Minimal",
    reasoningEffortMinimalDescription:
      "Quick lookup, direct answer — fact retrieval, definitions, simple Q&A",
    reasoningEffortLow: "Low",
    reasoningEffortLowDescription:
      "Light reasoning — summarize a paper, explain a concept, format references",
    reasoningEffortMedium: "Medium",
    reasoningEffortMediumDescription:
      "Structured analysis — compare methods, review experimental design, draft sections",
    reasoningEffortHigh: "High",
    reasoningEffortHighDescription:
      "Deep reasoning — multi-paper synthesis, statistical validation, end-to-end research workflow",
    reasoningEffortMax: "Max",
    reasoningEffortMaxDescription:
      "Maximum depth — complex agent tasks, exhaustive multi-step reasoning, no budget limit",
    reasoningEffortXhigh: "X-High",
    reasoningEffortXhighDescription:
      "Extra-high reasoning — provider-specific tier above high",
    searchModels: "Search models...",
    surpriseMe: "Surprise",
    surpriseMePrompt: "Surprise me",
    followupLoading: "Generating follow-up questions...",
    followupHeader: "Try asking",
    followupConfirmTitle: "Send suggestion?",
    followupConfirmDescription:
      "You already have text in the input. Choose how to send it.",
    followupConfirmAppend: "Append & send",
    followupConfirmReplace: "Replace & send",
    aiDisclaimer: "AI can make mistakes, please double-check the answer",
    toneStyle: "Tone",
    toneStyleNormal: "Normal",
    toneStyleNormalDescription: "Balanced, professional",
    toneStyleFormal: "Formal",
    toneStyleFormalDescription: "Structured, academic register",
    toneStyleConcise: "Concise",
    toneStyleConciseDescription: "Shorter, to-the-point",
    toneStyleExplanatory: "Explanatory",
    toneStyleExplanatoryDescription: "Thorough, step-by-step",
    toneStyleEncouraging: "Encouraging",
    toneStyleEncouragingDescription: "Warmer, supportive",
    suggestions: [
      {
        suggestion: "Write",
        prompt: "Write a blog post about the latest trends on [topic]",
        icon: PenLineIcon,
      },
      {
        suggestion: "Research",
        prompt:
          "Conduct a deep dive research on [topic], and summarize the findings.",
        icon: MicroscopeIcon,
      },
      {
        suggestion: "Collect",
        prompt: "Collect data from [source] and create a report.",
        icon: ShapesIcon,
      },
      {
        suggestion: "Learn",
        prompt: "Learn about [topic] and create a tutorial.",
        icon: GraduationCapIcon,
      },
    ],
    suggestionsCreate: [
      {
        suggestion: "Webpage",
        prompt: "Create a webpage about [topic]",
        icon: CompassIcon,
      },
      {
        suggestion: "Image",
        prompt: "Create an image about [topic]",
        icon: ImageIcon,
      },
      {
        suggestion: "Video",
        prompt: "Create a video about [topic]",
        icon: VideoIcon,
      },
      {
        type: "separator",
      },
      {
        suggestion: "Skill",
        prompt:
          "We're going to build a new skill step by step with `skill-creator`. To start, what do you want this skill to do?",
        icon: SparklesIcon,
      },
    ],
  },

  // Sidebar
  sidebar: {
    newChat: "New chat",
    chats: "Chats",
    recentChats: "Recent chats",
    demoChats: "Demo chats",
    agents: "Agents",
    apps: "Apps",
  },

  // Agents
  agents: {
    title: "Agents",
    description:
      "Create and manage custom agents with specialized prompts and capabilities.",
    newAgent: "New Agent",
    emptyTitle: "No custom agents yet",
    emptyDescription:
      "Create your first custom agent with a specialized system prompt.",
    chat: "Chat",
    delete: "Delete",
    deleteConfirm:
      "Are you sure you want to delete this agent? This action cannot be undone.",
    deleteSuccess: "Agent deleted",
    newChat: "New chat",
    createPageTitle: "Design your Agent",
    createPageSubtitle:
      "Describe the agent you want — I'll help you create it through conversation.",
    nameStepTitle: "Name your new Agent",
    nameStepHint:
      "Letters, digits, and hyphens only — stored lowercase (e.g. code-reviewer)",
    nameStepPlaceholder: "e.g. code-reviewer",
    nameStepContinue: "Continue",
    nameStepInvalidError:
      "Invalid name — use only letters, digits, and hyphens",
    nameStepAlreadyExistsError: "An agent with this name already exists",
    nameStepNetworkError:
      "Network request failed — check your network or backend connection",
    nameStepCheckError: "Could not verify name availability — please try again",
    nameStepApiDisabledError:
      "Custom agent management is not enabled on this server. Please contact your administrator.",
    nameStepBootstrapMessage:
      "The new custom agent name is {name}. Let's bootstrap it's **SOUL**.",
    save: "Save agent",
    saving: "Saving agent...",
    saveRequested:
      "Save requested. Scientific Tumbleweed is generating and saving an initial version now.",
    saveHint:
      "You can save this agent at any time from the top-right menu, even if this is only a first draft.",
    saveCommandMessage:
      "Please save this custom agent now based on everything we have discussed so far. Treat this as my explicit confirmation to save. If some details are still missing, make reasonable assumptions, generate a concise first SOUL.md in English, and call setup_agent immediately without asking me for more confirmation.",
    agentCreatedPendingRefresh:
      "The agent was created, but Scientific Tumbleweed could not load it yet. Please refresh this page in a moment.",
    more: "More actions",
    agentCreated: "Agent created!",
    startChatting: "Start chatting",
    backToGallery: "Back to Gallery",
  },

  // Apps
  apps: {
    title: "Apps",
    description:
      "Registered workflow apps appear here. Each app should provide its own metadata and launch behavior from a dedicated module.",
    searchPlaceholder: "Search apps",
    categoryFilterLabel: "Apps categories",
    allCategories: "All",
    featured: "Featured",
    comingSoon: "Soon",
    openApp: "Open",
    emptyTitle: "No apps registered yet",
    emptyDescription:
      "There are no real app modules to show. Add an app by registering a backend module and the frontend will read it from /api/apps.",
    noResultsTitle: "No apps match this view",
    noResultsDescription: "Try another search term or category.",
    errorTitle: "Could not load apps",
    errorDescription:
      "Make sure the Gateway API is running and /api/apps is reachable.",
    stats: {
      registered: "Registered",
      categories: "Categories",
      featured: "Featured",
    },
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "Workspace",
    chats: "Chats",
  },

  // Workspace
  workspace: {
    officialWebsite: "Official website",
    githubTooltip: "Scientific Tumbleweed on Github",
    settingsAndMore: "Settings and more",
    visitGithub: "GitHub",
    reportIssue: "Report a issue",
    contactUs: "Contact us",
    about: "About",
    threadInaccessible: "This conversation is not accessible.",
    startNewChat: "Start a new chat",
  },

  // Conversation
  conversation: {
    noMessages: "No messages yet",
    startConversation: "Start a conversation to see messages here",
  },

  // Chats
  chats: {
    description: "Review, search, and continue workspace conversations.",
    searchChats: "Search chats",
  },

  // Page titles (document title)
  pages: {
    appName: "Scientific Tumbleweed",
    chats: "Chats",
    newChat: "New chat",
    untitled: "Untitled",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `${count} more step${count === 1 ? "" : "s"}`,
    lessSteps: "Less steps",
    executeCommand: "Execute command",
    presentFiles: "Present files",
    needYourHelp: "Need your help",
    useTool: (toolName: string) => `Use "${toolName}" tool`,
    searchFor: (query: string) => `Search for "${query}"`,
    searchForRelatedInfo: "Search for related information",
    searchForRelatedImages: "Search for related images",
    searchForRelatedImagesFor: (query: string) =>
      `Search for related images for "${query}"`,
    searchOnWebFor: (query: string) => `Search on the web for "${query}"`,
    viewWebPage: "View web page",
    listFolder: "List folder",
    readFile: "Read file",
    writeFile: "Write file",
    clickToViewContent: "Click to view file content",
    writeTodos: "Update to-do list",
    skillInstallTooltip: "Install skill and make it available to Scientific Tumbleweed",
    searchAcademicPapers: "Search academic papers",
    searchAcademicPapersFor: (query: string) => `Search academic papers for "${query}"`,
    academicPaperCitations: (count: number) => `${count} citations`,
    exportBibtex: "Exporting BibTeX citations",
    getCitationNetwork: "Building citation network",
  },

  // Citations
  citations: {
    source: "Source",
    visitSource: "Visit source",
    citationsCount: (count: number) => `${count} citations`,
  },

  // Subtasks
  uploads: {
    uploading: "Uploading...",
    uploadingFiles: "Uploading files, please wait...",
    fileTooLargeWarning: (count: number, limit: string) =>
      count === 1
        ? `This file is larger than the upload limit (${limit}) and was not added.`
        : `${count} files are larger than the upload limit (${limit}) and were not added.`,
  },

  subtasks: {
    subtask: "Subtask",
    executing: (count: number) =>
      `Executing ${count === 1 ? "" : count + " "}subtask${count === 1 ? "" : "s in parallel"}`,
    in_progress: "Running subtask",
    completed: "Subtask completed",
    failed: "Subtask failed",
  },

  // Token Usage
  tokenUsage: {
    title: "Token Usage",
    label: "Tokens",
    input: "Input",
    output: "Output",
    total: "Total",
    view: "View",
    note:
      "Thread total comes from backend run records. Active runs may include a small live delta until the run is finalized.",
    finalAnswer: "Final answer",
    stepTotal: "Step total",
    sharedAttribution: "Shared across listed actions",
    startTodo: (content: string) => `Start todo: ${content}`,
    completeTodo: (content: string) => `Complete todo: ${content}`,
    updateTodo: (content: string) => `Update todo: ${content}`,
    removeTodo: (content: string) => `Remove todo: ${content}`,
    subagent: (description: string) => `Subagent: ${description}`,
    presets: {
      off: "off",
      per_run: "per_run",
      per_turn: "per_turn",
      step_debug: "step_debug",
    },
    presetDescriptions: {
      off: "Hide token usage.",
      per_run: "Show only the thread run total in the header.",
      per_turn: "Show the header total and one inline total for each turn.",
      step_debug: "Show the header total and attribution details for each turn.",
    },
    unavailable:
      "No token usage yet. Usage appears only after a successful model response when the provider returns usage_metadata.",
    unavailableShort: "No usage returned",
  },

  // Shortcuts
  shortcuts: {
    searchActions: "Search actions...",
    noResults: "No results found.",
    actions: "Actions",
    keyboardShortcuts: "Keyboard Shortcuts",
    keyboardShortcutsDescription:
      "Navigate Scientific Tumbleweed faster with keyboard shortcuts.",
    openCommandPalette: "Open Command Palette",
    toggleSidebar: "Toggle Sidebar",
  },

  // Settings
  settings: {
    title: "Settings",
    description: "Adjust how Scientific Tumbleweed looks and behaves for you.",
    sections: {
      appearance: "Appearance",
      memory: "Memory",
      tools: "Tools",
      skills: "Skills",
      notification: "Notification",
      about: "About",
    },
    memory: {
      title: "Memory",
      description:
        "Scientific Tumbleweed automatically learns from your conversations in the background. These memories help Scientific Tumbleweed understand you better and deliver a more personalized experience.",
      empty: "No memory data to display.",
      rawJson: "Raw JSON",
      exportButton: "Export memory",
      exportSuccess: "Memory exported",
      importButton: "Import memory",
      importConfirmTitle: "Import memory?",
      importConfirmDescription:
        "This will overwrite your current memory with the selected JSON backup.",
      importFileLabel: "Selected file",
      importInvalidFile:
        "Failed to read the selected memory file. Please choose a valid JSON export.",
      importSuccess: "Memory imported",
      manualFactSource: "Manual",
      addFact: "Add fact",
      addFactTitle: "Add memory fact",
      editFactTitle: "Edit memory fact",
      addFactSuccess: "Fact created",
      editFactSuccess: "Fact updated",
      clearAll: "Clear all memory",
      clearAllConfirmTitle: "Clear all memory?",
      clearAllConfirmDescription:
        "This will remove all saved summaries and facts. This action cannot be undone.",
      clearAllSuccess: "All memory cleared",
      factDeleteConfirmTitle: "Delete this fact?",
      factDeleteConfirmDescription:
        "This fact will be removed from memory immediately. This action cannot be undone.",
      factDeleteSuccess: "Fact deleted",
      factContentLabel: "Content",
      factCategoryLabel: "Category",
      factConfidenceLabel: "Confidence",
      factContentPlaceholder: "Describe the memory fact you want to save",
      factCategoryPlaceholder: "context",
      factConfidenceHint: "Use a number between 0 and 1.",
      factSave: "Save fact",
      factValidationContent: "Fact content cannot be empty.",
      factValidationConfidence: "Confidence must be a number between 0 and 1.",
      noFacts: "No saved facts yet.",
      summaryReadOnly:
        "Summary sections are read-only for now. You can currently add, edit, or delete individual facts, or clear all memory.",
      memoryFullyEmpty: "No memory saved yet.",
      factPreviewLabel: "Fact to delete",
      searchPlaceholder: "Search memory",
      filterAll: "All",
      filterFacts: "Facts",
      filterSummaries: "Summaries",
      noMatches: "No matching memory found.",
      markdown: {
        overview: "Overview",
        userContext: "User context",
        work: "Work",
        personal: "Personal",
        topOfMind: "Top of mind",
        historyBackground: "History",
        recentMonths: "Recent months",
        earlierContext: "Earlier context",
        longTermBackground: "Long-term background",
        updatedAt: "Updated at",
        facts: "Facts",
        empty: "(empty)",
        table: {
          category: "Category",
          confidence: "Confidence",
          confidenceLevel: {
            veryHigh: "Very high",
            high: "High",
            normal: "Normal",
            unknown: "Unknown",
          },
          content: "Content",
          source: "Source",
          createdAt: "CreatedAt",
          view: "View",
        },
      },
    },
    appearance: {
      themeTitle: "Theme",
      themeDescription:
        "Choose how the interface follows your device or stays fixed.",
      system: "System",
      light: "Light",
      dark: "Dark",
      systemDescription: "Match the operating system preference automatically.",
      lightDescription: "Bright palette with higher contrast for daytime.",
      darkDescription: "Dim palette that reduces glare for focus.",
      languageTitle: "Language",
      languageDescription: "Switch between languages.",
    },
    tools: {
      title: "Tools",
      description: "Manage the configuration and enabled status of MCP tools.",
    },
    skills: {
      title: "Agent Skills",
      description:
        "Manage the configuration and enabled status of the agent skills.",
      createSkill: "Create skill",
      emptyTitle: "No agent skill yet",
      emptyDescription:
        "Put your agent skill folders under the `/skills/custom` folder under the root folder of Scientific Tumbleweed.",
      emptyButton: "Create Your First Skill",
    },
    notification: {
      title: "Notification",
      description:
        "Scientific Tumbleweed only sends a completion notification when the window is not active. This is especially useful for long-running tasks so you can switch to other work and get notified when done.",
      requestPermission: "Request notification permission",
      deniedHint:
        "Notification permission was denied. You can enable it in your browser's site settings to receive completion alerts.",
      testButton: "Send test notification",
      testTitle: "Scientific Tumbleweed",
      testBody: "This is a test notification.",
      notSupported: "Your browser does not support notifications.",
      disableNotification: "Disable notification",
    },
    acknowledge: {
      emptyTitle: "Acknowledgements",
      emptyDescription: "Credits and acknowledgements will show here.",
    },
  },

  // Auth
  auth: {
    login: "Login",
    register: "Register",
    email: "Email",
    password: "Password",
    confirmPassword: "Confirm Password",
    username: "Username",
    displayName: "Display Name",
    usernamePlaceholder: "e.g. john_doe (letters, numbers, underscore)",
    displayNamePlaceholder: "e.g. John Doe",
    usernameRequired: "Username is required",
    usernameInvalid: "Username must be 3-30 characters, letters/numbers/underscore only",
    displayNameRequired: "Display name is required",
    usernameAlreadyExists: "Username already taken",
    loginButton: "Login",
    registerButton: "Register",
    noAccount: "Don't have an account?",
    hasAccount: "Already have an account?",
    loginSuccess: "Login successful",
    registerSuccess: "Registration successful",
    emailRequired: "Email is required",
    passwordRequired: "Password is required",
    passwordTooShort: "Password must be at least 8 characters",
    passwordMismatch: "Passwords do not match",
    emailAlreadyExists: "Email already registered",
    invalidCredentials: "Incorrect email or password",
    tooManyAttempts: "Too many login attempts. Please try again later",
    logout: "Logout",
    loggingOut: "Logging out...",
  },

  preferences: {
    title: "Preferences",
    description:
      "Manage memory, tools, and skills so the workspace fits your research habits.",
    tabs: {
      memory: "Memory",
      tools: "Tools",
      skills: "Skills",
    },
  },

  account: {
    title: "Account",
    username: "Username",
    displayName: "Display Name",
    email: "Email",
    logout: "Sign Out",
  },
};
