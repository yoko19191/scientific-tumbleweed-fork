import logging

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from deerflow.config.agents_config import AgentConfig, CustomAgentStore, normalize_agent_name
from deerflow.runtime.user_context import resolve_runtime_user_id
from deerflow.tools.types import Runtime

logger = logging.getLogger(__name__)


@tool(parse_docstring=True)
def setup_agent(
    soul: str,
    description: str,
    runtime: Runtime,
) -> Command:
    """Setup the custom Scientific Tumbleweed agent.

    Args:
        soul: Full SOUL.md content defining the agent's personality and behavior.
        description: One-line description of what the agent does.
    """

    agent_name: str | None = runtime.context.get("agent_name") if runtime.context else None

    try:
        agent_name = normalize_agent_name(agent_name) if agent_name else None

        if agent_name:
            user_id = resolve_runtime_user_id(runtime)
            CustomAgentStore().create_agent(
                AgentConfig(name=agent_name, description=description or ""),
                soul,
                user_id=user_id,
            )
        else:
            # The bootstrap/default-agent setup path historically wrote to
            # base_dir/SOUL.md. Custom agent creation is the only active caller
            # for setup_agent in the gateway, so keep the no-name path disabled
            # rather than silently writing an unscoped object-store key.
            raise ValueError("setup_agent requires an agent_name in runtime context.")

        logger.info("[agent_creator] Created agent '%s' for user %s", agent_name, resolve_runtime_user_id(runtime))
        return Command(
            update={
                "created_agent_name": agent_name,
                "messages": [ToolMessage(content=f"Agent '{agent_name}' created successfully!", tool_call_id=runtime.tool_call_id)],
            }
        )

    except Exception as e:
        logger.error(f"[agent_creator] Failed to create agent '{agent_name}': {e}", exc_info=True)
        return Command(update={"messages": [ToolMessage(content=f"Error: {e}", tool_call_id=runtime.tool_call_id)]})
