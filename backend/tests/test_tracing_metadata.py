"""Tests for Langfuse trace metadata helpers."""

from deerflow.tracing import metadata as tracing_metadata


def test_build_langfuse_trace_metadata_disabled(monkeypatch):
    monkeypatch.setattr(tracing_metadata, "get_enabled_tracing_providers", lambda: [])

    assert tracing_metadata.build_langfuse_trace_metadata(thread_id="t1", user_id="u1") == {}


def test_build_langfuse_trace_metadata_includes_reserved_keys(monkeypatch):
    monkeypatch.setattr(tracing_metadata, "get_enabled_tracing_providers", lambda: ["langfuse"])

    metadata = tracing_metadata.build_langfuse_trace_metadata(
        thread_id="thread-1",
        user_id="user-1",
        model_name="deepseek-v3",
        trace_name="lead-agent",
        environment="test",
    )

    assert metadata["langfuse_session_id"] == "thread-1"
    assert metadata["langfuse_user_id"] == "user-1"
    assert metadata["langfuse_trace_name"] == "lead-agent"
    assert metadata["langfuse_tags"] == ["env:test", "model:deepseek-v3"]


def test_inject_langfuse_metadata_preserves_caller_overrides(monkeypatch):
    monkeypatch.setattr(tracing_metadata, "get_enabled_tracing_providers", lambda: ["langfuse"])
    config = {"metadata": {"langfuse_user_id": "override"}}

    tracing_metadata.inject_langfuse_metadata(config, thread_id="thread-1", user_id="user-1")

    assert config["metadata"]["langfuse_user_id"] == "override"
    assert config["metadata"]["langfuse_session_id"] == "thread-1"
