"""Tests for MCP config secret masking and preservation.

Verifies that GET /api/mcp/config masks sensitive fields (env values,
header values, OAuth secrets) and that PUT /api/mcp/config correctly
preserves existing secrets when the frontend round-trips masked values.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateway.routers import mcp as mcp_router_module
from app.gateway.routers.mcp import (
    McpOAuthConfigResponse,
    McpServerConfigResponse,
    _mask_server_config,
    _merge_preserving_secrets,
)
from deerflow.config.extensions_config import ExtensionsConfig, reset_extensions_config, set_extensions_config
from deerflow.storage import user_extensions_override_key

# ---------------------------------------------------------------------------
# _mask_server_config
# ---------------------------------------------------------------------------


def test_mask_replaces_env_values_with_asterisks():
    """Env dict values should be replaced with '***'."""
    server = McpServerConfigResponse(
        env={"GITHUB_TOKEN": "ghp_real_secret_123", "API_KEY": "sk-abc"},
    )
    masked = _mask_server_config(server)
    assert masked.env == {"GITHUB_TOKEN": "***", "API_KEY": "***"}


def test_mask_replaces_header_values_with_asterisks():
    """Header dict values should be replaced with '***'."""
    server = McpServerConfigResponse(
        headers={"Authorization": "Bearer tok_123", "X-API-Key": "key_456"},
    )
    masked = _mask_server_config(server)
    assert masked.headers == {"Authorization": "***", "X-API-Key": "***"}


def test_mask_removes_oauth_secrets():
    """OAuth client_secret and refresh_token should be set to None."""
    server = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_id="my-client",
            client_secret="super-secret",
            refresh_token="refresh-token-abc",
            token_url="https://auth.example.com/token",
        ),
    )
    masked = _mask_server_config(server)
    assert masked.oauth is not None
    assert masked.oauth.client_secret is None
    assert masked.oauth.refresh_token is None
    # Non-secret fields preserved
    assert masked.oauth.client_id == "my-client"
    assert masked.oauth.token_url == "https://auth.example.com/token"


def test_mask_preserves_non_secret_fields():
    """Non-sensitive fields should pass through unchanged."""
    server = McpServerConfigResponse(
        enabled=True,
        type="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        env={"KEY": "val"},
        description="GitHub MCP server",
    )
    masked = _mask_server_config(server)
    assert masked.enabled is True
    assert masked.type == "stdio"
    assert masked.command == "npx"
    assert masked.args == ["-y", "@modelcontextprotocol/server-github"]
    assert masked.description == "GitHub MCP server"


def test_mask_handles_empty_env_and_headers():
    """Empty env/headers dicts should remain empty."""
    server = McpServerConfigResponse()
    masked = _mask_server_config(server)
    assert masked.env == {}
    assert masked.headers == {}


def test_mask_handles_no_oauth():
    """Server without OAuth should remain None."""
    server = McpServerConfigResponse(oauth=None)
    masked = _mask_server_config(server)
    assert masked.oauth is None


def test_mask_does_not_mutate_original():
    """Masking should return a new object, not modify the original."""
    server = McpServerConfigResponse(env={"KEY": "secret"})
    masked = _mask_server_config(server)
    assert server.env["KEY"] == "secret"
    assert masked.env["KEY"] == "***"


# ---------------------------------------------------------------------------
# _merge_preserving_secrets
# ---------------------------------------------------------------------------


def test_merge_preserves_masked_env_values():
    """Incoming '***' env values should be replaced with existing secrets."""
    incoming = McpServerConfigResponse(env={"KEY": "***"})
    existing = McpServerConfigResponse(env={"KEY": "real_secret"})
    merged = _merge_preserving_secrets(incoming, existing)
    assert merged.env["KEY"] == "real_secret"


def test_merge_preserves_masked_header_values():
    """Incoming '***' header values should be replaced with existing secrets."""
    incoming = McpServerConfigResponse(headers={"Authorization": "***"})
    existing = McpServerConfigResponse(headers={"Authorization": "Bearer real"})
    merged = _merge_preserving_secrets(incoming, existing)
    assert merged.headers["Authorization"] == "Bearer real"


def test_merge_preserves_oauth_secrets_when_none():
    """Incoming None oauth secrets should preserve existing values."""
    incoming = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_secret=None,
            refresh_token=None,
            token_url="https://auth.example.com/token",
        ),
    )
    existing = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_secret="existing-secret",
            refresh_token="existing-refresh",
            token_url="https://auth.example.com/token",
        ),
    )
    merged = _merge_preserving_secrets(incoming, existing)
    assert merged.oauth is not None
    assert merged.oauth.client_secret == "existing-secret"
    assert merged.oauth.refresh_token == "existing-refresh"


def test_merge_accepts_new_secret_values():
    """Incoming real secret values should replace existing ones."""
    incoming = McpServerConfigResponse(
        env={"KEY": "new_secret"},
        oauth=McpOAuthConfigResponse(
            client_secret="new-client-secret",
            refresh_token="new-refresh-token",
            token_url="https://auth.example.com/token",
        ),
    )
    existing = McpServerConfigResponse(
        env={"KEY": "old_secret"},
        oauth=McpOAuthConfigResponse(
            client_secret="old-secret",
            refresh_token="old-refresh",
            token_url="https://auth.example.com/token",
        ),
    )
    merged = _merge_preserving_secrets(incoming, existing)
    assert merged.env["KEY"] == "new_secret"
    assert merged.oauth.client_secret == "new-client-secret"
    assert merged.oauth.refresh_token == "new-refresh-token"


def test_merge_handles_no_existing_oauth():
    """When existing has no oauth but incoming does, keep incoming."""
    incoming = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_secret="new-secret",
            token_url="https://auth.example.com/token",
        ),
    )
    existing = McpServerConfigResponse(oauth=None)
    merged = _merge_preserving_secrets(incoming, existing)
    assert merged.oauth is not None
    assert merged.oauth.client_secret == "new-secret"


def test_merge_does_not_mutate_original():
    """Merge should return a new object, not modify the original."""
    incoming = McpServerConfigResponse(env={"KEY": "***"})
    existing = McpServerConfigResponse(env={"KEY": "secret"})
    merged = _merge_preserving_secrets(incoming, existing)
    assert incoming.env["KEY"] == "***"
    assert existing.env["KEY"] == "secret"
    assert merged.env["KEY"] == "secret"


# ---------------------------------------------------------------------------
# Comment 2 fix: masked value for new key is rejected
# ---------------------------------------------------------------------------


def test_merge_rejects_masked_value_for_new_env_key():
    """Sending '***' for a key that doesn't exist in existing should raise 400."""
    from fastapi import HTTPException

    incoming = McpServerConfigResponse(env={"NEW_KEY": "***"})
    existing = McpServerConfigResponse(env={})
    with pytest.raises(HTTPException) as exc_info:
        _merge_preserving_secrets(incoming, existing)
    assert exc_info.value.status_code == 400
    assert "NEW_KEY" in exc_info.value.detail


def test_merge_rejects_masked_value_for_new_header_key():
    """Sending '***' for a header key that doesn't exist should raise 400."""
    from fastapi import HTTPException

    incoming = McpServerConfigResponse(headers={"X-New-Auth": "***"})
    existing = McpServerConfigResponse(headers={})
    with pytest.raises(HTTPException) as exc_info:
        _merge_preserving_secrets(incoming, existing)
    assert exc_info.value.status_code == 400
    assert "X-New-Auth" in exc_info.value.detail


# ---------------------------------------------------------------------------
# Comment 4 fix: empty string clears OAuth secrets
# ---------------------------------------------------------------------------


def test_merge_empty_string_clears_oauth_client_secret():
    """Sending '' for client_secret should clear the stored value."""
    incoming = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_secret="",
            refresh_token=None,
            token_url="https://auth.example.com/token",
        ),
    )
    existing = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_secret="existing-secret",
            refresh_token="existing-refresh",
            token_url="https://auth.example.com/token",
        ),
    )
    merged = _merge_preserving_secrets(incoming, existing)
    assert merged.oauth.client_secret is None
    assert merged.oauth.refresh_token == "existing-refresh"


def test_merge_empty_string_clears_oauth_refresh_token():
    """Sending '' for refresh_token should clear the stored value."""
    incoming = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_secret=None,
            refresh_token="",
            token_url="https://auth.example.com/token",
        ),
    )
    existing = McpServerConfigResponse(
        oauth=McpOAuthConfigResponse(
            client_secret="existing-secret",
            refresh_token="existing-refresh",
            token_url="https://auth.example.com/token",
        ),
    )
    merged = _merge_preserving_secrets(incoming, existing)
    assert merged.oauth.client_secret == "existing-secret"
    assert merged.oauth.refresh_token is None


# ---------------------------------------------------------------------------
# Round-trip integration: mask → merge should preserve original secrets
# ---------------------------------------------------------------------------


def test_roundtrip_mask_then_merge_preserves_original_secrets():
    """Simulates the full frontend round-trip: GET (masked) → toggle → PUT."""
    original = McpServerConfigResponse(
        enabled=True,
        env={"GITHUB_TOKEN": "ghp_real_secret"},
        headers={"Authorization": "Bearer real_token"},
        oauth=McpOAuthConfigResponse(
            client_id="client-123",
            client_secret="oauth-secret",
            refresh_token="refresh-abc",
            token_url="https://auth.example.com/token",
        ),
        description="GitHub MCP server",
    )

    # Step 1: Server returns masked config (simulates GET response)
    masked = _mask_server_config(original)
    assert masked.env["GITHUB_TOKEN"] == "***"
    assert masked.oauth.client_secret is None

    # Step 2: Frontend toggles enabled and sends back (simulates PUT request)
    from_frontend = masked.model_copy(update={"enabled": False})

    # Step 3: Server merges with existing secrets (simulates PUT handler)
    restored = _merge_preserving_secrets(from_frontend, original)
    assert restored.enabled is False
    assert restored.env["GITHUB_TOKEN"] == "ghp_real_secret"
    assert restored.headers["Authorization"] == "Bearer real_token"
    assert restored.oauth.client_secret == "oauth-secret"
    assert restored.oauth.refresh_token == "refresh-abc"
    # Non-secret fields from the update are preserved
    assert restored.description == "GitHub MCP server"


@pytest.fixture
def mcp_endpoint_client(monkeypatch):
    storage: dict[str, bytes] = {}

    class FakeAsyncOperator:
        async def read(self, key: str) -> bytes:
            if key not in storage:
                raise FileNotFoundError(key)
            return storage[key]

        async def write(self, key: str, payload: bytes) -> None:
            storage[key] = bytes(payload)

    set_extensions_config(
        ExtensionsConfig.from_dict(
            {
                "mcpServers": {
                    "github": {
                        "enabled": True,
                        "type": "http",
                        "url": "https://mcp.example.com",
                        "env": {"GITHUB_TOKEN": "ghp_real_secret"},
                        "headers": {"Authorization": "Bearer real"},
                        "oauth": {
                            "token_url": "https://auth.example.com/token",
                            "client_id": "client-id",
                            "client_secret": "client-secret",
                            "refresh_token": "refresh-token",
                        },
                    }
                },
                "skills": {"demo-skill": {"enabled": True}},
            }
        )
    )
    monkeypatch.setattr("deerflow.storage.get_async_operator", lambda: FakeAsyncOperator())

    async def _optional_user(_request):
        return SimpleNamespace(id="user-a")

    monkeypatch.setattr(mcp_router_module, "get_optional_user_from_request", _optional_user)

    app = FastAPI()
    app.include_router(mcp_router_module.router)
    app.dependency_overrides[mcp_router_module.get_current_user_id] = lambda: "user-a"

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, storage

    app.dependency_overrides.clear()
    reset_extensions_config()


def test_get_mcp_config_masks_endpoint_secrets(mcp_endpoint_client):
    client, _storage = mcp_endpoint_client

    response = client.get("/api/mcp/config")

    assert response.status_code == 200
    server = response.json()["mcp_servers"]["github"]
    assert server["env"] == {"GITHUB_TOKEN": "***"}
    assert server["headers"] == {"Authorization": "***"}
    assert server["oauth"]["client_secret"] is None
    assert server["oauth"]["refresh_token"] is None
    assert server["url"] == "https://mcp.example.com"


def test_global_mcp_config_put_is_forbidden(mcp_endpoint_client):
    client, storage = mcp_endpoint_client

    response = client.put("/api/mcp/config", json={"mcp_servers": {}})

    assert response.status_code == 403
    assert storage == {}


def test_per_user_mcp_toggle_writes_only_enabled_override(mcp_endpoint_client):
    client, storage = mcp_endpoint_client
    key = user_extensions_override_key("user-a")
    storage[key] = json.dumps(
        {
            "skills": {"demo-skill": {"enabled": False}},
            "mcpServers": {"github": {"enabled": True, "env": {"GITHUB_TOKEN": "attempted-injection"}}},
        }
    ).encode("utf-8")

    response = client.put("/api/mcp/servers/github/enabled", json={"enabled": False})

    assert response.status_code == 200
    assert response.json() == {"success": True, "name": "github", "enabled": False}
    saved = json.loads(storage[key].decode("utf-8"))
    assert saved == {
        "skills": {"demo-skill": {"enabled": False}},
        "mcpServers": {"github": {"enabled": False}},
    }

    effective = client.get("/api/mcp/config").json()["mcp_servers"]["github"]
    assert effective["enabled"] is False
    assert effective["env"] == {"GITHUB_TOKEN": "***"}


def test_per_user_mcp_toggle_unknown_server_is_404(mcp_endpoint_client):
    client, storage = mcp_endpoint_client

    response = client.put("/api/mcp/servers/unknown/enabled", json={"enabled": False})

    assert response.status_code == 404
    assert storage == {}
