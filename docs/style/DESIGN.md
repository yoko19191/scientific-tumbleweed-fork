# Bio Agentic Workbench Design System

## Overview

This document defines the visual and interaction system for a biomedical Agentic Workbench: a platform where researchers, engineers, and domain experts coordinate AI agents, life-science capabilities, sandboxed execution, uploaded data, generated artifacts, and long-running research workflows.

The product should feel like a clean research command center rather than a generic chatbot. The first impression is bright, precise, and laboratory-grade: warm lab-paper backgrounds, crisp blue primary actions, orange upload/creation emphasis, green biological success states, cyan data highlights, purple AI reasoning states, and strong red only for truly critical conditions. The interface must support long sessions, dense information, and high-stakes review without becoming visually heavy.

The core design promise is:

- **Scientific clarity**: information is scannable, evidence is traceable, and visual hierarchy favors interpretation over decoration.
- **Agentic observability**: users can always see what the agent is doing, which tools or capabilities are involved, what changed, and what needs review.
- **Workbench efficiency**: the UI is built for repeated use: threads, files, citations, capabilities, artifacts, tasks, and agent state are always close at hand.
- **Biomedical trust**: colors, copy, tables, charts, and status states must avoid hype. Use precise labels, provenance, confidence, and review affordances.

Do not build a marketing-first interface for the main workspace. The default screen should be the usable workbench: navigation, current thread or project, agent execution, files, tools, artifacts, and review state.

## Design Principles

### 1. Workbench Before Showcase

Every workspace page should expose the user's working objects directly: current thread, selected agent, active capability/tool state, uploaded files, generated artifacts, tasks, citations, and run history. Avoid oversized hero treatments inside operational screens. Welcome states may be editorial, but once a user starts working, density and continuity matter more than spectacle.

### 2. Trust Through Structure

Biomedical users need to understand where an answer came from. Favor source lists, evidence rows, expandable reasoning summaries, dataset metadata, file provenance, and clear review states. A beautiful answer without traceability should be considered incomplete.

### 3. Agent State Is A First-Class Surface

Agent activity should not be represented by a generic spinner alone. The system needs visible states for planning, searching, reading, executing tools, delegating to subagents, writing artifacts, waiting for user approval, verifying, completing, failing, and being cancelled.

### 4. Color Has Jobs

Use color to communicate function. Blue means primary navigation/action. Orange means create/upload/initiate a lab action. Green means healthy biological or workflow success. Cyan means data/measurement/visualization. Purple means AI reasoning or agentic behavior. Yellow means caution or pending review. Red means critical risk, destructive action, failed validation, or clinical/safety concern.

### 5. Dense Does Not Mean Noisy

This product will have sidebars, threads, tables, files, logs, citations, and charts. Keep surfaces calm: thin dividers, restrained backgrounds, modest shadows, and consistent spacing. Let active states and data carry energy.

### 6. Real Product Chrome Beats Abstract Decoration

When a page needs visual richness, show actual product states: thread timelines, tool calls, task graphs, file cards, result tables, citation panels, sandbox output, sequence/protein/variant cards, and artifact previews. Avoid decorative blobs, abstract gradients, or pseudo-scientific ornaments.

## Color System

Use the HSL palette from `color_palette_demo.html` as the canonical visual direction. If implementation uses OKLCH or Tailwind tokens, keep perceptual results close to these values.

### Core Tokens

| Token | Value | Role |
|---|---:|---|
| `{colors.bg-main}` | `hsl(42, 24%, 93%)` | Main lab-paper background. Warm, bright, and easier on the eyes than pure white. |
| `{colors.bg-sub}` | `hsl(38, 18%, 88%)` | Secondary section background, side panels, quiet grouping bands. |
| `{colors.surface}` | `hsl(40, 24%, 97%)` | Primary card, popover, dialog, and content surface. |
| `{colors.surface-strong}` | `hsl(210, 20%, 92%)` | Sidebar wells, selected neutral controls, table header backgrounds. |
| `{colors.border}` | `hsl(210, 10%, 75%)` | Strong structural borders and panel outlines. |
| `{colors.border-soft}` | `hsl(210, 15%, 88%)` | Default card borders and dividers. |
| `{colors.divider}` | `hsl(210, 8%, 60%)` | Strong rules in dense tables or split panes. |
| `{colors.primary}` | `hsl(225, 76%, 52%)` | Primary blue: main action, active navigation, selected agent, current workflow. |
| `{colors.primary-hover}` | `hsl(225, 82%, 60%)` | Hover state for primary action. |
| `{colors.primary-active}` | `hsl(225, 82%, 38%)` | Pressed state, active text on pale blue, selected indicator. |
| `{colors.accent}` | `hsl(24, 98%, 56%)` | Orange action: upload, create dataset, launch workflow, generate artifact. |
| `{colors.accent-hover}` | `hsl(24, 100%, 64%)` | Hover state for orange action. |
| `{colors.success}` | `hsl(136, 100%, 39%)` | Success, healthy QC, completed run, normal biological finding. |
| `{colors.cyan}` | `hsl(198, 74%, 54%)` | Data, metrics, visualization traces, embeddings, quantitative comparisons. |
| `{colors.purple}` | `hsl(260, 60%, 60%)` | AI reasoning, agent delegation, synthesis, model activity. |
| `{colors.yellow}` | `hsl(50, 85%, 65%)` | Pending review, warning, uncertainty, needs user confirmation. |
| `{colors.danger}` | `hsl(357.41, 100%, 22.75%)` | Critical error, destructive action, safety issue, failed validation. |
| `{colors.danger-soft}` | `hsl(357, 72%, 86%)` | Non-blocking danger badge background or warning fill. |
| `{colors.text-main}` | `hsl(210, 15%, 20%)` | Primary text. |
| `{colors.text-sub}` | `hsl(210, 10%, 35%)` | Secondary body and subdued headings. |
| `{colors.text-muted}` | `hsl(210, 8%, 48%)` | Metadata, timestamps, captions, inactive labels. |
| `{colors.on-primary}` | `hsl(0, 0%, 100%)` | Text on blue, orange, green, danger, or dark filled surfaces. |

### Pale Functional Tints

Use these tints for badges, step chips, selected but low-emphasis states, and status backgrounds.

| Token | Value | Role |
|---|---:|---|
| `{colors.primary-soft}` | `hsl(225, 84%, 88%)` | Selected thread, active sidebar row, query highlight. |
| `{colors.success-soft}` | `hsl(136, 92%, 80%)` | Passed QC, completed capability, normal finding badge. |
| `{colors.accent-soft}` | `hsl(24, 100%, 86%)` | Upload queued, new artifact, creation affordance. |
| `{colors.purple-soft}` | `hsl(260, 75%, 92%)` | AI reasoning badge, subagent card background. |
| `{colors.cyan-soft}` | `hsl(198, 80%, 88%)` | Dataset, chart, embedding, measurement badge. |
| `{colors.yellow-soft}` | `hsl(50, 90%, 86%)` | Pending review, uncertainty, caution. |

### Dark Product Surface

Dark surfaces are allowed only for code, terminal, sandbox output, execution logs, compact run inspectors, and embedded technical previews. Do not use dark backgrounds as the default workspace shell.

| Token | Value | Role |
|---|---:|---|
| `{colors.ink-dark}` | `hsl(210, 18%, 14%)` | Dark code/log background. |
| `{colors.ink-dark-elevated}` | `hsl(210, 16%, 20%)` | Inner panels inside dark technical surfaces. |
| `{colors.ink-dark-border}` | `hsl(210, 12%, 28%)` | Dark panel hairline. |
| `{colors.on-dark}` | `hsl(40, 24%, 97%)` | Primary text on dark. |
| `{colors.on-dark-muted}` | `hsl(210, 10%, 72%)` | Metadata, line numbers, inactive technical labels. |

### Usage Rules

- Use `{colors.bg-main}` for the page floor and `{colors.surface}` for cards and dialogs.
- Use `{colors.primary}` for the single highest-priority action in a region.
- Use `{colors.accent}` for creation/upload/generation actions that begin a new lab or artifact operation.
- Use purple only for AI/agent-specific states; do not turn it into a generic brand color.
- Use cyan for quantitative data and visualization accents; avoid using cyan for primary CTAs.
- Use red only when the user needs to stop, review, or understand risk.
- Do not use large gradients as normal UI surfaces. Subtle gradients are acceptable only inside a hero/welcome state or visualization preview.

## Typography

### Font Families

| Role | Font Stack | Use |
|---|---|---|
| UI / Body | `Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | All workspace UI, labels, forms, tables, chat text. |
| Technical | `"JetBrains Mono", "SFMono-Regular", Consolas, "Liberation Mono", monospace` | Code blocks, terminal output, tool logs, IDs, sequence snippets, JSON, shell commands. |
| Scientific Optional | `"Source Serif 4", Georgia, serif` | Long-form reports or generated PDF/article previews only. Do not use serif in dense workspace chrome. |

### Type Scale

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---:|---:|---:|---:|---|
| `{typography.display}` | 48px | 700 | 1.05 | `-0.04em` | Empty workspace welcome, project overview. |
| `{typography.heading-xl}` | 36px | 700 | 1.12 | `-0.035em` | Page-level titles, artifact report headings. |
| `{typography.heading-lg}` | 28px | 650 | 1.2 | `-0.025em` | Major panels, agent gallery headers. |
| `{typography.heading-md}` | 22px | 650 | 1.28 | `-0.015em` | Card group titles, dialog titles. |
| `{typography.heading-sm}` | 18px | 650 | 1.35 | `0` | Card titles, section labels. |
| `{typography.body-lg}` | 18px | 400 | 1.6 | `0` | Long-form generated report body, welcome copy. |
| `{typography.body-md}` | 16px | 400 | 1.55 | `0` | Chat messages, forms, descriptions. |
| `{typography.body-sm}` | 14px | 400 | 1.5 | `0` | Sidebar rows, metadata, dense card body. |
| `{typography.label}` | 13px | 600 | 1.35 | `0` | Field labels, table column labels. |
| `{typography.caption}` | 12px | 500 | 1.35 | `0` | Timestamps, file metadata, run IDs. |
| `{typography.label-uppercase}` | 11px | 700 | 1.3 | `0.06em` | Agent step chips, category tags, status labels. |
| `{typography.code}` | 13px | 400 | 1.55 | `0` | Code, logs, terminal output. |
| `{typography.button}` | 14px | 650 | 1 | `0` | Standard button text. |

### Typography Rules

- Use smaller, tighter type inside workspace panels. Do not put hero-scale type inside cards, sidebars, toolbars, or tables.
- Keep letter spacing at `0` for body and UI text. Negative tracking is allowed only for display and large headings.
- Use `font-mono` only when exact syntax, IDs, logs, sequences, or commands matter.
- Use tabular numerals for metrics, counts, token usage, cost, runtime, rows, and percentages.
- Keep generated biomedical explanations readable: 16px minimum body size, 1.55 line height, clear paragraph rhythm.

## Spacing, Grid, And Layout

### Spacing Scale

Use a 4px base unit with 8px as the normal visual rhythm.

| Token | Value | Use |
|---|---:|---|
| `{spacing.xxs}` | 4px | Icon/text gap, compact table cells. |
| `{spacing.xs}` | 8px | Small control gap, badge padding. |
| `{spacing.sm}` | 12px | Dense panel padding, toolbar gaps. |
| `{spacing.md}` | 16px | Default component padding. |
| `{spacing.lg}` | 24px | Cards, side panels, dialog body. |
| `{spacing.xl}` | 32px | Major card groups, empty states. |
| `{spacing.xxl}` | 48px | Welcome states, dashboard bands. |
| `{spacing.section}` | 64px | Major page sections outside the main workbench. |

### Workspace Shell

The primary app layout is a three-zone workbench:

1. **Navigation rail / sidebar**: agents, chats, recent threads, capabilities, settings.
2. **Conversation and execution center**: thread messages, composer, task state, active run.
3. **Inspector / artifact region**: files, citations, generated artifacts, code preview, result tables, run details.

The center region should remain readable at all times. Right-side inspectors may collapse to tabs or drawers on smaller screens. The sidebar may collapse to icons, but icons require tooltips.

### Containers

| Pattern | Width | Use |
|---|---:|---|
| `{layout.workbench-full}` | `100%` | Main workspace, split panes, canvas. |
| `{layout.content-md}` | `960px` max | Settings, agent creation, forms. |
| `{layout.content-lg}` | `1180px` max | Agent gallery, capability catalog, project overview. |
| `{layout.report}` | `760px` max | Generated narrative reports and citation-heavy summaries. |
| `{layout.table}` | `100%` with horizontal scroll | Dense result tables and file manifests. |

### Grid Rules

- Agent cards: 3-up desktop, 2-up tablet, 1-up mobile.
- Capability/tool cards: 4-up desktop if compact, 3-up for descriptive cards, 1-up mobile.
- Metrics: 4-up desktop, 2-up tablet, 1-up mobile.
- Artifact previews: use a split layout when there is enough width; stack preview above details on mobile.
- Tables should scroll horizontally rather than compressing important scientific identifiers.

## Elevation And Depth

Depth comes from surface contrast, borders, and occasional soft shadows.

| Level | Treatment | Use |
|---|---|---|
| Flat | No border, bg-main | Workspace floor, open report background. |
| Hairline | `1px {colors.border-soft}` | Default cards, tables, inputs, dividers. |
| Panel | `{colors.surface}` + hairline | Workspace cards, inspectors, file panels. |
| Raised | `{colors.surface}` + `0 8px 28px hsla(210, 30%, 20%, 0.08)` | Dialogs, popovers, command palette, hoverable artifact previews. |
| Technical dark | `{colors.ink-dark}` + inner hairline | Code, terminal, logs, sandbox output. |

Rules:

- Avoid heavy shadows in the main workbench.
- Use shadow only when an element floats above the layout: modal, popover, command palette, drag preview.
- Do not nest cards inside cards. If grouping is needed, use a header, divider, table row, tabs, or a full-width panel region.
- Use borders before shadows for dense biomedical data.

## Shapes

| Token | Value | Use |
|---|---:|---|
| `{rounded.xs}` | 4px | Tiny badges, code token backgrounds. |
| `{rounded.sm}` | 6px | Table row controls, compact menu items. |
| `{rounded.md}` | 8px | Buttons, inputs, tabs, side-nav rows. |
| `{rounded.lg}` | 12px | Cards, dialogs, file panels, inspectors. |
| `{rounded.xl}` | 16px | Large empty-state panels, upload zones. |
| `{rounded.2xl}` | 20px | Rare showcase/welcome panels only. |
| `{rounded.full}` | 9999px | Status dots, pills, avatars, progress markers. |

Rules:

- Buttons use 8px radius. Avoid pill buttons except for tags, badges, segmented status chips, or compact filters.
- Cards use 12px radius. Larger radius should be reserved for friendly onboarding or upload drop zones.
- Icon buttons are square with 8px radius unless they represent avatars or status dots.

## Iconography And Visual Assets

Use iconography to support scanning, not decoration.

- Use `lucide-react` icons for common actions: upload, search, settings, chat, delete, copy, download, external link, run, pause, stop, approve, file, database, chart, code, terminal, shield, warning, check.
- Use domain-specific icons sparingly: DNA helix, protein, flask, microscope, pill, gene, clinical cross. They should clarify object type, not decorate every card.
- Primary images/media in documentation or landing contexts should show real product states, generated artifacts, data visualizations, or biomedical objects. Avoid generic lab stock imagery inside the app shell.
- Use consistent 16px icons in sidebars and buttons; 20px for card headers; 24px only for empty states or feature selectors.
- Every icon-only button requires an accessible label and a visible tooltip on hover/focus.

## Core Components

### `app-shell`

The root workspace layout.

- Background: `{colors.bg-main}`.
- Structure: collapsible sidebar, sticky 64px header, main work area, optional inspector.
- Header uses a translucent surface with backdrop blur only if content scrolls underneath.
- Header should expose breadcrumbs, current thread/project status, model/agent indicator, and global actions.

### `workspace-sidebar`

Persistent navigation for chats, agents, capabilities, recent threads, and settings.

- Background: `{colors.surface-strong}` or a quiet variant of `{colors.bg-sub}`.
- Active item: `{colors.primary}` fill with `{colors.on-primary}` text for strong navigation; `{colors.primary-soft}` with `{colors.primary-active}` text for lower emphasis.
- Item height: 36-40px desktop, at least 44px on touch contexts.
- Collapsed mode: 48px rail, icon buttons with tooltips.
- Recent thread rows should truncate title, show timestamp on hover or secondary line, and preserve unread/running indicators.

### `workspace-header`

Sticky top bar for context and quick actions.

- Height: 64px.
- Border bottom: `1px {colors.border-soft}`.
- Left: breadcrumb or current workspace label.
- Center optional: active run status, model, or selected agent.
- Right: command palette, settings, theme, account, and high-priority contextual actions.
- Avoid large buttons here; use compact icon buttons and one primary text button at most.

### `thread-view`

Main conversation area.

- Max readable message width: 760-880px.
- Assistant messages may use full width when containing tables, code, charts, plans, or artifacts.
- User messages can be visually lighter; assistant/system/tool messages need clearer structure.
- Keep timestamps and token/debug metadata secondary by default; reveal more detail through expanders.
- Long biomedical answers should use headings, citation blocks, tables, and evidence lists.

### `message-user`

User-authored message bubble or block.

- Background: `{colors.surface}` or `{colors.primary-soft}` for selected/current.
- Text: `{colors.text-main}`.
- Radius: `{rounded.lg}`.
- Use right alignment only if the rest of the chat pattern already supports it; otherwise use aligned timeline blocks for better dense content.

### `message-agent`

Agent-authored output.

- Background: transparent for normal prose; `{colors.surface}` panel for structured outputs.
- Use clear section headers for findings, plan, artifacts, evidence, and next steps.
- Include citations or source affordances close to the claims they support.
- Do not use decorative avatars repeatedly in long threads. Use a compact agent label at the start of a run or message group.

### `prompt-composer`

Primary input at the bottom of a thread.

- Background: `{colors.surface}`.
- Border: `1px {colors.border-soft}`.
- Radius: `{rounded.lg}` or `{rounded.xl}` if it contains multiple tool rows.
- Minimum text area height: 56px; expands up to 40% viewport height.
- Controls: attach, capability/tool selector, model/agent mode, send, stop.
- Send button: `{colors.primary}`.
- Upload or new artifact action: `{colors.accent}` if separate from send.
- Disabled state must explain why on hover/focus when possible.

### `agent-card`

Represents a configured agent.

- Background: `{colors.surface}`.
- Border: `1px {colors.border-soft}`.
- Radius: `{rounded.lg}`.
- Header: icon tile, agent name, model badge.
- Body: 1-2 line description, enabled capability groups, memory and permission indicators if relevant.
- Footer: primary "Chat" action plus compact secondary actions.
- Running agent state: add a purple or blue status chip; avoid turning the whole card bright.

### `agent-welcome`

Empty state shown before a thread begins.

- Centered but compact; do not consume the whole viewport with marketing copy.
- Icon tile: `{colors.primary-soft}` background and `{colors.primary}` icon.
- Title: selected agent name.
- Body: concise description, 1-3 suggested prompts, and available capabilities.
- Suggested prompts should look like action chips or quiet cards, not large feature tiles.

### `capability-card`

Represents a capability, tool group, connector, data source, workflow template, or analysis module.

- Show capability name, domain, risk level if applicable, input/output shape, and enabled state.
- Use badges for biology domain: genetics, omics, protein, chemistry, clinical, literature, datasets, visualization.
- Use purple badge for AI workflow capabilities; cyan for data extraction/analysis; green for validation/QC; yellow for requires review.

### `file-card`

Represents uploaded or generated files.

- Include file type icon, name, size, source, upload/generation time, and processing state.
- For biomedical files, show recognized format when possible: FASTA, VCF, CSV, TSV, PDF, DOCX, PDB, SDF, JSON, image.
- Provide preview, cite, download/export, and remove actions.
- Processing status should use step chips: uploaded, parsing, indexed, available, failed.

### `artifact-card`

Represents generated outputs: report, chart, table, code, presentation, image, dataset, or notebook.

- Header: artifact type, title, last updated, provenance.
- Body: preview or summary.
- Footer: open, export, cite, compare, regenerate.
- Generated artifact cards should always retain a link back to the producing thread/run.

### `run-timeline`

Displays agent execution as a sequence of observable steps.

Use compact chips and rows:

| Step | Color | Meaning |
|---|---|---|
| Planning | `{colors.purple-soft}` / `{colors.purple}` | Agent is decomposing the task. |
| Searching | `{colors.cyan-soft}` / `{colors.cyan}` | Web, literature, database, or local index retrieval. |
| Reading | `{colors.primary-soft}` / `{colors.primary}` | Inspecting files, documents, or evidence. |
| Executing | `{colors.accent-soft}` / `{colors.accent}` | Running code, tool, sandbox, or workflow. |
| Delegating | `{colors.purple-soft}` / `{colors.purple}` | Subagent task started. |
| Writing | `{colors.primary-soft}` / `{colors.primary}` | Creating report, artifact, or code. |
| Verifying | `{colors.yellow-soft}` / `{colors.text-main}` | Checking results, tests, citations, or constraints. |
| Complete | `{colors.success-soft}` / `{colors.success}` | Finished successfully. |
| Failed | `{colors.danger-soft}` / `{colors.danger}` | Failed or blocked. |

Rules:

- Timeline rows show verb, target, elapsed time, and result.
- Tool calls can be collapsed by default but must be expandable.
- Long-running runs need visible progress even when exact percentage is unknown.
- Failed steps should offer retry, inspect logs, or copy error actions.

### `tool-call-card`

Displays one tool invocation.

- Header: tool name, status, duration, risk/permission badge if relevant.
- Body collapsed by default: command/query/input summary.
- Expanded: input, stdout/stderr/result, linked files, errors.
- Use monospace for commands, paths, JSON, IDs, and stack traces.
- Dangerous or permission-requiring tools use yellow or red framing depending on risk.

### `subagent-card`

Displays delegated work.

- Background: `{colors.purple-soft}` at low opacity or normal surface with purple badge.
- Show subagent type, assignment, status, started time, elapsed time, and result summary.
- If multiple subagents run in parallel, group them in a compact grid or table.
- Completed subagent output should be summarized first, with full transcript/details expandable.

### `evidence-panel`

Displays citations, sources, dataset provenance, and confidence.

- Use a right inspector or bottom drawer.
- Each evidence item shows title/name, source type, date/version if available, relevance, and linked claims.
- Biomedical claims should support confidence states: strong, moderate, weak, conflicting, unavailable.
- Conflicting evidence uses yellow, not red, unless it indicates a safety-critical issue.

### `data-table`

For research results, variants, genes, compounds, trials, files, and benchmark outputs.

- Header background: `{colors.surface-strong}`.
- Row height: 40-48px.
- Sticky header for long tables.
- Use tabular numerals and monospace for IDs.
- Support sorting, filtering, column visibility, export, and row details.
- Long identifiers must truncate with copy action and tooltip.
- Do not wrap sequence strings inside cells; use horizontal scroll or detail drawer.

### `metric-card`

For run health, QC, sample count, task count, token/cost, or data coverage.

- Large number in tabular numerals.
- Label beneath or above in `{typography.caption}`.
- Optional trend indicator with green/cyan/yellow/red.
- Avoid standalone huge metrics unless connected to a workflow or dataset.

### `chart-panel`

For visualization.

- Background: `{colors.surface}`.
- Border: `1px {colors.border-soft}`.
- Radius: `{rounded.lg}`.
- Use chart colors in this order: primary blue, cyan, success green, accent orange, purple, yellow, danger red.
- Always include axis labels, units, legend, and source/provenance where relevant.
- Avoid 3D charts for analytical views.
- Use red only for adverse, failed, critical, or clinically relevant negative states.

### `review-banner`

For high-stakes or uncertain results.

- Yellow for needs review, red for critical.
- Include clear reason, affected output, and action.
- Actions: review evidence, approve, revise, rerun, dismiss if safe.
- Do not use generic "Something went wrong" copy for biomedical workflows.

### `settings-dialog`

For preferences, model settings, tools, memory, permissions, and theme.

- Use a two-column layout: left nav, right settings page.
- Left nav background: `{colors.surface-strong}`.
- Inputs should be compact but touch-safe.
- Risky settings need explicit descriptions and confirmation states.

### `command-palette`

Fast keyboard-driven action surface.

- Raised panel with max width 640px.
- Search input at top.
- Group commands by workspace, agent, capabilities, files, artifacts, settings.
- Show keyboard shortcuts where available.
- Results use icons, title, subtitle, and optional badge.

## Biomedical Domain Patterns

### Biological Entity Chips

Use compact chips to distinguish domain objects:

| Entity | Accent |
|---|---|
| Gene / variant | Blue or cyan |
| Protein / structure | Purple |
| Compound / ligand | Orange |
| Pathway / ontology | Green |
| Clinical trial / phenotype | Yellow for review, blue for neutral |
| Literature / citation | Neutral surface with blue link |
| Dataset / assay | Cyan |

Entity chips should include copyable IDs when relevant: gene symbol, Ensembl ID, rsID, UniProt ID, PDB ID, ChEMBL ID, PMID, DOI, NCT ID.

### Confidence And Evidence

Use explicit labels:

- `High confidence`: strong evidence, replicated or authoritative source.
- `Moderate confidence`: plausible but limited evidence.
- `Low confidence`: weak, indirect, or sparse evidence.
- `Conflicting`: evidence points in multiple directions.
- `Needs review`: human judgment required before acting.

Never imply clinical certainty from exploratory outputs. UI copy should say "candidate", "associated", "reported", "predicted", or "requires validation" when appropriate.

### Safety And Risk

High-stakes biomedical actions need friction:

- Deleting files, changing memory, running shell commands, exporting sensitive data, or invoking external services should show clear confirmation.
- Clinical or patient-related outputs should be marked as research support unless the product explicitly supports regulated clinical workflows.
- Generated recommendations should expose sources and uncertainty.

## Interaction States

### Standard Component States

Every interactive component should define:

- Default
- Hover
- Focus visible
- Active/pressed
- Selected
- Disabled
- Loading
- Error

Focus rings should be visible and use `{colors.primary}` or `{colors.cyan}` depending on context. Do not set focus rings to transparent for new components.

### Loading

Use progressive disclosure:

- Under 500ms: no spinner needed.
- 500ms-2s: small inline loader.
- 2s-10s: show status text and current step.
- Over 10s: show run timeline, elapsed time, and cancel/stop affordance.

### Empty States

Empty states should be useful:

- Explain what object is empty.
- Offer one primary action.
- Offer 2-4 suggested prompts/actions if relevant.
- Use a small visual mark, not a giant illustration.

### Error States

Errors should include:

- What failed.
- Why, if known.
- Whether user data or files were affected.
- What the user can do next.
- Copy details / inspect logs for technical errors.

## Responsive Behavior

### Breakpoints

| Name | Width | Behavior |
|---|---:|---|
| Small mobile | `< 480px` | Single column, sidebar becomes drawer, inspector becomes bottom sheet, composer controls collapse. |
| Mobile | `480-767px` | Thread-first layout, cards 1-up, tables horizontally scroll. |
| Tablet | `768-1023px` | Sidebar may remain visible, inspector collapses, grids 2-up. |
| Desktop | `1024-1439px` | Full workbench: sidebar + center + optional inspector. |
| Wide | `>= 1440px` | Inspector can remain open; content max widths prevent overlong lines. |

### Mobile Rules

- Main task flow must remain usable with one thumb: send, stop, attach, open tools.
- Table-heavy views use horizontal scroll plus row detail drawer.
- Code/log panes use horizontal scroll, not forced wrapping.
- Do not shrink text below 14px for interactive UI or 16px for long-form reading.
- Bottom sheets need clear drag/close affordances and focus trapping.

## Accessibility

- Minimum contrast: WCAG AA for all text; stronger contrast for scientific tables and warnings.
- Touch target: 44px minimum on mobile; 36-40px acceptable for dense desktop controls.
- Keyboard: all controls, menus, dialogs, tabs, command palette, and tool-call expanders must be keyboard accessible.
- Icons: icon-only controls require `aria-label` and tooltip.
- Motion: respect reduced motion. Disable ambient animation, pulsing, and auto-scrolling effects when reduced motion is enabled.
- Color: never rely on color alone. Pair status colors with labels, icons, or text.
- Tables: use semantic table structures or accessible grid patterns with column headers.

## Motion

Motion should clarify state changes, not entertain.

| Token | Duration | Use |
|---|---:|---|
| `{motion.fast}` | 120ms | Button press, menu item active. |
| `{motion.base}` | 160ms | Hover, focus, small reveal. |
| `{motion.panel}` | 220ms | Drawer, popover, inspector resize. |
| `{motion.slow}` | 320ms | Workspace layout transition, large modal. |

Rules:

- Use ease-out for entrances and ease-in for exits.
- Avoid infinite attention animations except subtle running indicators.
- Agent activity can use small progress pulses, but the text state must carry the meaning.
- Do not animate large backgrounds in the main workspace.

## Copy Voice

The product voice is precise, calm, and research-oriented.

Use:

- "Run analysis"
- "Upload dataset"
- "Review evidence"
- "Inspect tool output"
- "Approve and continue"
- "Generated artifact"
- "Needs validation"
- "No source available"

Avoid:

- Hype words like "magical", "revolutionary", "instant breakthrough".
- Vague error copy like "Oops".
- Clinical overclaiming like "diagnosis confirmed" unless the workflow is explicitly regulated and validated.
- Anthropomorphic claims that hide execution details. Prefer "The agent is searching PubMed" over "Thinking deeply".

## Page Patterns

### Workspace Home

Purpose: get users into work quickly.

Required elements:

- Recent threads.
- Available agents.
- Primary action to start a new chat or workflow.
- Capability/tool health or configuration notice if needed.
- Optional biomedical example prompts.

Visual treatment:

- Use a constrained content width.
- Cards are useful object cards, not marketing feature cards.
- Keep one primary blue action and one orange upload/create action.

### Chat Thread

Purpose: conduct agent work with transparent execution.

Required elements:

- Sidebar context.
- Thread messages.
- Composer.
- Active run state.
- Stop/cancel while running.
- Artifact and file access.
- Evidence/citation access for research outputs.

### Agent Gallery

Purpose: select, create, or manage specialized agents.

Required elements:

- Agent cards.
- Filter/search by capability or domain.
- Model/tool/memory indicators.
- Create/edit/delete flows with confirmation for destructive changes.

### Capability Library

Purpose: discover, configure, and monitor available capabilities.

Required elements:

- Domain filters.
- Capability cards.
- Enabled/disabled state.
- Input/output summary.
- Required credentials or permissions.
- Risk/review marker for external calls or high-impact tools.

### Artifact Workspace

Purpose: inspect generated outputs.

Required elements:

- Preview.
- Metadata.
- Source thread/run.
- Export/download.
- Version history if available.
- Regenerate or revise action.

### Data/Research Table View

Purpose: analyze structured results.

Required elements:

- Search/filter/sort.
- Column visibility.
- Export.
- Row detail.
- Citation/provenance columns.
- Empty/error/loading states.

## Implementation Guidance

### Token Naming

Prefer semantic tokens over raw colors in components:

- Use `bg-background`, `bg-card`, `text-foreground`, `text-muted-foreground`, `border-border` for baseline shell.
- Add platform tokens for biomedical states: `bio-primary`, `bio-accent`, `bio-success`, `bio-cyan`, `bio-purple`, `bio-warning`, `bio-danger`.
- Do not inline raw HSL values inside individual components except while defining tokens.

### Component Construction

- Start from existing shared UI primitives where available.
- Keep workspace-specific components in the workspace component boundary.
- Use lucide icons for common actions.
- Use stable dimensions for sidebars, toolbars, icon buttons, cards, and table rows.
- Avoid layout shift when status labels change. Reserve space or use fixed-width/status chip patterns.
- Use responsive constraints instead of viewport-scaled font sizes.

### Data Visualization

- Use accessible chart libraries or semantic SVG/canvas wrappers with labels.
- Always preserve raw data access through table/export where charts summarize data.
- Do not invent data in production UI. Empty states and demos must be clearly marked as examples.

## Do's And Don'ts

### Do

- Use warm lab-paper backgrounds and bright surfaces.
- Keep the main workbench functional on first screen.
- Show agent progress as named steps.
- Make citations, files, tools, and artifacts traceable.
- Use blue for primary action and orange for upload/create/generate.
- Reserve purple for AI/agent states.
- Use cyan for data and green for successful biological/workflow states.
- Use compact, information-rich cards.
- Use tables and inspectors for dense scientific information.
- Keep code/log surfaces dark only when they improve readability.

### Don't

- Do not mention or imitate external brand systems in product docs or UI copy.
- Do not build marketing-style hero sections inside the workbench.
- Do not use decorative gradient blobs, bokeh, or abstract science wallpaper.
- Do not make every section a card; use tables, rows, tabs, dividers, and inspectors.
- Do not rely on spinners for long-running agent work.
- Do not use red for ordinary absence or neutral negative values.
- Do not hide provenance behind generic "sources" if claims are high-stakes.
- Do not use pill buttons as the default button shape.
- Do not shrink scientific identifiers until they become unreadable.
- Do not present exploratory AI output as validated clinical guidance.

## Iteration Checklist For Design Agents

Before proposing or implementing a new screen, verify:

- The screen has a clear primary user job.
- The first viewport exposes real workbench controls or data.
- Color roles follow this document.
- Agent/tool/run state is visible when relevant.
- Biomedical evidence and provenance are accessible.
- Empty, loading, error, disabled, and permission states are designed.
- Tables, code, and long identifiers remain readable.
- Mobile collapse behavior is specified.
- Keyboard and screen-reader affordances are included.
- No external brand names or visual signatures are referenced.

## Known Gaps

- The current repository theme uses a neutral OKLCH token set in `frontend/src/styles/globals.css`; implementation should map this document's HSL palette into those tokens or introduce a platform-specific token layer.
- The palette demo currently displays a few label values that do not exactly match its CSS variables. Treat the CSS variable values as the source of truth until the demo is cleaned up.
- Detailed visualization specs for specialized biomedical charts, such as genomic tracks, protein structure viewers, dose-response curves, pathway graphs, and survival plots, should be added when those components enter scope.
- Regulated clinical workflow requirements are not defined here. If the product moves beyond research support, add compliance, audit, and approval-specific UI rules before shipping those flows.
