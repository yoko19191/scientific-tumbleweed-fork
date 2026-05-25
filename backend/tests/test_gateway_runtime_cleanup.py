"""Regression coverage for the Gateway-owned LangGraph API runtime."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def test_nginx_routes_official_langgraph_prefix_to_gateway_api():
    for path in ("docker/nginx/nginx.local.conf", "docker/nginx/nginx.conf"):
        content = _read(path)

        assert "/api/langgraph-compat" not in content
        assert "rewrite ^/api/langgraph/(.*) /api/$1 break;" in content
        assert "proxy_pass http://gateway" in content or "proxy_pass http://$gateway_upstream" in content


def test_nginx_defers_cors_to_gateway_allowlist():
    for path in ("docker/nginx/nginx.local.conf", "docker/nginx/nginx.conf"):
        content = _read(path)

        assert "Access-Control-Allow-Origin" not in content
        assert "Access-Control-Allow-Methods" not in content
        assert "Access-Control-Allow-Headers" not in content
        assert "Access-Control-Allow-Credentials" not in content
        assert "proxy_hide_header 'Access-Control-Allow-" not in content
        assert "if ($request_method = 'OPTIONS')" not in content


def test_gateway_cors_configuration_uses_gateway_allowlist():
    gateway_config = _read("backend/app/gateway/config.py")
    gateway_app = _read("backend/app/gateway/app.py")
    csrf_middleware = _read("backend/app/gateway/csrf_middleware.py")

    assert not re.search(r"(?<!GATEWAY_)[\"']CORS_ORIGINS[\"']", gateway_config)
    assert "cors_origins" not in gateway_config
    assert "get_configured_cors_origins" in gateway_app
    assert "GATEWAY_CORS_ORIGINS" in csrf_middleware
