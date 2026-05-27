"""Tests for DeerFlowClient graph-root Langfuse tracing wiring."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from deerflow.client import DeerFlowClient


class _FakeAgent:
    def __init__(self) -> None:
        self.captured_config: dict | None = None
        self.checkpointer = None
        self.store = None

    def stream(self, state, *, config, context, stream_mode):
        self.captured_config = config
        return iter(())


@pytest.fixture(autouse=True)
def _clear_langfuse_env(monkeypatch):
    from deerflow.config.tracing_config import reset_tracing_config

    for name in ("LANGFUSE_TRACING", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL", "DEER_FLOW_ENV", "ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    reset_tracing_config()
    yield
    reset_tracing_config()


def _enable_langfuse(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_TRACING", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    from deerflow.config.tracing_config import reset_tracing_config

    reset_tracing_config()


def _stub_agent_creation(monkeypatch, fake_agent: _FakeAgent) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def _stub_ensure_agent(self, config):
        captured["config"] = config
        self._agent = fake_agent
        self._agent_config_key = ("stub",)

    monkeypatch.setattr(DeerFlowClient, "_ensure_agent", _stub_ensure_agent)
    return captured


def _make_client() -> DeerFlowClient:
    fake_app_config = SimpleNamespace(models=[SimpleNamespace(name="stub-model")])
    client = DeerFlowClient.__new__(DeerFlowClient)
    client._app_config = fake_app_config
    client._extensions_config = None
    client._model_name = "stub-model"
    client._thinking_enabled = False
    client._plan_mode = False
    client._subagent_enabled = False
    client._agent_name = None
    client._available_skills = None
    client._middlewares = []
    client._checkpointer = None
    client._agent = None
    client._agent_config_key = None
    client._environment = "test"
    return client


def test_stream_injects_langfuse_metadata_when_enabled(monkeypatch):
    _enable_langfuse(monkeypatch)
    sentinel = object()
    monkeypatch.setattr("deerflow.client.build_tracing_callbacks", lambda: [sentinel])

    fake_agent = _FakeAgent()
    captured = _stub_agent_creation(monkeypatch, fake_agent)
    client = _make_client()

    list(client.stream("hi", thread_id="thread-client-1"))

    metadata = captured["config"].get("metadata") or {}
    assert metadata["langfuse_session_id"] == "thread-client-1"
    assert metadata["langfuse_user_id"] == "default"
    assert metadata["langfuse_trace_name"] == "lead-agent"
    assert metadata["langfuse_tags"] == ["env:test", "model:stub-model"]
    assert sentinel in (captured["config"].get("callbacks") or [])


def test_stream_is_inert_when_langfuse_disabled(monkeypatch):
    monkeypatch.setattr("deerflow.client.build_tracing_callbacks", lambda: [])

    fake_agent = _FakeAgent()
    captured = _stub_agent_creation(monkeypatch, fake_agent)
    client = _make_client()

    list(client.stream("hi", thread_id="thread-client-2"))

    metadata = captured["config"].get("metadata") or {}
    assert "callbacks" not in captured["config"] or not captured["config"]["callbacks"]
    assert "langfuse_session_id" not in metadata
    assert "langfuse_user_id" not in metadata


def test_stream_preserves_caller_metadata_overrides(monkeypatch):
    _enable_langfuse(monkeypatch)
    monkeypatch.setattr("deerflow.client.build_tracing_callbacks", lambda: [])

    fake_agent = _FakeAgent()
    captured = _stub_agent_creation(monkeypatch, fake_agent)
    client = _make_client()
    original_get_config = DeerFlowClient._get_runnable_config

    def patched_get_runnable_config(self, thread_id, **overrides):
        cfg = original_get_config(self, thread_id, **overrides)
        cfg["metadata"] = {
            "langfuse_session_id": "explicit-session",
            "langfuse_user_id": "explicit-user",
        }
        return cfg

    monkeypatch.setattr(DeerFlowClient, "_get_runnable_config", patched_get_runnable_config)

    list(client.stream("hi", thread_id="thread-client-3"))

    metadata = captured["config"].get("metadata") or {}
    assert metadata["langfuse_session_id"] == "explicit-session"
    assert metadata["langfuse_user_id"] == "explicit-user"
    assert metadata["langfuse_trace_name"] == "lead-agent"
