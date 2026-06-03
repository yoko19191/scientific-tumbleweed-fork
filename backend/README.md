# Scientific Tumbleweed Backend

Scientific Tumbleweed is a LangGraph-based AI super agent with sandbox execution, persistent memory, and extensible tool integration. The backend enables AI agents to execute code, browse the web, manage files, delegate tasks to subagents, and retain context across conversations - all in isolated, per-thread environments.

---

## Architecture

```
                        ┌──────────────────────────────────────┐
                        │          Nginx (Port 2026)           │
                        │      Unified reverse proxy           │
                        └───────┬──────────────────┬───────────┘
                                │                  │
              /api/langgraph/*  │                  │  /api/* (other)
                                ▼                  ▼
               ┌──────────────────────────────────────────────┐
               │             Gateway API (8001)               │
               │  FastAPI REST + LangGraph-compatible runtime │
               │                                              │
               │ Models, MCP, Skills, Memory, Uploads,       │
               │ Artifacts, Threads, Runs, Streaming          │
               │                                              │
               │ ┌────────────────┐                           │
               │ │  Lead Agents   │                           │
               │ │  ┌──────────┐  │                           │
               │ │  │Middleware│  │                           │
               │ │  │  Chain   │  │                           │
               │ │  └──────────┘  │                           │
               │ │  ┌──────────┐  │                           │
               │ │  │  Tools   │  │                           │
               │ │  └──────────┘  │                           │
               │ │  ┌──────────┐  │                           │
               │ │  │Subagents │  │                           │
               │ │  └──────────┘  │                           │
               │ └────────────────┘                           │
               └──────────────────────────────────────────────┘
```

**Request Routing** (via Nginx):
- `/api/langgraph/*` → Gateway API - LangGraph-compatible agent interactions, threads, runs, and streaming translated to native `/api/*` routers
- `/api/*` (other) → Gateway API - models, MCP, skills, memory, artifacts, uploads, thread-local cleanup
- `/` (non-API) → Frontend - Next.js web interface

---

## Core Components

### Agent Modules

The backend exposes two LangGraph lead-agent runtime entry points: `chat_lead_agent`, created via `make_chat_lead_agent(config)`, and `computer_lead_agent`, created via `make_computer_lead_agent(config)`. `lead_agent/base.py` owns the shared `create_agent` assembly, `lead_agent/config.py` owns typed variant profiles, and `lead_agent/chat.py` / `lead_agent/computer.py` declare the concrete variants. Chat uses local filesystem-backed file tools plus web/academic search, plan mode, and non-exec subagents; Computer keeps the full sandbox/tool surface for workspace automation. Both combine:

- **Dynamic model selection** with thinking and vision support
- **Middleware chain** for cross-cutting concerns, ordered by the canonical builder
- **Tool system** with sandbox, MCP, community, and built-in tools
- **Subagent delegation** for parallel task execution
- **System prompt** with skills injection, memory context, and working directory guidance

Follow-up suggestions and automatic titles live in harness modules too: `agents/suggestion_agent` owns suggestion prompt rendering and JSON parsing, while `agents/title_agent` owns title prompt rendering, model invocation, parsing, and fallback. Gateway routers and middlewares stay thin boundary layers around those modules.

### Middleware Chain

Middlewares execute in strict order, each handling a specific concern:

| # | Middleware | Purpose |
|---|-----------|---------|
| 1 | **ThreadDataMiddleware** | Creates per-thread isolated directories (workspace, uploads, outputs) |
| 2 | **UploadsMiddleware** | Injects newly uploaded files into conversation context |
| 3 | **SandboxMiddleware** | Acquires sandbox environment for code execution |
| 4 | **DanglingToolCallMiddleware** | Repairs missing tool responses after interruptions |
| 5 | **LLMErrorHandlingMiddleware** | Normalizes model/provider failures into recoverable responses |
| 6 | **GuardrailMiddleware** | Authorizes tool calls when guardrails are configured (optional) |
| 7 | **SandboxAuditMiddleware** | Audits sandboxed operations before tool execution continues |
| 8 | **ToolErrorHandlingMiddleware** | Converts tool exceptions into error ToolMessages |
| 9 | **PermissionMiddleware** | Applies configured tool permission policy (optional) |
| 10 | **HookMiddleware** | Runs configured pre/post tool hooks (optional) |
| 11 | **DynamicContextMiddleware** | Injects runtime reminders without changing the static prompt |
| 12 | **SummarizationMiddleware** | Reduces context when approaching token limits (optional) |
| 13 | **CompactionMiddleware** | Compresses context when configured (optional) |
| 14 | **TodoListMiddleware** | Tracks multi-step tasks in plan mode (optional) |
| 15 | **TokenUsageMiddleware** | Records token usage metrics when enabled |
| 16 | **TitleMiddleware** | Auto-generates conversation titles after first exchange |
| 17 | **MemoryMiddleware** | Queues conversations for async memory extraction |
| 18 | **ViewImageMiddleware** | Injects image data for vision-capable models (conditional) |
| 19 | **DeferredToolFilterMiddleware** | Hides deferred tool schemas until tool search is enabled |
| 20 | **SubagentLimitMiddleware** | Enforces parallel subagent call limits (optional) |
| 21 | **LoopDetectionMiddleware** | Detects repeated tool-call loops and forces a final answer |
| 22 | **SafetyFinishReasonMiddleware** | Suppresses unsafe provider-terminated tool calls |
| 23 | **ClarificationMiddleware** | Intercepts clarification requests and interrupts execution (must be last) |

### Sandbox System

Per-thread isolated execution with virtual path translation:

- **Abstract interface**: `execute_command`, `read_file`, `write_file`, `list_dir`
- **Providers**: `LocalSandboxProvider` (filesystem) and `AioSandboxProvider` (Docker, in community/). Async runtime paths use async sandbox lifecycle hooks so startup, readiness polling, and release do not block the event loop.
- **Virtual paths**: `/mnt/user-data/{workspace,uploads,outputs}` → thread-specific physical directories
- **Skills path**: `/mnt/skills` → `deer-flow/skills/` directory
- **Skills loading**: Recursively discovers nested `SKILL.md` files under `skills/{public,custom}` and preserves nested container paths
- **File-write safety**: `str_replace` serializes read-modify-write per `(sandbox.id, path)` so isolated sandboxes keep concurrency even when virtual paths match
- **Tools**: `bash`, `ls`, `read_file`, `write_file`, `str_replace` (`write_file` overwrites by default and exposes `append` for end-of-file writes; `bash` is disabled by default when using `LocalSandboxProvider`; use `AioSandboxProvider` for isolated shell access)

### Subagent System

Async task delegation with concurrent execution:

- **Built-in agents**: `general-purpose` (full toolset) and `bash` (command specialist, exposed only when shell access is available)
- **Concurrency**: Max 3 subagents per turn, 15-minute timeout
- **Execution**: Background thread pools with status tracking and SSE events
- **Flow**: Agent calls `task()` tool → executor runs subagent in background → polls for completion → returns result

### Custom Agent Store

Custom agents are stored through OpenDAL under
`custom-agents/{user_id|__global__}/{name}/`. `CustomAgentStore` owns name
normalization, config YAML reads/writes, `SOUL.md` reads/writes, existence
checks, prefix deletion, and create-time cleanup. Gateway routes and
`setup_agent` / `update_agent` tools use that store instead of hand-editing
agent objects.

### Workspace Apps

Workspace apps are registered through the harness-level `deerflow.apps`
registry and exposed by Gateway at `GET /api/apps`. The registry starts empty;
each real app should live in its own module and register an `AppDefinition`
instead of relying on frontend placeholder cards.

### Memory System

LLM-powered persistent context retention across conversations:

- **Automatic extraction**: Analyzes conversations for user context, facts, and preferences
- **Structured storage**: User context (work, personal, top-of-mind), history, and confidence-scored facts
- **Debounced updates**: Batches updates to minimize LLM calls (configurable wait time)
- **System prompt injection**: Top facts + context injected into agent prompts
- **Storage**: JSON file with mtime-based cache invalidation

### Tool Ecosystem

| Category | Tools |
|----------|-------|
| **Sandbox** | `bash`, `ls`, `read_file`, `write_file`, `str_replace` |
| **Built-in** | `present_files`, `ask_clarification`, `view_image`, `task` (subagent) |
| **Community** | Tavily (web search), Jina AI (web fetch), Firecrawl (scraping), DuckDuckGo (image search) |
| **MCP** | Any Model Context Protocol server (stdio, SSE, HTTP transports) |
| **Skills** | Domain-specific workflows injected via system prompt |

### Gateway API

FastAPI application providing REST endpoints for frontend integration:

| Route | Purpose |
|-------|---------|
| `GET /api/models` | List available LLM models |
| `GET /api/apps` | List registered workspace app modules |
| `GET/PUT /api/mcp/config` | Manage MCP server configurations |
| `GET/PUT /api/skills` | List and manage skills |
| `POST /api/skills/install` | Install skill from `.skill` archive |
| `GET /api/memory` | Retrieve memory data |
| `POST /api/memory/reload` | Force memory reload |
| `GET /api/memory/config` | Memory configuration |
| `GET /api/memory/status` | Combined config + data |
| `POST /api/threads/{id}/uploads` | Upload files (auto-converts PDF/PPT/Excel/Word to Markdown, rejects directory paths, auto-renames duplicate filenames in one request) |
| `GET /api/threads/{id}/uploads/list` | List uploaded files |
| `DELETE /api/threads/{id}` | Delete Scientific Tumbleweed-managed local thread data after LangGraph thread deletion; unexpected failures are logged server-side and return a generic 500 detail |
| `GET /api/threads/{id}/artifacts/{path}` | Serve generated artifacts |

Thread-scoped Gateway routes resolve uploads, artifacts, local cleanup, and `.skill`
installation through an authenticated thread resource, so filesystem access is bound
to the server-verified owner before any `/mnt/user-data/...` path is translated.

Gateway run launch keeps LangGraph `context` mode and legacy `configurable` mode
separate. Request body runtime options are merged through a single service helper,
while `RuntimeContext` installs canonical `thread_id`, `run_id`, `user_id`,
`agent_name`, and `app_config` before the agent executes.

Run wait endpoints read checkpoint-backed final state through
`deerflow.runtime.runs.checkpoints`, and stream responses format SSE frames
through `deerflow.runtime.format_sse_frame()`. Persistent run hydration maps
`RunStore` rows through `RunRecord.from_store_row()` before the Gateway shapes
HTTP response models.

Agent middleware entry points resolve concrete middleware instances locally, then
delegate final ordering to `deerflow.agents.middleware_builder`. This keeps
`make_chat_lead_agent()`, `make_computer_lead_agent()`, and the SDK
`create_deerflow_agent()` aligned on ordering, extra middleware insertion, and
the clarification-last invariant.

### IM Channels

The IM bridge supports Feishu, Slack, and Telegram. Slack and Telegram still use the final `runs.wait()` response path, while Feishu now streams through `runs.stream(["messages-tuple", "values"])` and updates a single in-thread card in place.

For Feishu card updates, Scientific Tumbleweed stores the running card's `message_id` per inbound message and patches that same card until the run finishes, preserving the existing `OK` / `DONE` reaction flow.

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- API keys for your chosen LLM provider

### Installation

```bash
cd scientific-tumbleweed-monorepo

# Copy configuration files
cp config.example.yaml config.yaml

# Install backend dependencies
cd backend
make install
```

### Configuration

Edit `config.yaml` in the project root:

```yaml
models:
  - name: gpt-4o
    display_name: GPT-4o
    use: langchain_openai:ChatOpenAI
    model: gpt-4o
    api_key: $OPENAI_API_KEY
    supports_thinking: false
    supports_vision: true

  - name: gpt-5-responses
    display_name: GPT-5 (Responses API)
    use: langchain_openai:ChatOpenAI
    model: gpt-5
    api_key: $OPENAI_API_KEY
    use_responses_api: true
    output_version: responses/v1
    supports_vision: true
```

Set your API keys:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Running

**Full Application** (from project root):

```bash
make dev  # Starts LangGraph + Gateway + Frontend + Nginx
```

Access at: http://localhost:2026

**Backend Only** (from backend directory):

```bash
# Terminal 1: LangGraph server
make dev

# Terminal 2: Gateway API
make gateway
```

Direct access: LangGraph at http://localhost:2024, Gateway at http://localhost:8001

---

## Project Structure

```
backend/
├── src/
│   ├── agents/                  # Agent system
│   │   ├── lead_agent/         # Main agent (factory, prompts)
│   │   ├── middlewares/        # Runtime middleware components
│   │   ├── middleware_builder.py # Canonical middleware ordering
│   │   ├── memory/             # Memory extraction & storage
│   │   └── thread_state.py    # ThreadState schema
│   ├── gateway/                # FastAPI Gateway API
│   │   ├── app.py             # Application setup
│   │   └── routers/           # 6 route modules
│   ├── sandbox/                # Sandbox execution
│   │   ├── local/             # Local filesystem provider
│   │   ├── sandbox.py         # Abstract interface
│   │   ├── tools.py           # bash, ls, read/write/str_replace
│   │   └── middleware.py      # Sandbox lifecycle
│   ├── subagents/              # Subagent delegation
│   │   ├── builtins/          # general-purpose, bash agents
│   │   ├── executor.py        # Background execution engine
│   │   └── registry.py        # Agent registry
│   ├── tools/builtins/         # Built-in tools
│   ├── mcp/                    # MCP protocol integration
│   ├── models/                 # Model factory
│   ├── skills/                 # Skill discovery & loading
│   ├── config/                 # Configuration system
│   ├── community/              # Community tools & providers
│   ├── reflection/             # Dynamic module loading
│   └── utils/                  # Utilities
├── docs/                       # Documentation
├── tests/                      # Test suite
├── langgraph.json              # LangGraph server configuration
├── pyproject.toml              # Python dependencies
├── Makefile                    # Development commands
└── Dockerfile                  # Container build
```

---

## Configuration

### Main Configuration (`config.yaml`)

Place in project root. Config values starting with `$` resolve as environment variables.

Key sections:
- `models` - LLM configurations with class paths, API keys, thinking/vision flags
- `tools` - Tool definitions with module paths and groups
- `tool_groups` - Logical tool groupings
- `sandbox` - Execution environment provider
- `skills` - Skills directory paths
- `title` - Auto-title generation settings
- `summarization` - Context summarization settings; default summaries are structured five-field continuation records
- `subagents` - Subagent system (enabled/disabled)
- `memory` - Memory system settings (enabled, storage, debounce, facts limits)

Provider note:
- `models[*].use` references provider classes by module path (for example `langchain_openai:ChatOpenAI`).
- If a provider module is missing, Scientific Tumbleweed now returns an actionable error with install guidance (for example `uv add langchain-google-genai`).

### Extensions Configuration (`extensions_config.json`)

MCP servers and skill states in a single file:

```json
{
  "mcpServers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"}
    },
    "secure-http": {
      "enabled": true,
      "type": "http",
      "url": "https://api.example.com/mcp",
      "oauth": {
        "enabled": true,
        "token_url": "https://auth.example.com/oauth/token",
        "grant_type": "client_credentials",
        "client_id": "$MCP_OAUTH_CLIENT_ID",
        "client_secret": "$MCP_OAUTH_CLIENT_SECRET"
      }
    }
  },
  "skills": {
    "pdf-processing": {"enabled": true}
  }
}
```

The repo-level file is the developer-level global config. Logged-in user MCP
and skill enablement changes are stored as per-user OpenDAL overrides at
`user-extensions/{user_id}/extensions_config.json`, then merged through
`get_effective_extensions_config()` so MCP and skills share the same effective
view.

### Environment Variables

- `DEER_FLOW_CONFIG_PATH` - Override config.yaml location
- `DEER_FLOW_EXTENSIONS_CONFIG_PATH` - Override extensions_config.json location
- Model API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, etc.
- Tool API keys: `TAVILY_API_KEY`, `GITHUB_TOKEN`, etc.

### LangSmith Tracing

Scientific Tumbleweed has built-in [LangSmith](https://smith.langchain.com) integration for observability. When enabled, all LLM calls, agent runs, tool executions, and middleware processing are traced and visible in the LangSmith dashboard.

**Setup:**

1. Sign up at [smith.langchain.com](https://smith.langchain.com) and create a project.
2. Add the following to your `.env` file in the project root:

```bash
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxx
LANGSMITH_PROJECT=xxx
```

**Legacy variables:** The `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`, and `LANGCHAIN_ENDPOINT` variables are also supported for backward compatibility. `LANGSMITH_*` variables take precedence when both are set.

### Langfuse Tracing

Scientific Tumbleweed also supports [Langfuse](https://langfuse.com) observability for LangChain-compatible runs.

Add the following to your `.env` file:

```bash
LANGFUSE_TRACING=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxx
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

If you are using a self-hosted Langfuse deployment, set `LANGFUSE_BASE_URL` to your Langfuse host.

### Dual Provider Behavior

If both LangSmith and Langfuse are enabled, Scientific Tumbleweed initializes and attaches both callbacks so the same run data is reported to both systems.

If a provider is explicitly enabled but required credentials are missing, or the provider callback cannot be initialized, Scientific Tumbleweed raises an error when tracing is initialized during model creation instead of silently disabling tracing.

**Docker:** In `docker-compose.yaml`, tracing is disabled by default (`LANGSMITH_TRACING=false`). Set `LANGSMITH_TRACING=true` and/or `LANGFUSE_TRACING=true` in your `.env`, together with the required credentials, to enable tracing in containerized deployments.

---

## Development

### Commands

```bash
make install    # Install dependencies
make dev        # Run LangGraph server (port 2024)
make gateway    # Run Gateway API (port 8001)
make lint       # Run linter (ruff)
make format     # Format code (ruff)
```

### Code Style

- **Linter/Formatter**: `ruff`
- **Line length**: 240 characters
- **Python**: 3.12+ with type hints
- **Quotes**: Double quotes
- **Indentation**: 4 spaces

### Testing

```bash
uv run pytest
```

---

## Technology Stack

- **LangGraph** (1.0.6+) - Agent framework and multi-agent orchestration
- **LangChain** (1.2.3+) - LLM abstractions and tool system
- **FastAPI** (0.115.0+) - Gateway REST API
- **langchain-mcp-adapters** - Model Context Protocol support
- **agent-sandbox** - Sandboxed code execution
- **markitdown** - Multi-format document conversion
- **tavily-python** / **firecrawl-py** - Web search and scraping

---

## Documentation

- [Configuration Guide](docs/CONFIGURATION.md)
- [Architecture Details](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [File Upload](docs/FILE_UPLOAD.md)
- [Path Examples](docs/PATH_EXAMPLES.md)
- [Context Summarization](docs/summarization.md)
- [Plan Mode](docs/plan_mode_usage.md)
- [Setup Guide](docs/SETUP.md)

---

## License

See the [LICENSE](../LICENSE) file in the project root.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
