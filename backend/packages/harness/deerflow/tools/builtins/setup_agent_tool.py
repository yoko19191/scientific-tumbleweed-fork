import logging

import yaml
import opendal.exceptions as opendal_exc
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from deerflow.config.agents_config import validate_agent_name
from deerflow.runtime.user_context import resolve_runtime_user_id
from deerflow.storage import get_operator, user_agent_config_key, user_agent_prefix, user_agent_soul_key
from deerflow.tools.types import Runtime

logger = logging.getLogger(__name__)


def _is_not_found(exc: BaseException) -> bool:
    return isinstance(exc, (opendal_exc.NotFound, FileNotFoundError))


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
    created_keys: list[str] = []

    try:
        agent_name = validate_agent_name(agent_name)
        operator = get_operator()

        if agent_name:
            user_id = resolve_runtime_user_id(runtime)
            config_data: dict = {"name": agent_name}
            if description:
                config_data["description"] = description

            config_key = user_agent_config_key(user_id, agent_name)
            try:
                operator.stat(config_key)
                raise FileExistsError(f"Agent '{agent_name}' already exists for the current user.")
            except Exception as exc:
                if not _is_not_found(exc):
                    raise

            config_yaml = yaml.dump(config_data, default_flow_style=False, allow_unicode=True, sort_keys=False)
            operator.write(config_key, config_yaml.encode("utf-8"))
            created_keys.append(config_key)

            soul_key = user_agent_soul_key(user_id, agent_name)
            operator.write(soul_key, soul.encode("utf-8"))
            created_keys.append(soul_key)
        else:
            # The bootstrap/default-agent setup path historically wrote to
            # base_dir/SOUL.md. Custom agent creation is the only active caller
            # for setup_agent in the gateway, so keep the no-name path disabled
            # rather than silently writing an unscoped object-store key.
            raise ValueError("setup_agent requires an agent_name in runtime context.")

        logger.info("[agent_creator] Created agent '%s' at %s", agent_name, user_agent_prefix(resolve_runtime_user_id(runtime), agent_name))
        return Command(
            update={
                "created_agent_name": agent_name,
                "messages": [ToolMessage(content=f"Agent '{agent_name}' created successfully!", tool_call_id=runtime.tool_call_id)],
            }
        )

    except Exception as e:
        if created_keys:
            try:
                operator = get_operator()
                for key in created_keys:
                    operator.delete(key)
            except Exception:
                logger.debug("Failed to clean up partially created agent objects", exc_info=True)
        logger.error(f"[agent_creator] Failed to create agent '{agent_name}': {e}", exc_info=True)
        return Command(update={"messages": [ToolMessage(content=f"Error: {e}", tool_call_id=runtime.tool_call_id)]})
