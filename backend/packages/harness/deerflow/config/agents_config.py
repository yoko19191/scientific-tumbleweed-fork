"""Configuration and loaders for custom agents.

After Round 2.1 the agent directory layout lives in OpenDAL under the
``custom-agents/{user_id|__global__}/{name}/`` prefix instead of on the
local filesystem. The on-disk shape is preserved (each agent owns a
``config.yaml`` and an optional ``SOUL.md``) so the public Pydantic API
is unchanged; only the read/write transport changed.
"""

import logging
import re
from typing import Any

import opendal.exceptions as opendal_exc
import yaml
from pydantic import BaseModel

from deerflow.storage import (
    GLOBAL_SCOPE,
    get_operator,
    user_agent_config_key,
    user_agent_soul_key,
    user_agents_prefix,
)

logger = logging.getLogger(__name__)

SOUL_FILENAME = "SOUL.md"
AGENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")


def validate_agent_name(name: str | None) -> str | None:
    """Validate a custom agent name before using it in storage keys."""
    if name is None:
        return None
    if not isinstance(name, str):
        raise ValueError("Invalid agent name. Expected a string or None.")
    if not AGENT_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"Invalid agent name '{name}'. Must match pattern: {AGENT_NAME_PATTERN.pattern}")
    return name


class AgentConfig(BaseModel):
    """Configuration for a custom agent."""

    name: str
    description: str = ""
    model: str | None = None
    tool_groups: list[str] | None = None
    skills: list[str] | None = None


def _is_not_found(exc: BaseException) -> bool:
    """OpenDAL 0.47 raises ``opendal.exceptions.NotFound``; older releases
    occasionally bubble up a plain ``FileNotFoundError`` from the
    filesystem backend."""
    return isinstance(exc, (opendal_exc.NotFound, FileNotFoundError))


def load_agent_config(name: str | None, user_id: str | None = None) -> AgentConfig | None:
    """Load the custom agent's config from object storage.

    Returns ``None`` for ``name=None``. Otherwise reads
    ``custom-agents/{user_id|__global__}/{name}/config.yaml``.

    Raises ``FileNotFoundError`` (preserving the legacy contract) when
    the agent or its config does not exist; the gateway routers map
    that to a 404.
    """
    if name is None:
        return None

    name = validate_agent_name(name)

    operator = get_operator()
    config_key = user_agent_config_key(user_id, name)
    try:
        raw = bytes(operator.read(config_key))
    except Exception as exc:
        if _is_not_found(exc):
            raise FileNotFoundError(f"Agent config not found: {config_key}") from exc
        raise

    try:
        data: dict[str, Any] = yaml.safe_load(raw.decode("utf-8")) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse agent config {config_key}: {e}") from e

    # Ensure name is set from the storage key if not in the file.
    if "name" not in data:
        data["name"] = name

    # Strip unknown fields before passing to Pydantic (e.g. legacy prompt_file).
    known_fields = set(AgentConfig.model_fields.keys())
    data = {k: v for k, v in data.items() if k in known_fields}

    return AgentConfig(**data)


def load_agent_soul(agent_name: str | None, user_id: str | None = None) -> str | None:
    """Read the SOUL.md file for a custom agent, if it exists."""
    if agent_name is None:
        return None

    operator = get_operator()
    soul_key = user_agent_soul_key(user_id, agent_name)
    try:
        raw = bytes(operator.read(soul_key))
    except Exception as exc:
        if _is_not_found(exc):
            return None
        raise

    content = raw.decode("utf-8").strip()
    return content or None


def list_custom_agents(user_id: str | None = None) -> list[AgentConfig]:
    """Scan the per-user (or global) agents prefix and return all valid agents.

    Walks the ``custom-agents/{scope}/`` prefix on the OpenDAL operator,
    extracts the agent name from each ``.../config.yaml`` key, and loads
    the parsed config for every entry.
    """
    operator = get_operator()
    prefix = user_agents_prefix(user_id) + "/"

    seen: set[str] = set()
    try:
        entries = list(operator.list(prefix))
    except Exception as exc:
        if _is_not_found(exc):
            return []
        raise

    for entry in entries:
        path = entry.path  # full key under the operator root
        if not path.startswith(prefix):
            continue
        rest = path[len(prefix):]
        # We want to flatten the listing to "first-level child name". The
        # filesystem backend yields entries like
        # ``custom-agents/abc/foo/`` for directories and
        # ``custom-agents/abc/foo/config.yaml`` for files; both pin foo
        # as the agent name once we split on '/'.
        if not rest:
            continue
        head = rest.split("/", 1)[0]
        if not head or head in seen:
            continue
        seen.add(head)

    agents: list[AgentConfig] = []
    for agent_name in sorted(seen):
        try:
            cfg = load_agent_config(agent_name, user_id=user_id)
        except FileNotFoundError:
            logger.debug("Skipping %s: no config.yaml", agent_name)
            continue
        except Exception as e:
            logger.warning("Skipping agent '%s': %s", agent_name, e)
            continue
        if cfg is not None:
            agents.append(cfg)

    return agents
