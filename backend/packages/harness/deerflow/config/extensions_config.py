"""Unified extensions configuration for MCP servers and skills."""

import json
import logging
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class McpOAuthConfig(BaseModel):
    """OAuth configuration for an MCP server (HTTP/SSE transports)."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(
        default="client_credentials",
        description="OAuth grant type",
    )
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token (for refresh_token grant)")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience (provider-specific)")
    token_field: str = Field(default="access_token", description="Field name containing access token in token response")
    token_type_field: str = Field(default="token_type", description="Field name containing token type in token response")
    expires_in_field: str = Field(default="expires_in", description="Field name containing expiry (seconds) in token response")
    default_token_type: str = Field(default="Bearer", description="Default token type when missing in token response")
    refresh_skew_seconds: int = Field(default=60, description="Refresh token this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")
    model_config = ConfigDict(extra="allow")


class McpServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', or 'http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfig | None = Field(default=None, description="OAuth configuration (for sse or http type)")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")
    model_config = ConfigDict(extra="allow")


class SkillStateConfig(BaseModel):
    """Configuration for a single skill's state."""

    enabled: bool = Field(default=True, description="Whether this skill is enabled")


class ExtensionsConfig(BaseModel):
    """Unified configuration for MCP servers and skills."""

    mcp_servers: dict[str, McpServerConfig] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
        alias="mcpServers",
    )
    skills: dict[str, SkillStateConfig] = Field(
        default_factory=dict,
        description="Map of skill name to state configuration",
    )
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def resolve_config_path(cls, config_path: str | None = None) -> Path | None:
        """Resolve the extensions config file path.

        Priority:
        1. If provided `config_path` argument, use it.
        2. If provided `DEER_FLOW_EXTENSIONS_CONFIG_PATH` environment variable, use it.
        3. Otherwise, check for `extensions_config.json` in the current directory, then in the parent directory.
        4. For backward compatibility, also check for `mcp_config.json` if `extensions_config.json` is not found.
        5. If not found, return None (extensions are optional).

        Args:
            config_path: Optional path to extensions config file.

        Resolution order:
            1. If provided `config_path` argument, use it.
            2. If provided `DEER_FLOW_EXTENSIONS_CONFIG_PATH` environment variable, use it.
            3. Otherwise, search backend/repository-root defaults for
               `extensions_config.json`, then legacy `mcp_config.json`.

        Returns:
            Path to the extensions config file if found, otherwise None.
        """
        if config_path:
            path = Path(config_path)
            if not path.exists():
                raise FileNotFoundError(f"Extensions config file specified by param `config_path` not found at {path}")
            return path
        elif os.getenv("DEER_FLOW_EXTENSIONS_CONFIG_PATH"):
            path = Path(os.getenv("DEER_FLOW_EXTENSIONS_CONFIG_PATH"))
            if not path.exists():
                raise FileNotFoundError(f"Extensions config file specified by environment variable `DEER_FLOW_EXTENSIONS_CONFIG_PATH` not found at {path}")
            return path
        else:
            backend_dir = Path(__file__).resolve().parents[4]
            repo_root = backend_dir.parent
            for path in (
                backend_dir / "extensions_config.json",
                repo_root / "extensions_config.json",
                backend_dir / "mcp_config.json",
                repo_root / "mcp_config.json",
            ):
                if path.exists():
                    return path

            # Extensions are optional, so return None if not found
            return None

    @classmethod
    def from_dict(cls, config_data: dict[str, Any] | None) -> "ExtensionsConfig":
        """Build an :class:`ExtensionsConfig` from an in-memory dict.

        Mirrors :meth:`from_file` but skips the path-resolution logic so
        callers that already hold the JSON in memory (e.g. the OpenDAL
        per-user override loader) can avoid a roundtrip through disk.

        ``None`` and empty dicts both yield an empty config so callers
        can pass through "no override available" without branching.
        """
        if not config_data:
            return cls(mcp_servers={}, skills={})
        cls.resolve_env_variables(config_data)
        return cls.model_validate(config_data)

    @classmethod
    def from_file(cls, config_path: str | None = None) -> "ExtensionsConfig":
        """Load extensions config from JSON file.

        See `resolve_config_path` for more details.

        Args:
            config_path: Path to the extensions config file.

        Returns:
            ExtensionsConfig: The loaded config, or empty config if file not found.
        """
        resolved_path = cls.resolve_config_path(config_path)
        if resolved_path is None:
            # Return empty config if extensions config file is not found
            return cls(mcp_servers={}, skills={})

        try:
            with open(resolved_path, encoding="utf-8") as f:
                config_data = json.load(f)
            config_data = cls.resolve_env_variables(config_data)
            return cls.model_validate(config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Extensions config file at {resolved_path} is not valid JSON: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to load extensions config from {resolved_path}: {e}") from e

    @classmethod
    def resolve_env_variables(cls, config: Any) -> Any:
        """Recursively resolve environment variables in the config.

        Environment variables are resolved using the `os.getenv` function. Example: $OPENAI_API_KEY

        Args:
            config: The config to resolve environment variables in.

        Returns:
            The config with environment variables resolved.
        """
        if isinstance(config, str):
            if not config.startswith("$"):
                return config
            env_value = os.getenv(config[1:])
            if env_value is None:
                # Unresolved placeholder — store empty string so downstream
                # consumers (e.g. MCP servers) don't receive the literal "$VAR"
                # token as an actual environment value.
                return ""
            return env_value

        if isinstance(config, dict):
            return {key: cls.resolve_env_variables(value) for key, value in config.items()}

        if isinstance(config, list):
            return [cls.resolve_env_variables(item) for item in config]

        if isinstance(config, tuple):
            return tuple(cls.resolve_env_variables(item) for item in config)

        return config

    def get_enabled_mcp_servers(self) -> dict[str, McpServerConfig]:
        """Get only the enabled MCP servers.

        Returns:
            Dictionary of enabled MCP servers.
        """
        return {name: config for name, config in self.mcp_servers.items() if config.enabled}

    def is_skill_enabled(self, skill_name: str, skill_category: str) -> bool:
        """Check if a skill is enabled.

        Args:
            skill_name: Name of the skill
            skill_category: Category of the skill

        Returns:
            True if enabled, False otherwise
        """
        skill_config = self.skills.get(skill_name)
        if skill_config is None:
            # Default to enable for public & custom skill
            return skill_category in ("public", "custom")
        return skill_config.enabled


_extensions_config: ExtensionsConfig | None = None


def get_extensions_config() -> ExtensionsConfig:
    """Get the extensions config instance.

    Returns a cached singleton instance. Use `reload_extensions_config()` to reload
    from file, or `reset_extensions_config()` to clear the cache.

    Returns:
        The cached ExtensionsConfig instance.
    """
    global _extensions_config
    if _extensions_config is None:
        _extensions_config = ExtensionsConfig.from_file()
    return _extensions_config


def reload_extensions_config(config_path: str | None = None) -> ExtensionsConfig:
    """Reload the extensions config from file and update the cached instance.

    This is useful when the config file has been modified and you want
    to pick up the changes without restarting the application.

    Args:
        config_path: Optional path to extensions config file. If not provided,
                     uses the default resolution strategy.

    Returns:
        The newly loaded ExtensionsConfig instance.
    """
    global _extensions_config
    _extensions_config = ExtensionsConfig.from_file(config_path)
    return _extensions_config


def reset_extensions_config() -> None:
    """Reset the cached extensions config instance.

    This clears the singleton cache, causing the next call to
    `get_extensions_config()` to reload from file. Useful for testing
    or when switching between different configurations.
    """
    global _extensions_config
    _extensions_config = None


def set_extensions_config(config: ExtensionsConfig) -> None:
    """Set a custom extensions config instance.

    This allows injecting a custom or mock config for testing purposes.

    Args:
        config: The ExtensionsConfig instance to use.
    """
    global _extensions_config
    _extensions_config = config


def _is_not_found_error(exc: BaseException) -> bool:
    try:
        import opendal.exceptions as opendal_exc

        return isinstance(exc, (opendal_exc.NotFound, FileNotFoundError))
    except Exception:
        return isinstance(exc, FileNotFoundError)


def _parse_user_extensions_override(raw: bytes, *, user_id: str) -> dict:
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        logger.warning("Per-user extensions config for user %s is not valid JSON", user_id, exc_info=True)
        return {}
    if not isinstance(data, dict):
        logger.warning("Per-user extensions config for user %s is not a JSON object", user_id)
        return {}
    return data


def load_user_extensions_override(user_id: str) -> dict:
    """Read a per-user extensions override from object storage.

    Missing, invalid, or unreadable overrides return an empty dict so callers
    can safely fall back to the developer-level global config.
    """
    from deerflow.storage import get_operator, user_extensions_override_key

    try:
        raw = bytes(get_operator().read(user_extensions_override_key(user_id)))
    except Exception as exc:
        if _is_not_found_error(exc):
            return {}
        logger.warning("Failed to read per-user extensions config for user %s", user_id, exc_info=True)
        return {}
    return _parse_user_extensions_override(raw, user_id=user_id)


async def aload_user_extensions_override(user_id: str) -> dict:
    """Async variant of :func:`load_user_extensions_override`."""
    from deerflow.storage import get_async_operator, user_extensions_override_key

    try:
        raw = bytes(await get_async_operator().read(user_extensions_override_key(user_id)))
    except Exception as exc:
        if _is_not_found_error(exc):
            return {}
        logger.warning("Failed to read per-user extensions config for user %s", user_id, exc_info=True)
        return {}
    return _parse_user_extensions_override(raw, user_id=user_id)


async def asave_user_extensions_override(user_id: str, data: dict) -> None:
    """Persist a per-user extensions override to object storage."""
    from deerflow.storage import get_async_operator, user_extensions_override_key

    payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    await get_async_operator().write(user_extensions_override_key(user_id), payload)


def _enabled_override(entry: Any) -> bool | None:
    if not isinstance(entry, dict):
        return None
    enabled = entry.get("enabled")
    return enabled if isinstance(enabled, bool) else None


def merge_extensions_config(global_config: ExtensionsConfig, user_override: dict | None) -> ExtensionsConfig:
    """Merge a per-user override on top of the developer-level global config."""
    if not user_override:
        return global_config

    merged = global_config.model_dump(by_alias=True)

    skills = dict(merged.get("skills") or {})
    for name, entry in (user_override.get("skills") or {}).items():
        enabled = _enabled_override(entry)
        if enabled is not None:
            skills[name] = {"enabled": enabled}
    merged["skills"] = skills

    mcp_servers = dict(merged.get("mcpServers") or {})
    for name, entry in (user_override.get("mcpServers") or {}).items():
        enabled = _enabled_override(entry)
        if enabled is None or name not in mcp_servers:
            continue
        server = dict(mcp_servers[name])
        server["enabled"] = enabled
        mcp_servers[name] = server
    merged["mcpServers"] = mcp_servers

    return ExtensionsConfig.from_dict(merged)


def get_effective_extensions_config(
    user_id: str | None = None,
    *,
    global_config: ExtensionsConfig | None = None,
) -> ExtensionsConfig:
    """Return global extensions config merged with an optional user override."""
    base_config = global_config or get_extensions_config()
    if user_id is None:
        return base_config
    return merge_extensions_config(base_config, load_user_extensions_override(user_id))


async def aget_effective_extensions_config(
    user_id: str | None = None,
    *,
    global_config: ExtensionsConfig | None = None,
) -> ExtensionsConfig:
    """Async variant of :func:`get_effective_extensions_config`."""
    base_config = global_config or get_extensions_config()
    if user_id is None:
        return base_config
    return merge_extensions_config(base_config, await aload_user_extensions_override(user_id))


async def aupdate_user_extensions_override(
    user_id: str,
    mutate: Callable[[dict], None],
) -> dict:
    """Load, mutate, and save one user's extensions override."""
    data = await aload_user_extensions_override(user_id)
    if not isinstance(data, dict):
        data = {}
    mutate(data)
    await asave_user_extensions_override(user_id, data)
    return data


async def aset_user_skill_enabled(user_id: str, skill_name: str, enabled: bool) -> dict:
    """Set a skill enabled override for one user."""

    def _mutate(data: dict) -> None:
        skills = data.setdefault("skills", {})
        if not isinstance(skills, dict):
            skills = {}
            data["skills"] = skills
        skills[skill_name] = {"enabled": enabled}

    return await aupdate_user_extensions_override(user_id, _mutate)


async def aset_user_mcp_server_enabled(user_id: str, server_name: str, enabled: bool) -> dict:
    """Set an MCP server enabled override for one user."""

    def _mutate(data: dict) -> None:
        mcp_servers = data.setdefault("mcpServers", {})
        if not isinstance(mcp_servers, dict):
            mcp_servers = {}
            data["mcpServers"] = mcp_servers
        server_entry = mcp_servers.setdefault(server_name, {})
        if not isinstance(server_entry, dict):
            server_entry = {}
            mcp_servers[server_name] = server_entry
        server_entry["enabled"] = enabled

    return await aupdate_user_extensions_override(user_id, _mutate)
