import json
import logging
from pathlib import Path
from typing import Literal

import opendal.exceptions as opendal_exc
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.deps import get_current_user_id, get_optional_user_from_request
from deerflow.config.extensions_config import ExtensionsConfig, get_extensions_config, reload_extensions_config
from deerflow.config.paths import get_paths
from deerflow.storage import get_async_operator, user_extensions_override_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])


def _is_opendal_not_found(exc: BaseException) -> bool:
    """OpenDAL 0.47 raises ``opendal.exceptions.NotFound``; older releases
    sometimes bubble up a plain ``FileNotFoundError`` from the filesystem
    backend."""
    return isinstance(exc, (opendal_exc.NotFound, FileNotFoundError))


async def _load_user_extensions_override(user_id: str) -> dict:
    """Read the per-user extensions override JSON. Returns empty dict on miss."""
    operator = get_async_operator()
    try:
        raw = bytes(await operator.read(user_extensions_override_key(user_id)))
    except Exception as exc:
        if _is_opendal_not_found(exc):
            return {}
        logger.warning("Failed to read per-user extensions config for user %s", user_id, exc_info=True)
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        logger.warning("Per-user extensions config for user %s is not valid JSON", user_id, exc_info=True)
        return {}


async def _save_user_extensions_override(user_id: str, data: dict) -> None:
    """Persist the per-user extensions override JSON."""
    operator = get_async_operator()
    payload = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
    await operator.write(user_extensions_override_key(user_id), payload)


class McpOAuthConfigResponse(BaseModel):
    """OAuth configuration for an MCP server."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(default="", description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(default="client_credentials", description="OAuth grant type")
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience")
    token_field: str = Field(default="access_token", description="Token response field containing access token")
    token_type_field: str = Field(default="token_type", description="Token response field containing token type")
    expires_in_field: str = Field(default="expires_in", description="Token response field containing expires-in seconds")
    default_token_type: str = Field(default="Bearer", description="Default token type when response omits token_type")
    refresh_skew_seconds: int = Field(default=60, description="Refresh this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")


class McpServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', or 'http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfigResponse | None = Field(default=None, description="OAuth configuration for MCP HTTP/SSE servers")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")


class McpConfigResponse(BaseModel):
    """Response model for MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
    )


class McpConfigUpdateRequest(BaseModel):
    """Request model for updating MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        ...,
        description="Map of MCP server name to configuration",
    )


_MASKED_VALUE = "***"


def _mask_server_config(server: McpServerConfigResponse) -> McpServerConfigResponse:
    """Return a copy of server config with sensitive fields masked.

    Masks env values, header values, and removes OAuth secrets so they
    are not exposed through the GET API endpoint.
    """
    masked_env = {k: _MASKED_VALUE for k in server.env}
    masked_headers = {k: _MASKED_VALUE for k in server.headers}
    masked_oauth = None
    if server.oauth is not None:
        masked_oauth = server.oauth.model_copy(
            update={
                "client_secret": None,
                "refresh_token": None,
            }
        )
    return server.model_copy(
        update={
            "env": masked_env,
            "headers": masked_headers,
            "oauth": masked_oauth,
        }
    )


def _merge_preserving_secrets(
    incoming: McpServerConfigResponse,
    existing: McpServerConfigResponse,
) -> McpServerConfigResponse:
    """Merge incoming config with existing, preserving secrets masked by GET.

    When the frontend toggles ``enabled`` it round-trips the full config:
    GET (masked) → modify enabled → PUT (masked values sent back).
    This function ensures masked values (``***``) are replaced with the
    real secrets from the current on-disk config.

    ``***`` is only accepted for keys that already exist in *existing*.
    New keys must provide a real value.

    For OAuth secrets, ``None`` means "preserve the existing stored value"
    so masked GET responses can be safely round-tripped. To explicitly clear
    a stored secret, clients may send an empty string, which is converted
    to ``None`` before persisting.
    """
    merged_env = {}
    for k, v in incoming.env.items():
        if v == _MASKED_VALUE:
            if k in existing.env:
                merged_env[k] = existing.env[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set env key '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_env[k] = v

    merged_headers = {}
    for k, v in incoming.headers.items():
        if v == _MASKED_VALUE:
            if k in existing.headers:
                merged_headers[k] = existing.headers[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set header '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_headers[k] = v

    merged_oauth = incoming.oauth
    if incoming.oauth is not None and existing.oauth is not None:
        # None = preserve (masked round-trip), "" = explicitly clear, else = new value
        merged_client_secret = existing.oauth.client_secret if incoming.oauth.client_secret is None else (None if incoming.oauth.client_secret == "" else incoming.oauth.client_secret)
        merged_refresh_token = existing.oauth.refresh_token if incoming.oauth.refresh_token is None else (None if incoming.oauth.refresh_token == "" else incoming.oauth.refresh_token)
        merged_oauth = incoming.oauth.model_copy(
            update={
                "client_secret": merged_client_secret,
                "refresh_token": merged_refresh_token,
            }
        )
    return incoming.model_copy(
        update={
            "env": merged_env,
            "headers": merged_headers,
            "oauth": merged_oauth,
        }
    )


@router.get(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Get MCP Configuration",
    description="Retrieve the current Model Context Protocol (MCP) server configurations.",
)
async def get_mcp_configuration(request: Request) -> McpConfigResponse:
    """Get the current MCP configuration.

    When the user is logged in, merges global MCP server list with per-user
    enabled overrides from users/{user_id}/extensions_config.json.

    Returns:
        The current MCP configuration with all servers.
    """
    config = get_extensions_config()
    servers = {name: _mask_server_config(McpServerConfigResponse(**server.model_dump())) for name, server in config.mcp_servers.items()}

    # Anonymous callers see the public config; logged-in users get the
    # per-user override merged on top.
    user = await get_optional_user_from_request(request)
    if user is not None:
        user_data = await _load_user_extensions_override(str(user.id))
        user_mcp = user_data.get("mcpServers", {}) if isinstance(user_data, dict) else {}
        for name, overrides in user_mcp.items():
            if name in servers and isinstance(overrides, dict) and "enabled" in overrides:
                servers[name] = servers[name].model_copy(update={"enabled": overrides["enabled"]})

    return McpConfigResponse(mcp_servers=servers)


@router.put(
    "/mcp/config",
    summary="Update MCP Configuration (disabled)",
    description="Global MCP config is read-only. Use PUT /api/mcp/servers/{name}/enabled to toggle per-user.",
)
async def update_mcp_configuration() -> None:
    """Global MCP config is now read-only.

    Use PUT /api/mcp/servers/{name}/enabled to toggle individual servers per user.
    """
    raise HTTPException(
        status_code=403,
        detail="Global MCP config is read-only. Use PUT /api/mcp/servers/{name}/enabled to toggle per-user.",
    )


class McpServerEnabledRequest(BaseModel):
    """Request body for toggling a per-user MCP server enabled state."""

    enabled: bool


@router.put(
    "/mcp/servers/{name}/enabled",
    summary="Toggle per-user MCP server enabled state",
    description="Enable or disable an MCP server for the authenticated user.",
)
async def set_mcp_server_enabled(
    name: str,
    body: McpServerEnabledRequest,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """Toggle an MCP server on/off for the authenticated user.

    Writes only the enabled field to the per-user extensions override
    object, preserving existing skills entries.

    Raises:
        HTTPException 401: If not logged in.
        HTTPException 404: If server name not in global config.
    """
    global_config = get_extensions_config()
    if name not in global_config.mcp_servers:
        raise HTTPException(status_code=404, detail=f"MCP server not found: {name}")

    # Load existing per-user overrides so we can preserve unrelated keys
    # (skills, other mcpServers entries).
    user_data = await _load_user_extensions_override(user_id)
    if not isinstance(user_data, dict):
        user_data = {}

    mcp_section = user_data.setdefault("mcpServers", {})
    server_entry = mcp_section.setdefault(name, {})
    server_entry["enabled"] = body.enabled
    await _save_user_extensions_override(user_id, user_data)

    logger.info("User %s set MCP server %r enabled=%s", user_id, name, body.enabled)
    return {"success": True, "name": name, "enabled": body.enabled}
