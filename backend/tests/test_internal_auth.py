"""Tests for Gateway internal authentication helpers."""

from __future__ import annotations

import importlib

from app.gateway import internal_auth as internal_auth_module


def _reload_internal_auth():
    return importlib.reload(internal_auth_module)


def test_internal_auth_uses_configured_env_token(monkeypatch):
    monkeypatch.setenv("DEER_FLOW_INTERNAL_AUTH_TOKEN", "shared-internal-token")
    module = _reload_internal_auth()

    assert module.create_internal_auth_headers() == {
        module.INTERNAL_AUTH_HEADER_NAME: "shared-internal-token"
    }
    assert module.is_valid_internal_auth_token("shared-internal-token") is True
    assert module.is_valid_internal_auth_token("wrong-token") is False


def test_internal_auth_falls_back_to_random_token(monkeypatch):
    monkeypatch.delenv("DEER_FLOW_INTERNAL_AUTH_TOKEN", raising=False)
    first = _reload_internal_auth()
    first_token = first.create_internal_auth_headers()[first.INTERNAL_AUTH_HEADER_NAME]

    second = _reload_internal_auth()
    second_token = second.create_internal_auth_headers()[second.INTERNAL_AUTH_HEADER_NAME]

    assert first_token
    assert second_token
    assert first_token != second_token
    assert second.is_valid_internal_auth_token(second_token) is True
    assert second.is_valid_internal_auth_token(first_token) is False
