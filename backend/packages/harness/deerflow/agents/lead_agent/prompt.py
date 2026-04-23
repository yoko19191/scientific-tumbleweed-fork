import asyncio
import logging
import threading
from datetime import datetime
from functools import lru_cache

from deerflow.config.agents_config import load_agent_soul
from deerflow.prompts.sections import (
    DEFAULT_AGENT_NAME,
    PLATFORM_DEVELOPER,
    collaboration_mechanics_section,
    conversation_craft_section,
    platform_persona_section,
)
from deerflow.skills import load_skills
from deerflow.skills.types import Skill
from deerflow.subagents import get_available_subagent_names

logger = logging.getLogger(__name__)

_ENABLED_SKILLS_REFRESH_WAIT_TIMEOUT_SECONDS = 5.0
_enabled_skills_lock = threading.Lock()
_enabled_skills_cache: list[Skill] | None = None
_enabled_skills_refresh_active = False
_enabled_skills_refresh_version = 0
_enabled_skills_refresh_event = threading.Event()


def _load_enabled_skills_sync(user_id: str | None = None) -> list[Skill]:
    return list(load_skills(enabled_only=True, user_id=user_id))


def _start_enabled_skills_refresh_thread() -> None:
    threading.Thread(
        target=_refresh_enabled_skills_cache_worker,
        name="deerflow-enabled-skills-loader",
        daemon=True,
    ).start()


def _refresh_enabled_skills_cache_worker() -> None:
    global _enabled_skills_cache, _enabled_skills_refresh_active

    while True:
        with _enabled_skills_lock:
            target_version = _enabled_skills_refresh_version

        try:
            skills = _load_enabled_skills_sync()
        except Exception:
            logger.exception("Failed to load enabled skills for prompt injection")
            skills = []

        with _enabled_skills_lock:
            if _enabled_skills_refresh_version == target_version:
                _enabled_skills_cache = skills
                _enabled_skills_refresh_active = False
                _enabled_skills_refresh_event.set()
                return

            # A newer invalidation happened while loading. Keep the worker alive
            # and loop again so the cache always converges on the latest version.
            _enabled_skills_cache = None


def _ensure_enabled_skills_cache() -> threading.Event:
    global _enabled_skills_refresh_active

    with _enabled_skills_lock:
        if _enabled_skills_cache is not None:
            _enabled_skills_refresh_event.set()
            return _enabled_skills_refresh_event
        if _enabled_skills_refresh_active:
            return _enabled_skills_refresh_event
        _enabled_skills_refresh_active = True
        _enabled_skills_refresh_event.clear()

    _start_enabled_skills_refresh_thread()
    return _enabled_skills_refresh_event


def _invalidate_enabled_skills_cache() -> threading.Event:
    global _enabled_skills_cache, _enabled_skills_refresh_active, _enabled_skills_refresh_version

    _get_cached_skills_prompt_section.cache_clear()
    with _enabled_skills_lock:
        _enabled_skills_cache = None
        _enabled_skills_refresh_version += 1
        _enabled_skills_refresh_event.clear()
        if _enabled_skills_refresh_active:
            return _enabled_skills_refresh_event
        _enabled_skills_refresh_active = True

    _start_enabled_skills_refresh_thread()
    return _enabled_skills_refresh_event


def prime_enabled_skills_cache() -> None:
    _ensure_enabled_skills_cache()


def warm_enabled_skills_cache(timeout_seconds: float = _ENABLED_SKILLS_REFRESH_WAIT_TIMEOUT_SECONDS) -> bool:
    if _ensure_enabled_skills_cache().wait(timeout=timeout_seconds):
        return True

    logger.warning("Timed out waiting %.1fs for enabled skills cache warm-up", timeout_seconds)
    return False


def _get_enabled_skills():
    with _enabled_skills_lock:
        cached = _enabled_skills_cache

    if cached is not None:
        return list(cached)

    _ensure_enabled_skills_cache()
    return []


def _skill_mutability_label(category: str) -> str:
    return "[custom, editable]" if category == "custom" else "[built-in]"


def clear_skills_system_prompt_cache() -> None:
    _invalidate_enabled_skills_cache()


async def refresh_skills_system_prompt_cache_async() -> None:
    await asyncio.to_thread(_invalidate_enabled_skills_cache().wait)


def _reset_skills_system_prompt_cache_state() -> None:
    global _enabled_skills_cache, _enabled_skills_refresh_active, _enabled_skills_refresh_version

    _get_cached_skills_prompt_section.cache_clear()
    with _enabled_skills_lock:
        _enabled_skills_cache = None
        _enabled_skills_refresh_active = False
        _enabled_skills_refresh_version += 1
        _enabled_skills_refresh_event.clear()


def _refresh_enabled_skills_cache() -> None:
    """Backward-compatible test helper for direct synchronous reload."""
    try:
        skills = _load_enabled_skills_sync()
    except Exception:
        logger.exception("Failed to load enabled skills for prompt injection")
        skills = []

    with _enabled_skills_lock:
        _enabled_skills_cache = skills
        _enabled_skills_refresh_active = False
        _enabled_skills_refresh_event.set()


def _build_skill_evolution_section(skill_evolution_enabled: bool) -> str:
    if not skill_evolution_enabled:
        return ""
    return """
## Skill Self-Evolution
After completing a task, consider creating or updating a skill when:
- The task required 5+ tool calls to resolve
- You overcame non-obvious errors or pitfalls
- The user corrected your approach and the corrected version worked
- You discovered a non-trivial, recurring workflow
If you used a skill and encountered issues not covered by it, patch it immediately.
Prefer patch over edit. Before creating a new skill, confirm with the user first.
Skip simple one-off tasks.
"""


def _build_subagent_section(max_concurrent: int) -> str:
    """Build the subagent system prompt section with dynamic concurrency limit.

    Args:
        max_concurrent: Maximum number of concurrent subagent calls allowed per response.

    Returns:
        Formatted subagent section string.
    """
    n = max_concurrent
    bash_available = "bash" in get_available_subagent_names()
    available_subagents = (
        "- **general-purpose**: For complex multi-step tasks — web research, literature synthesis, data analysis, code implementation, etc.\n"
        "- **explore**: For read-only investigation — codebase exploration, literature survey, background research, source comparison\n"
        "- **plan**: For designing implementation plans or research experiments — architecture decisions, experimental design, hypothesis decomposition\n"
        "- **verification**: For adversarial validation — code testing, statistical review, claim verification, reproducibility checks\n"
        "- **bash**: For command execution — git, build, test, data pipelines, scientific computing"
        if bash_available
        else "- **general-purpose**: For complex multi-step tasks — web research, literature synthesis, data analysis, code implementation, etc.\n"
        "- **explore**: For read-only investigation — codebase exploration, literature survey, background research, source comparison\n"
        "- **plan**: For designing implementation plans or research experiments — architecture decisions, experimental design, hypothesis decomposition\n"
        "- **verification**: For adversarial validation — code testing, statistical review, claim verification, reproducibility checks\n"
        "- **bash**: Not available in the current sandbox configuration. Use direct file/web tools or switch to AioSandboxProvider for isolated shell access."
    )
    direct_tool_examples = "bash, ls, read_file, web_search, etc." if bash_available else "ls, read_file, web_search, etc."
    direct_execution_example = (
        '# User asks: "Run the tests"\n# Thinking: Cannot decompose into parallel sub-tasks\n# → Execute directly\n\nbash("npm test")  # Direct execution, not task()'
        if bash_available
        else '# User asks: "Read the README"\n# Thinking: Single straightforward file read\n# → Execute directly\n\nread_file("/mnt/user-data/workspace/README.md")  # Direct execution, not task()'
    )
    return f"""<subagent_system>
**🚀 SUBAGENT MODE ACTIVE - DECOMPOSE, DELEGATE, SYNTHESIZE**

You are running with subagent capabilities enabled. Your role is to be a **task orchestrator**:
1. **DECOMPOSE**: Break complex tasks into parallel sub-tasks
2. **DELEGATE**: Launch multiple subagents simultaneously using parallel `task` calls
3. **SYNTHESIZE**: Collect and integrate results into a coherent answer

**CORE PRINCIPLE: Complex tasks should be decomposed and distributed across multiple subagents for parallel execution.**

**⛔ HARD CONCURRENCY LIMIT: MAXIMUM {n} `task` CALLS PER RESPONSE. THIS IS NOT OPTIONAL.**
- Each response, you may include **at most {n}** `task` tool calls. Any excess calls are **silently discarded** by the system — you will lose that work.
- **Before launching subagents, you MUST count your sub-tasks in your thinking:**
  - If count ≤ {n}: Launch all in this response.
  - If count > {n}: **Pick the {n} most important/foundational sub-tasks for this turn.** Save the rest for the next turn.
- **Multi-batch execution** (for >{n} sub-tasks):
  - Turn 1: Launch sub-tasks 1-{n} in parallel → wait for results
  - Turn 2: Launch next batch in parallel → wait for results
  - ... continue until all sub-tasks are complete
  - Final turn: Synthesize ALL results into a coherent answer
- **Example thinking pattern**: "I identified 6 sub-tasks. Since the limit is {n} per turn, I will launch the first {n} now, and the rest in the next turn."

**Available Subagents:**
{available_subagents}

**Your Orchestration Strategy:**

✅ **DECOMPOSE + PARALLEL EXECUTION (Preferred Approach):**

For complex queries, break them down into focused sub-tasks and execute in parallel batches (max {n} per turn):

**Example 1: "Why is Tencent's stock price declining?" (3 sub-tasks → 1 batch)**
→ Turn 1: Launch 3 subagents in parallel:
- Subagent 1: Recent financial reports, earnings data, and revenue trends
- Subagent 2: Negative news, controversies, and regulatory issues
- Subagent 3: Industry trends, competitor performance, and market sentiment
→ Turn 2: Synthesize results

**Example 2: "Compare 5 cloud providers" (5 sub-tasks → multi-batch)**
→ Turn 1: Launch {n} subagents in parallel (first batch)
→ Turn 2: Launch remaining subagents in parallel
→ Final turn: Synthesize ALL results into comprehensive comparison

**Example 3: "Refactor the authentication system"**
→ Turn 1: Launch 3 subagents in parallel:
- Subagent 1: Analyze current auth implementation and technical debt
- Subagent 2: Research best practices and security patterns
- Subagent 3: Review related tests, documentation, and vulnerabilities
→ Turn 2: Synthesize results

**Example 4: "Is transformer architecture better than LSTM for time series forecasting?" (research workflow)**
→ Turn 1: Launch 3 subagents in parallel:
- explore: Survey recent papers and benchmarks comparing transformers vs LSTMs for time series
- explore: Find uploaded datasets and check their characteristics (length, features, stationarity)
- plan: Design an experiment — model configs, evaluation metrics, train/test split, statistical tests
→ Turn 2: Execute the experiment:
- general-purpose: Implement and run the comparison experiment per the plan
- bash: Execute training scripts, collect metrics
→ Turn 3: Verify and synthesize:
- verification: Audit the results — check for data leakage, verify statistical significance, reproduce key numbers
→ Final: Synthesize into a structured research report with citations

✅ **USE Parallel Subagents (max {n} per turn) when:**
- **Complex research questions**: Requires multiple information sources or perspectives
- **Multi-aspect analysis**: Task has several independent dimensions to explore
- **Large codebases**: Need to analyze different parts simultaneously
- **Comprehensive investigations**: Questions requiring thorough coverage from multiple angles

❌ **DO NOT use subagents (execute directly) when:**
- **Task cannot be decomposed**: If you can't break it into 2+ meaningful parallel sub-tasks, execute directly
- **Ultra-simple actions**: Read one file, quick edits, single commands
- **Need immediate clarification**: Must ask user before proceeding
- **Meta conversation**: Questions about conversation history
- **Sequential dependencies**: Each step depends on previous results (do steps yourself sequentially)

**CRITICAL WORKFLOW** (STRICTLY follow this before EVERY action):
1. **COUNT**: In your thinking, list all sub-tasks and count them explicitly: "I have N sub-tasks"
2. **PLAN BATCHES**: If N > {n}, explicitly plan which sub-tasks go in which batch:
   - "Batch 1 (this turn): first {n} sub-tasks"
   - "Batch 2 (next turn): next batch of sub-tasks"
3. **EXECUTE**: Launch ONLY the current batch (max {n} `task` calls). Do NOT launch sub-tasks from future batches.
4. **REPEAT**: After results return, launch the next batch. Continue until all batches complete.
5. **SYNTHESIZE**: After ALL batches are done, synthesize all results.
6. **Cannot decompose** → Execute directly using available tools ({direct_tool_examples})

**⛔ VIOLATION: Launching more than {n} `task` calls in a single response is a HARD ERROR. The system WILL discard excess calls and you WILL lose work. Always batch.**

**Remember: Subagents are for parallel decomposition, not for wrapping single tasks.**

**How It Works:**
- The task tool runs subagents asynchronously in the background
- The backend automatically polls for completion (you don't need to poll)
- The tool call will block until the subagent completes its work
- Once complete, the result is returned to you directly

**Usage Example 1 - Single Batch (≤{n} sub-tasks):**

```python
# User asks: "Why is Tencent's stock price declining?"
# Thinking: 3 sub-tasks → fits in 1 batch

# Turn 1: Launch 3 subagents in parallel
task(description="Tencent financial data", prompt="...", subagent_type="general-purpose")
task(description="Tencent news & regulation", prompt="...", subagent_type="general-purpose")
task(description="Industry & market trends", prompt="...", subagent_type="general-purpose")
# All 3 run in parallel → synthesize results
```

**Usage Example 2 - Multiple Batches (>{n} sub-tasks):**

```python
# User asks: "Compare AWS, Azure, GCP, Alibaba Cloud, and Oracle Cloud"
# Thinking: 5 sub-tasks → need multiple batches (max {n} per batch)

# Turn 1: Launch first batch of {n}
task(description="AWS analysis", prompt="...", subagent_type="general-purpose")
task(description="Azure analysis", prompt="...", subagent_type="general-purpose")
task(description="GCP analysis", prompt="...", subagent_type="general-purpose")

# Turn 2: Launch remaining batch (after first batch completes)
task(description="Alibaba Cloud analysis", prompt="...", subagent_type="general-purpose")
task(description="Oracle Cloud analysis", prompt="...", subagent_type="general-purpose")

# Turn 3: Synthesize ALL results from both batches
```

**Counter-Example - Direct Execution (NO subagents):**

```python
{direct_execution_example}
```

**CRITICAL**:
- **Max {n} `task` calls per turn** - the system enforces this, excess calls are discarded
- Only use `task` when you can launch 2+ subagents in parallel
- Single task = No value from subagents = Execute directly
- For >{n} sub-tasks, use sequential batches of {n} across multiple turns
</subagent_system>"""


SYSTEM_PROMPT_TEMPLATE = """
<role>
你是 {agent_name}。
默认平台身份是“{default_agent_name}”，由{platform_developer}开发，定位是面向科学家和 AI 协作的新一代平台。
如果当前会话传入自定义 agent 名称，请保留该自定义身份，同时继承“{default_agent_name}”的平台气质和协作规范。
</role>

{platform_persona_section}

{conversation_craft_section}

{collaboration_mechanics_section}

{soul}
{memory_context}

<thinking_style>
- Think concisely and strategically about the user's request BEFORE taking action
- Break down the task: What is clear? What is ambiguous? What is missing?
- When using a tool directly, briefly consider what expert role best fits this tool before acting (e.g., statistician for data analysis, bibliographer for literature search).
{subagent_thinking}- Never write down your full final answer or report in thinking process, but only outline
- CRITICAL: After thinking, you MUST provide your actual response to the user. Thinking is for planning, the response is for delivery.
- Your response must contain the actual answer, not just a reference to what you thought about
</thinking_style>

{clarification_section}

{skills_section}

{deferred_tools_section}

{subagent_section}

<working_directory existed="true">
- User uploads: `/mnt/user-data/uploads` - Files uploaded by the user (automatically listed in context)
- User workspace: `/mnt/user-data/workspace` - Working directory for temporary files
- Output files: `/mnt/user-data/outputs` - Final deliverables must be saved here

**File Management:**
- Uploaded files are automatically listed in the <uploaded_files> section before each request
- Use `read_file` tool to read uploaded files using their paths from the list
- For PDF, PPT, Excel, and Word files, converted Markdown versions (*.md) are available alongside originals
- All temporary work happens in `/mnt/user-data/workspace`
- Treat `/mnt/user-data/workspace` as your default current working directory for coding and file-editing tasks
- When writing scripts or commands that create/read files from the workspace, prefer relative paths such as `hello.txt`, `../uploads/data.csv`, and `../outputs/report.md`
- Avoid hardcoding `/mnt/user-data/...` inside generated scripts when a relative path from the workspace is enough
- Final deliverables must be copied to `/mnt/user-data/outputs` and presented using `present_file` tool
{acp_section}
</working_directory>

{citations_section}
"""


def _get_memory_context(user_id: str | None = None) -> str:
    """Get memory context for injection into system prompt.

    Args:
        user_id: If provided, loads per-user memory. If None, loads global memory.

    Returns:
        Formatted memory context string wrapped in XML tags, or empty string if disabled.
    """
    try:
        from deerflow.agents.memory import format_memory_for_injection, get_memory_data
        from deerflow.config.memory_config import get_memory_config

        config = get_memory_config()
        if not config.enabled or not config.injection_enabled:
            return ""

        memory_data = get_memory_data(user_id)
        memory_content = format_memory_for_injection(memory_data, max_tokens=config.max_injection_tokens)

        if not memory_content.strip():
            return ""

        return f"""<memory>
{memory_content}
</memory>
"""
    except Exception as e:
        logger.error("Failed to load memory context: %s", e)
        return ""


@lru_cache(maxsize=32)
def _get_cached_skills_prompt_section(
    skill_signature: tuple[tuple[str, str, str, str], ...],
    available_skills_key: tuple[str, ...] | None,
    container_base_path: str,
    skill_evolution_section: str,
) -> str:
    filtered = [(name, description, category, location) for name, description, category, location in skill_signature if available_skills_key is None or name in available_skills_key]
    skills_list = ""
    if filtered:
        skill_items = "\n".join(
            f"    <skill>\n        <name>{name}</name>\n        <description>{description} {_skill_mutability_label(category)}</description>\n        <location>{location}</location>\n    </skill>"
            for name, description, category, location in filtered
        )
        skills_list = f"<available_skills>\n{skill_items}\n</available_skills>"
    return f"""<skill_system>
You have access to skills that provide optimized workflows for specific tasks. Each skill contains best practices, frameworks, and references to additional resources.

**Progressive Loading Pattern:**
1. When a user query matches a skill's use case, immediately call `read_file` on the skill's main file using the path attribute provided in the skill tag below
2. Read and understand the skill's workflow and instructions
3. The skill file contains references to external resources under the same folder
4. Load referenced resources only when needed during execution
5. Follow the skill's instructions precisely

**Skills are located at:** {container_base_path}
{skill_evolution_section}
{skills_list}

</skill_system>"""


def get_skills_prompt_section(available_skills: set[str] | None = None, user_id: str | None = None) -> str:
    """Generate the skills prompt section with available skills list.

    Args:
        available_skills: Optional set of skill names to filter by.
        user_id: If provided, loads skills with user-scoped enablement state.

    Returns:
        Formatted skills prompt section string.
    """
    skills = list(load_skills(enabled_only=True, user_id=user_id))

    try:
        from deerflow.config import get_app_config

        config = get_app_config()
        container_base_path = config.skills.container_path
        skill_evolution_enabled = config.skill_evolution.enabled
    except Exception:
        container_base_path = "/mnt/skills"
        skill_evolution_enabled = False

    if not skills and not skill_evolution_enabled:
        return ""

    if available_skills is not None and not any(skill.name in available_skills for skill in skills):
        return ""

    skill_signature = tuple((skill.name, skill.description, skill.category, skill.get_container_file_path(container_base_path)) for skill in skills)
    available_key = tuple(sorted(available_skills)) if available_skills is not None else None
    if not skill_signature and available_key is not None:
        return ""
    skill_evolution_section = _build_skill_evolution_section(skill_evolution_enabled)
    return _get_cached_skills_prompt_section(skill_signature, available_key, container_base_path, skill_evolution_section)


def get_agent_soul(agent_name: str | None, user_id: str | None = None) -> str:
    # Append SOUL.md (agent personality) if present
    soul = load_agent_soul(agent_name, user_id=user_id)
    if soul:
        return f"<soul>\n{soul}\n</soul>\n" if soul else ""
    return ""


def get_deferred_tools_prompt_section() -> str:
    """Generate <available-deferred-tools> block for the system prompt.

    Lists only deferred tool names so the agent knows what exists
    and can use tool_search to load them.
    Returns empty string when tool_search is disabled or no tools are deferred.
    """
    from deerflow.tools.builtins.tool_search import get_deferred_registry

    try:
        from deerflow.config import get_app_config

        if not get_app_config().tool_search.enabled:
            return ""
    except Exception:
        return ""

    registry = get_deferred_registry()
    if not registry:
        return ""

    names = "\n".join(e.name for e in registry.entries)
    return f"<available-deferred-tools>\n{names}\n</available-deferred-tools>"


def _build_acp_section() -> str:
    """Build the ACP agent prompt section, only if ACP agents are configured."""
    try:
        from deerflow.config.acp_config import get_acp_agents

        agents = get_acp_agents()
        if not agents:
            return ""
    except Exception:
        return ""

    return (
        "\n**ACP Agent Tasks (invoke_acp_agent):**\n"
        "- ACP agents (e.g. codex, claude_code) run in their own independent workspace — NOT in `/mnt/user-data/`\n"
        "- When writing prompts for ACP agents, describe the task only — do NOT reference `/mnt/user-data` paths\n"
        "- ACP agent results are accessible at `/mnt/acp-workspace/` (read-only) — use `ls`, `read_file`, or `bash cp` to retrieve output files\n"
        "- To deliver ACP output to the user: copy from `/mnt/acp-workspace/<file>` to `/mnt/user-data/outputs/<file>`, then use `present_file`"
    )


def _build_custom_mounts_section() -> str:
    """Build a prompt section for explicitly configured sandbox mounts."""
    try:
        from deerflow.config import get_app_config

        mounts = get_app_config().sandbox.mounts or []
    except Exception:
        logger.exception("Failed to load configured sandbox mounts for the lead-agent prompt")
        return ""

    if not mounts:
        return ""

    lines = []
    for mount in mounts:
        access = "read-only" if mount.read_only else "read-write"
        lines.append(f"- Custom mount: `{mount.container_path}` - Host directory mapped into the sandbox ({access})")

    mounts_list = "\n".join(lines)
    return f"\n**Custom Mounted Directories:**\n{mounts_list}\n- If the user needs files outside `/mnt/user-data`, use these absolute container paths directly when they match the requested directory"


def _apply_prompt_via_builder(
    subagent_enabled: bool = False,
    max_concurrent_subagents: int = 3,
    *,
    agent_name: str | None = None,
    user_id: str | None = None,
    available_skills: set[str] | None = None,
) -> str:
    """Build system prompt using the modular SystemPromptBuilder.

    This produces a prompt with a clear static/dynamic boundary for LLM API
    prompt caching, while including all the same content as the legacy template.
    """
    from deerflow.prompts import SystemPromptBuilder

    name = agent_name or DEFAULT_AGENT_NAME
    builder = SystemPromptBuilder(agent_name=name)

    # Soul
    soul = get_agent_soul(agent_name, user_id=user_id)
    if soul:
        builder.with_soul(soul)

    # Memory
    memory = _get_memory_context(user_id)
    if memory:
        builder.with_memory(memory)

    # Skills
    skills = get_skills_prompt_section(available_skills, user_id=user_id)
    if skills:
        builder.with_skills(skills)

    # Deferred tools
    deferred = get_deferred_tools_prompt_section()
    if deferred:
        builder.with_deferred_tools(deferred)

    # Environment
    builder.with_environment(cwd=None, date_str=datetime.now().strftime("%Y-%m-%d, %A"))

    # Subagent section
    if subagent_enabled:
        n = max_concurrent_subagents
        subagent_section = _build_subagent_section(n)
        builder.with_subagent(subagent_section, enabled=True)
        builder.with_specialized_agents(verification=True, explore=True, plan=True)

    # Clarification system (included as a dynamic section)
    builder.with_clarification(_build_clarification_section())

    # Working directory
    acp_section = _build_acp_section()
    custom_mounts_section = _build_custom_mounts_section()
    acp_and_mounts = "\n".join(s for s in (acp_section, custom_mounts_section) if s)
    builder.with_working_directory(_build_working_directory_section(acp_and_mounts))

    # Citations
    builder.with_citations(_build_citations_section())

    return builder.build()


def _build_clarification_section() -> str:
    return """<clarification_system>
当用户提出开放或模糊的问题时，不要猜全部答案，也不要连环追问。使用漏斗式缩放：

1. 用最强、最具体的方式复述问题（标注为 "working formulation"）。
2. 挑出当前置信度最高的证据，标注 {high | medium | low} 并给一句理由。
3. 据此给出 2-4 个互斥的下一步选项，各标明后果。
4. 只在"再往下走就要付出不可逆成本"时停下来问用户。
5. 每一步说明"目前没做什么、为什么没做"，让用户可以随时打断。

对于明确、可直接执行的请求，跳过漏斗，直接行动。
调用 `ask_clarification` 仅当：信息缺失会实质改变结果、选择有重大 trade-off、或操作不可逆。
不要把可以通过检查文件、配置、工具输出或对话上下文回答的问题抛给用户。
</clarification_system>"""


def _build_working_directory_section(acp_section: str) -> str:
    return f"""<working_directory existed="true">
- User uploads: `/mnt/user-data/uploads` - Files uploaded by the user
- User workspace: `/mnt/user-data/workspace` - Working directory for temporary files
- Output files: `/mnt/user-data/outputs` - Final deliverables must be saved here

**File Management:**
- Use `read_file` tool to read uploaded files using their paths
- For PDF, PPT, Excel, and Word files, converted Markdown versions (*.md) are available alongside originals
- All temporary work happens in `/mnt/user-data/workspace`
- Treat `/mnt/user-data/workspace` as your default current working directory for coding and file-editing tasks
- When writing scripts or commands that create/read files from the workspace, prefer relative paths such as `hello.txt`, `../uploads/data.csv`, and `../outputs/report.md`
- Avoid hardcoding `/mnt/user-data/...` inside generated scripts when a relative path from the workspace is enough
- Final deliverables must be copied to `/mnt/user-data/outputs` and presented using `present_file` tool
{acp_section}
</working_directory>"""


def _build_citations_section() -> str:
    return """<citations>
引用格式：`[citation:Author Year - Title](URL or file_path:line)` 紧跟在所支持的论断之后。
- 网络搜索结果必须附带引用。
- 长报告末尾汇总为 "Sources" 小节，每条必须是可点击的 Markdown 链接。
- 本地文件引用使用 `file_path:line` 格式。
</citations>"""


def apply_prompt_template(subagent_enabled: bool = False, max_concurrent_subagents: int = 3, *, agent_name: str | None = None, user_id: str | None = None, available_skills: set[str] | None = None) -> str:
    """Build the lead agent system prompt.

    Uses SystemPromptBuilder for modular assembly with static/dynamic cache
    boundary. Falls back to the legacy template only if the builder fails.
    """
    try:
        return _apply_prompt_via_builder(
            subagent_enabled=subagent_enabled,
            max_concurrent_subagents=max_concurrent_subagents,
            agent_name=agent_name,
            user_id=user_id,
            available_skills=available_skills,
        )
    except Exception:
        logger.warning("SystemPromptBuilder failed; falling back to legacy template", exc_info=True)
        return _apply_legacy_prompt_template(
            subagent_enabled=subagent_enabled,
            max_concurrent_subagents=max_concurrent_subagents,
            agent_name=agent_name,
            user_id=user_id,
            available_skills=available_skills,
        )


def _apply_legacy_prompt_template(subagent_enabled: bool = False, max_concurrent_subagents: int = 3, *, agent_name: str | None = None, user_id: str | None = None, available_skills: set[str] | None = None) -> str:
    """Legacy template-based prompt assembly (kept as fallback)."""
    # Get memory context
    memory_context = _get_memory_context(user_id)

    # Include subagent section only if enabled (from runtime parameter)
    n = max_concurrent_subagents
    subagent_section = _build_subagent_section(n) if subagent_enabled else ""

    # Add subagent reminder (kept for legacy template compatibility, now unused in template)
    subagent_reminder = ""

    # Add subagent thinking guidance if enabled
    subagent_thinking = (
        "- **DECOMPOSITION CHECK: Can this task be broken into 2+ parallel sub-tasks? If YES, COUNT them. "
        f"If count > {n}, you MUST plan batches of ≤{n} and only launch the FIRST batch now. "
        f"NEVER launch more than {n} `task` calls in one response.**\n"
        if subagent_enabled
        else ""
    )

    # Get skills section
    skills_section = get_skills_prompt_section(available_skills, user_id=user_id)

    # Get deferred tools section (tool_search)
    deferred_tools_section = get_deferred_tools_prompt_section()

    # Build ACP agent section only if ACP agents are configured
    acp_section = _build_acp_section()
    custom_mounts_section = _build_custom_mounts_section()
    acp_and_mounts_section = "\n".join(section for section in (acp_section, custom_mounts_section) if section)

    # Format the prompt with dynamic skills and memory
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        agent_name=agent_name or DEFAULT_AGENT_NAME,
        default_agent_name=DEFAULT_AGENT_NAME,
        platform_developer=PLATFORM_DEVELOPER,
        platform_persona_section=platform_persona_section(agent_name or DEFAULT_AGENT_NAME),
        conversation_craft_section=conversation_craft_section(),
        collaboration_mechanics_section=collaboration_mechanics_section(),
        soul=get_agent_soul(agent_name, user_id=user_id),
        clarification_section=_build_clarification_section(),
        citations_section=_build_citations_section(),
        skills_section=skills_section,
        deferred_tools_section=deferred_tools_section,
        memory_context=memory_context,
        subagent_section=subagent_section,
        subagent_reminder=subagent_reminder,
        subagent_thinking=subagent_thinking,
        acp_section=acp_and_mounts_section,
    )

    return prompt + f"\n<current_date>{datetime.now().strftime('%Y-%m-%d, %A')}</current_date>"
