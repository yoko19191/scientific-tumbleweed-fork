import type { LucideIcon } from "lucide-react";

type MarketingNavKey =
  | "product"
  | "useCase"
  | "research"
  | "blog"
  | "pricing"
  | "about";

type MarketingCard = {
  body?: string;
  label?: string;
  meta?: string;
  quote?: string;
  result?: string;
  title: string;
};

type MarketingPage = {
  eyebrow?: string;
  headline: string;
  subhead: string;
  cards: MarketingCard[];
};

type MarketingTranslations = {
  nav: Record<MarketingNavKey, string> & {
    tryNow: string;
    talkToUs: string;
    readVision: string;
  };
  footer: {
    columns: { links: string[]; title: string }[];
    note: string;
  };
  landing: {
    toc: { href: string; label: string }[];
    hero: {
      badge: string;
      headline: string;
      subhead: string;
    };
    workbench: {
      headline: string;
      body: string;
      items: MarketingCard[];
    };
    scenario: {
      headline: string;
      subhead: string;
      cards: MarketingCard[];
      note: string;
    };
    capability: {
      headline: string;
      subhead: string;
      columns: (MarketingCard & { chips: string[]; metric: string })[];
      workflows: { label: string; text: string }[];
      note: string;
    };
    compute: {
      headline: string;
      subhead: string;
      sandboxTitle: string;
      sandboxBody: string;
      intelligenceTitle: string;
      agents: MarketingCard[];
      note: string;
    };
    different: {
      headline: string;
      rows: { generic: string; label: string; tumbleweed: string }[];
      note: string;
    };
    method: {
      headline: string;
      subhead: string;
      trigger: string;
      acts: MarketingCard[];
      quote: string;
    };
    trusted: {
      headline: string;
      cards: MarketingCard[];
      badges: string[];
    };
    finalCta: {
      headline: string;
      subhead: string;
    };
  };
  pages: {
    product: MarketingPage;
    useCase: MarketingPage;
    research: MarketingPage & {
      subscribe: string;
      footer: string;
    };
    blog: MarketingPage & {
      subscribe: string;
    };
    pricing: MarketingPage;
    about: MarketingPage;
  };
};

export interface Translations {
  // Locale meta
  locale: {
    localName: string;
  };

  // Common
  common: {
    home: string;
    settings: string;
    delete: string;
    edit: string;
    rename: string;
    share: string;
    openInNewWindow: string;
    close: string;
    back: string;
    backToFiles: string;
    more: string;
    search: string;
    download: string;
    thinking: string;
    artifacts: string;
    public: string;
    custom: string;
    notAvailableInDemoMode: string;
    loading: string;
    version: string;
    lastUpdated: string;
    code: string;
    preview: string;
    cancel: string;
    save: string;
    install: string;
    create: string;
    import: string;
    export: string;
    exportAsMarkdown: string;
    exportAsJSON: string;
    exportSuccess: string;
    noPreviewTitle: string;
    noPreviewDescription: string;
    yesterday: string;
  };

  home: {
    docs: string;
    blog: string;
  };

  marketing: MarketingTranslations;

  // Welcome
  welcome: {
    greeting: string;
    description: string;
    createYourOwnSkill: string;
    createYourOwnSkillDescription: string;
  };

  // Clipboard
  clipboard: {
    copyToClipboard: string;
    copiedToClipboard: string;
    failedToCopyToClipboard: string;
    linkCopied: string;
  };

  // Input Box
  inputBox: {
    placeholder: string;
    createSkillPrompt: string;
    addAttachments: string;
    mode: string;
    chatMode: string;
    chatModeDescription: string;
    computerMode: string;
    computerModeDescription: string;
    reasoningEffort: string;
    reasoningEffortNone: string;
    reasoningEffortNoneDescription: string;
    reasoningEffortMinimal: string;
    reasoningEffortMinimalDescription: string;
    reasoningEffortLow: string;
    reasoningEffortLowDescription: string;
    reasoningEffortMedium: string;
    reasoningEffortMediumDescription: string;
    reasoningEffortHigh: string;
    reasoningEffortHighDescription: string;
    reasoningEffortMax: string;
    reasoningEffortMaxDescription: string;
    reasoningEffortXhigh: string;
    reasoningEffortXhighDescription: string;
    searchModels: string;
    surpriseMe: string;
    surpriseMePrompt: string;
    followupLoading: string;
    followupHeader: string;
    followupConfirmTitle: string;
    followupConfirmDescription: string;
    followupConfirmAppend: string;
    followupConfirmReplace: string;
    aiDisclaimer: string;
    toneStyle: string;
    toneStyleNormal: string;
    toneStyleNormalDescription: string;
    toneStyleFormal: string;
    toneStyleFormalDescription: string;
    toneStyleConcise: string;
    toneStyleConciseDescription: string;
    toneStyleExplanatory: string;
    toneStyleExplanatoryDescription: string;
    toneStyleEncouraging: string;
    toneStyleEncouragingDescription: string;
    suggestions: {
      suggestion: string;
      prompt: string;
      icon: LucideIcon;
    }[];
    suggestionsCreate: (
      | {
          suggestion: string;
          prompt: string;
          icon: LucideIcon;
        }
      | {
          type: "separator";
        }
    )[];
  };

  // Sidebar
  sidebar: {
    recentChats: string;
    newChat: string;
    chats: string;
    demoChats: string;
    agents: string;
    apps: string;
  };

  // Agents
  agents: {
    title: string;
    description: string;
    newAgent: string;
    emptyTitle: string;
    emptyDescription: string;
    chat: string;
    delete: string;
    deleteConfirm: string;
    deleteSuccess: string;
    newChat: string;
    createPageTitle: string;
    createPageSubtitle: string;
    nameStepTitle: string;
    nameStepHint: string;
    nameStepPlaceholder: string;
    nameStepContinue: string;
    nameStepInvalidError: string;
    nameStepAlreadyExistsError: string;
    nameStepNetworkError: string;
    nameStepCheckError: string;
    nameStepApiDisabledError: string;
    nameStepBootstrapMessage: string;
    save: string;
    saving: string;
    saveRequested: string;
    saveHint: string;
    saveCommandMessage: string;
    agentCreatedPendingRefresh: string;
    more: string;
    agentCreated: string;
    startChatting: string;
    backToGallery: string;
  };

  // Apps
  apps: {
    title: string;
    description: string;
    searchPlaceholder: string;
    categoryFilterLabel: string;
    allCategories: string;
    featured: string;
    comingSoon: string;
    openApp: string;
    emptyTitle: string;
    emptyDescription: string;
    noResultsTitle: string;
    noResultsDescription: string;
    errorTitle: string;
    errorDescription: string;
    stats: {
      registered: string;
      categories: string;
      featured: string;
    };
  };

  // Breadcrumb
  breadcrumb: {
    workspace: string;
    chats: string;
  };

  // Workspace
  workspace: {
    officialWebsite: string;
    githubTooltip: string;
    settingsAndMore: string;
    visitGithub: string;
    reportIssue: string;
    contactUs: string;
    about: string;
    threadInaccessible: string;
    startNewChat: string;
  };

  // Conversation
  conversation: {
    noMessages: string;
    startConversation: string;
  };

  // Chats
  chats: {
    description: string;
    searchChats: string;
  };

  // Page titles (document title)
  pages: {
    appName: string;
    chats: string;
    newChat: string;
    untitled: string;
  };

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => string;
    lessSteps: string;
    executeCommand: string;
    presentFiles: string;
    needYourHelp: string;
    useTool: (toolName: string) => string;
    searchForRelatedInfo: string;
    searchForRelatedImages: string;
    searchFor: (query: string) => string;
    searchForRelatedImagesFor: (query: string) => string;
    searchOnWebFor: (query: string) => string;
    viewWebPage: string;
    listFolder: string;
    readFile: string;
    writeFile: string;
    clickToViewContent: string;
    writeTodos: string;
    skillInstallTooltip: string;
    searchAcademicPapers: string;
    searchAcademicPapersFor: (query: string) => string;
    academicPaperCitations: (count: number) => string;
    exportBibtex: string;
    getCitationNetwork: string;
  };

  // Citations
  citations: {
    source: string;
    visitSource: string;
    citationsCount: (count: number) => string;
  };

  // Uploads
  uploads: {
    uploading: string;
    uploadingFiles: string;
    fileTooLargeWarning: (count: number, limit: string) => string;
  };

  // Subtasks
  subtasks: {
    subtask: string;
    executing: (count: number) => string;
    in_progress: string;
    completed: string;
    failed: string;
  };

  // Token Usage
  tokenUsage: {
    title: string;
    label: string;
    input: string;
    output: string;
    total: string;
    view: string;
    note: string;
    finalAnswer: string;
    stepTotal: string;
    sharedAttribution: string;
    startTodo: (content: string) => string;
    completeTodo: (content: string) => string;
    updateTodo: (content: string) => string;
    removeTodo: (content: string) => string;
    subagent: (description: string) => string;
    presets: {
      off: string;
      per_run: string;
      per_turn: string;
      step_debug: string;
    };
    presetDescriptions: {
      off: string;
      per_run: string;
      per_turn: string;
      step_debug: string;
    };
    unavailable: string;
    unavailableShort: string;
  };

  // Shortcuts
  shortcuts: {
    searchActions: string;
    noResults: string;
    actions: string;
    keyboardShortcuts: string;
    keyboardShortcutsDescription: string;
    openCommandPalette: string;
    toggleSidebar: string;
  };

  // Settings
  settings: {
    title: string;
    description: string;
    sections: {
      appearance: string;
      memory: string;
      tools: string;
      skills: string;
      notification: string;
      about: string;
    };
    memory: {
      title: string;
      description: string;
      empty: string;
      rawJson: string;
      exportButton: string;
      exportSuccess: string;
      importButton: string;
      importConfirmTitle: string;
      importConfirmDescription: string;
      importFileLabel: string;
      importInvalidFile: string;
      importSuccess: string;
      manualFactSource: string;
      addFact: string;
      addFactTitle: string;
      editFactTitle: string;
      addFactSuccess: string;
      editFactSuccess: string;
      clearAll: string;
      clearAllConfirmTitle: string;
      clearAllConfirmDescription: string;
      clearAllSuccess: string;
      factDeleteConfirmTitle: string;
      factDeleteConfirmDescription: string;
      factDeleteSuccess: string;
      factContentLabel: string;
      factCategoryLabel: string;
      factConfidenceLabel: string;
      factContentPlaceholder: string;
      factCategoryPlaceholder: string;
      factConfidenceHint: string;
      factSave: string;
      factValidationContent: string;
      factValidationConfidence: string;
      noFacts: string;
      summaryReadOnly: string;
      memoryFullyEmpty: string;
      factPreviewLabel: string;
      searchPlaceholder: string;
      filterAll: string;
      filterFacts: string;
      filterSummaries: string;
      noMatches: string;
      markdown: {
        overview: string;
        userContext: string;
        work: string;
        personal: string;
        topOfMind: string;
        historyBackground: string;
        recentMonths: string;
        earlierContext: string;
        longTermBackground: string;
        updatedAt: string;
        facts: string;
        empty: string;
        table: {
          category: string;
          confidence: string;
          confidenceLevel: {
            veryHigh: string;
            high: string;
            normal: string;
            unknown: string;
          };
          content: string;
          source: string;
          createdAt: string;
          view: string;
        };
      };
    };
    appearance: {
      themeTitle: string;
      themeDescription: string;
      system: string;
      light: string;
      dark: string;
      systemDescription: string;
      lightDescription: string;
      darkDescription: string;
      languageTitle: string;
      languageDescription: string;
    };
    tools: {
      title: string;
      description: string;
    };
    skills: {
      title: string;
      description: string;
      createSkill: string;
      emptyTitle: string;
      emptyDescription: string;
      emptyButton: string;
    };
    notification: {
      title: string;
      description: string;
      requestPermission: string;
      deniedHint: string;
      testButton: string;
      testTitle: string;
      testBody: string;
      notSupported: string;
      disableNotification: string;
    };
    acknowledge: {
      emptyTitle: string;
      emptyDescription: string;
    };
  };

  // Auth
  auth: {
    login: string;
    register: string;
    email: string;
    password: string;
    confirmPassword: string;
    username: string;
    displayName: string;
    usernamePlaceholder: string;
    displayNamePlaceholder: string;
    usernameRequired: string;
    usernameInvalid: string;
    displayNameRequired: string;
    usernameAlreadyExists: string;
    loginButton: string;
    registerButton: string;
    noAccount: string;
    hasAccount: string;
    loginSuccess: string;
    registerSuccess: string;
    emailRequired: string;
    passwordRequired: string;
    passwordTooShort: string;
    passwordMismatch: string;
    emailAlreadyExists: string;
    invalidCredentials: string;
    tooManyAttempts: string;
    logout: string;
    loggingOut: string;
  };

  // Preferences
  preferences: {
    title: string;
    description: string;
    tabs: {
      memory: string;
      tools: string;
      skills: string;
    };
  };

  // Account
  account: {
    title: string;
    username: string;
    displayName: string;
    email: string;
    logout: string;
  };
}
