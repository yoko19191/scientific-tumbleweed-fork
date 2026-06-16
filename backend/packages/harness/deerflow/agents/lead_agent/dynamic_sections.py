"""Lead-agent dynamic prompt sections."""

from __future__ import annotations

import logging

from deerflow.config.agents_config import load_agent_soul
from deerflow.prompts.render import render_partial
from deerflow.subagents.registry import get_available_subagent_names

logger = logging.getLogger(__name__)


def build_subagent_section(max_concurrent: int, *, app_config=None, bash_available: bool | None = None) -> str:
    """Build the subagent system prompt section with dynamic concurrency limit."""
    n = max_concurrent
    if bash_available is None:
        bash_available = "bash" in get_available_subagent_names(app_config=app_config)
    available_subagents = (
        "- **general-purpose**: For complex multi-step tasks — web research, literature synthesis, data analysis, code implementation, etc.\n"
        "- **explore**: For investigation with optional workspace actions — codebase exploration, literature survey, command execution, file notes/artifacts\n"
        "- **plan**: For designing implementation plans or research experiments — architecture decisions, experimental design, hypothesis decomposition\n"
        "- **verification**: For adversarial validation — code testing, statistical review, claim verification, reproducibility checks\n"
        "- **bash**: For command execution — git, build, test, data pipelines, scientific computing"
        if bash_available
        else "- **general-purpose**: For complex multi-step tasks — web research, literature synthesis, data analysis, code implementation, etc.\n"
        "- **explore**: For investigation with optional workspace actions — codebase exploration, literature survey, command execution, file notes/artifacts\n"
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
    return render_partial(
        "subagent_section.j2",
        n=n,
        available_subagents=available_subagents,
        direct_tool_examples=direct_tool_examples,
        direct_execution_example=direct_execution_example,
    )


def get_agent_soul(agent_name: str | None, user_id: str | None = None) -> str:
    soul = load_agent_soul(agent_name, user_id=user_id)
    if soul:
        return f"<soul>\n{soul}\n</soul>\n" if soul else ""
    return ""


def get_deferred_tools_prompt_section(*, deferred_names: frozenset[str] = frozenset()) -> str:
    """Generate <available-deferred-tools> from an explicit deferred-name set."""
    from deerflow.tools.builtins.tool_search import get_deferred_tools_prompt_section as render_deferred_tools

    return render_deferred_tools(deferred_names=deferred_names)


def build_acp_section(*, app_config=None) -> str:
    """Build the ACP agent prompt section, only if ACP agents are configured."""
    if app_config is None:
        try:
            from deerflow.config.acp_config import get_acp_agents

            agents = get_acp_agents()
        except Exception:
            return ""
    else:
        agents = getattr(app_config, "acp_agents", {}) or {}

    if not agents:
        return ""

    return (
        "\n**ACP Agent Tasks (invoke_acp_agent):**\n"
        "- ACP agents (e.g. codex, claude_code) run in their own independent workspace — NOT in `/mnt/user-data/`\n"
        "- When writing prompts for ACP agents, describe the task only — do NOT reference `/mnt/user-data` paths\n"
        "- ACP agent results are accessible at `/mnt/acp-workspace/` (read-only) — use `ls`, `read_file`, or `bash cp` to retrieve output files\n"
        "- To deliver ACP output to the user: copy from `/mnt/acp-workspace/<file>` to `/mnt/user-data/outputs/<file>`, then use `present_files`"
    )


def build_custom_mounts_section(*, app_config=None) -> str:
    """Build a prompt section for explicitly configured sandbox mounts."""
    if app_config is None:
        try:
            from deerflow.config import get_app_config

            config = get_app_config()
        except Exception:
            logger.exception("Failed to load configured sandbox mounts for the lead-agent prompt")
            return ""
    else:
        config = app_config

    mounts = config.sandbox.mounts or []

    if not mounts:
        return ""

    lines = []
    for mount in mounts:
        access = "read-only" if mount.read_only else "read-write"
        lines.append(f"- Custom mount: `{mount.container_path}` - Host directory mapped into the sandbox ({access})")

    mounts_list = "\n".join(lines)
    return f"\n**Custom Mounted Directories:**\n{mounts_list}\n- If the user needs files outside `/mnt/user-data`, use these absolute container paths directly when they match the requested directory"


def build_clarification_section() -> str:
    return render_partial("clarification.j2")


def build_working_directory_section(acp_section: str) -> str:
    return render_partial("working_directory.j2", acp_section=acp_section)


def build_self_update_section(agent_name: str | None) -> str:
    if not agent_name:
        return ""
    return render_partial("self_update.j2")


def build_citations_section() -> str:
    return render_partial("citations.j2")
