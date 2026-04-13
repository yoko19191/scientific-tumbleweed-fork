import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.gateway.deps import get_optional_user_id
from deerflow.config.extensions_config import ExtensionsConfig, get_extensions_config, reload_extensions_config
from deerflow.config.paths import get_paths

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])


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
    servers = {name: McpServerConfigResponse(**server.model_dump()) for name, server in config.mcp_servers.items()}

    user_id = get_optional_user_id(request)
    if user_id:
        user_ext_file = get_paths().user_extensions_config_file(user_id)
        if user_ext_file.is_file():
            try:
                user_data = json.loads(user_ext_file.read_text(encoding="utf-8"))
                user_mcp = user_data.get("mcpServers", {})
                for name, overrides in user_mcp.items():
                    if name in servers and "enabled" in overrides:
                        servers[name] = servers[name].model_copy(update={"enabled": overrides["enabled"]})
            except Exception:
                logger.warning("Failed to read per-user extensions config for user %s", user_id, exc_info=True)

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
async def set_mcp_server_enabled(name: str, body: McpServerEnabledRequest, request: Request) -> dict:
    """Toggle an MCP server on/off for the authenticated user.

    Writes only the enabled field to users/{user_id}/extensions_config.json
    mcpServers section, preserving existing skills entries.

    Raises:
        HTTPException 401: If not logged in.
        HTTPException 404: If server name not in global config.
    """
    user_id = get_optional_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    global_config = get_extensions_config()
    if name not in global_config.mcp_servers:
        raise HTTPException(status_code=404, detail=f"MCP server not found: {name}")

    user_ext_file = get_paths().user_extensions_config_file(user_id)
    user_ext_file.parent.mkdir(parents=True, exist_ok=True)

    # Load existing user config to preserve skills and other entries
    if user_ext_file.is_file():
        try:
            user_data = json.loads(user_ext_file.read_text(encoding="utf-8"))
        except Exception:
            user_data = {}
    else:
        user_data = {}

    mcp_section = user_data.setdefault("mcpServers", {})
    server_entry = mcp_section.setdefault(name, {})
    server_entry["enabled"] = body.enabled
    user_ext_file.write_text(json.dumps(user_data, indent=2), encoding="utf-8")

    logger.info("User %s set MCP server %r enabled=%s", user_id, name, body.enabled)
    return {"success": True, "name": name, "enabled": body.enabled}
