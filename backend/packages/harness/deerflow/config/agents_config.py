"""Configuration and loaders for custom agents.

After Round 2.1 the agent directory layout lives in OpenDAL under the
``custom-agents/{user_id|__global__}/{name}/`` prefix instead of on the
local filesystem. The on-disk shape is preserved (each agent owns a
``config.yaml`` and an optional ``SOUL.md``) so the public Pydantic API
is unchanged; only the read/write transport changed.
"""

import logging
import re
from typing import Any, Literal

import opendal.exceptions as opendal_exc
import yaml
from pydantic import BaseModel

from deerflow.storage import (
    get_operator,
    user_agent_config_key,
    user_agent_prefix,
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


def normalize_agent_name(name: str) -> str:
    """Validate and normalize a custom agent name for storage."""
    validated = validate_agent_name(name)
    if validated is None:
        raise ValueError("Invalid agent name. Expected a string.")
    return validated.lower()


class AgentConfig(BaseModel):
    """Configuration for a custom agent."""

    name: str
    description: str = ""
    model: str | None = None
    variant: Literal["chat", "computer"] | None = None
    tool_groups: list[str] | None = None
    skills: list[str] | None = None


def _is_not_found(exc: BaseException) -> bool:
    """OpenDAL 0.47 raises ``opendal.exceptions.NotFound``; older releases
    occasionally bubble up a plain ``FileNotFoundError`` from the
    filesystem backend."""
    return isinstance(exc, (opendal_exc.NotFound, FileNotFoundError))


class CustomAgentStore:
    """Storage interface for custom agent config and SOUL.md objects."""

    def __init__(self, operator=None):
        self.operator = operator or get_operator()

    def config_key(self, name: str, user_id: str | None = None) -> str:
        return user_agent_config_key(user_id, normalize_agent_name(name))

    def soul_key(self, name: str, user_id: str | None = None) -> str:
        return user_agent_soul_key(user_id, normalize_agent_name(name))

    def prefix(self, name: str, user_id: str | None = None) -> str:
        return user_agent_prefix(user_id, normalize_agent_name(name))

    def exists(self, name: str, user_id: str | None = None) -> bool:
        try:
            self.operator.stat(self.config_key(name, user_id))
            return True
        except Exception as exc:
            if _is_not_found(exc):
                return False
            raise

    def load_config(self, name: str | None, user_id: str | None = None) -> AgentConfig | None:
        if name is None:
            return None

        normalized = normalize_agent_name(name)
        config_key = user_agent_config_key(user_id, normalized)
        try:
            raw = bytes(self.operator.read(config_key))
        except Exception as exc:
            if _is_not_found(exc):
                raise FileNotFoundError(f"Agent config not found: {config_key}") from exc
            raise

        try:
            data: dict[str, Any] = yaml.safe_load(raw.decode("utf-8")) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse agent config {config_key}: {e}") from e

        if "name" not in data:
            data["name"] = normalized

        known_fields = set(AgentConfig.model_fields.keys())
        data = {k: v for k, v in data.items() if k in known_fields}
        data["name"] = normalize_agent_name(data["name"])

        return AgentConfig(**data)

    def load_soul(self, name: str | None, user_id: str | None = None) -> str | None:
        if name is None:
            return None

        soul_key = self.soul_key(name, user_id)
        try:
            raw = bytes(self.operator.read(soul_key))
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise

        content = raw.decode("utf-8").strip()
        return content or None

    def list_agents(self, user_id: str | None = None) -> list[AgentConfig]:
        prefix = user_agents_prefix(user_id) + "/"

        seen: set[str] = set()
        try:
            entries = list(self.operator.list(prefix))
        except Exception as exc:
            if _is_not_found(exc):
                return []
            raise

        for entry in entries:
            path = entry.path
            if not path.startswith(prefix):
                continue
            rest = path[len(prefix):]
            if not rest:
                continue
            head = rest.split("/", 1)[0]
            if not head or head in seen:
                continue
            seen.add(head)

        agents: list[AgentConfig] = []
        for agent_name in sorted(seen):
            try:
                cfg = self.load_config(agent_name, user_id=user_id)
            except FileNotFoundError:
                logger.debug("Skipping %s: no config.yaml", agent_name)
                continue
            except Exception as e:
                logger.warning("Skipping agent '%s': %s", agent_name, e)
                continue
            if cfg is not None:
                agents.append(cfg)

        return agents

    def _config_payload(self, config: AgentConfig) -> dict[str, Any]:
        data: dict[str, Any] = {"name": normalize_agent_name(config.name)}
        if config.description:
            data["description"] = config.description
        if config.model is not None:
            data["model"] = config.model
        if config.variant is not None:
            data["variant"] = config.variant
        if config.tool_groups is not None:
            data["tool_groups"] = config.tool_groups
        if config.skills is not None:
            data["skills"] = config.skills
        return data

    def write_config(self, config: AgentConfig, user_id: str | None = None) -> str:
        config = config.model_copy(update={"name": normalize_agent_name(config.name)})
        config_key = user_agent_config_key(user_id, config.name)
        config_yaml = yaml.dump(self._config_payload(config), default_flow_style=False, allow_unicode=True, sort_keys=False)
        self.operator.write(config_key, config_yaml.encode("utf-8"))
        return config_key

    def write_soul(self, name: str, soul: str, user_id: str | None = None) -> str:
        soul_key = self.soul_key(name, user_id)
        self.operator.write(soul_key, soul.encode("utf-8"))
        return soul_key

    def create_agent(self, config: AgentConfig, soul: str, user_id: str | None = None) -> AgentConfig:
        config = config.model_copy(update={"name": normalize_agent_name(config.name)})
        if self.exists(config.name, user_id=user_id):
            raise FileExistsError(f"Agent '{config.name}' already exists for the current user.")

        created_keys: list[str] = []
        try:
            created_keys.append(self.write_config(config, user_id=user_id))
            created_keys.append(self.write_soul(config.name, soul, user_id=user_id))
        except Exception:
            for key in created_keys:
                try:
                    self.operator.delete(key)
                except Exception:
                    logger.debug("Failed to clean up partially created agent object %s", key, exc_info=True)
            raise
        loaded = self.load_config(config.name, user_id=user_id)
        if loaded is None:
            raise FileNotFoundError(f"Agent config not found after create: {config.name}")
        return loaded

    def delete_agent(self, name: str, user_id: str | None = None) -> int:
        prefix = self.prefix(name, user_id) + "/"

        try:
            entries = list(self.operator.list(prefix))
        except Exception as exc:
            if _is_not_found(exc):
                return 0
            raise

        removed = 0
        for entry in entries:
            path = entry.path
            if not path or path.endswith("/"):
                continue
            self.operator.delete(path)
            removed += 1
        return removed


def load_agent_config(name: str | None, user_id: str | None = None) -> AgentConfig | None:
    """Load the custom agent's config from object storage.

    Returns ``None`` for ``name=None``. Otherwise reads
    ``custom-agents/{user_id|__global__}/{name}/config.yaml``.

    Raises ``FileNotFoundError`` (preserving the legacy contract) when
    the agent or its config does not exist; the gateway routers map
    that to a 404.
    """
    return CustomAgentStore().load_config(name, user_id=user_id)


def load_agent_soul(agent_name: str | None, user_id: str | None = None) -> str | None:
    """Read the SOUL.md file for a custom agent, if it exists."""
    return CustomAgentStore().load_soul(agent_name, user_id=user_id)


def list_custom_agents(user_id: str | None = None) -> list[AgentConfig]:
    """Scan the per-user (or global) agents prefix and return all valid agents.

    Walks the ``custom-agents/{scope}/`` prefix on the OpenDAL operator,
    extracts the agent name from each ``.../config.yaml`` key, and loads
    the parsed config for every entry.
    """
    return CustomAgentStore().list_agents(user_id=user_id)
