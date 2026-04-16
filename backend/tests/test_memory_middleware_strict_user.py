"""Tests for US-009: MemoryMiddleware strict per-user isolation.

Verifies that:
- MemoryMiddleware skips queuing when user_id is absent (no global fallback)
- MemoryMiddleware queues with the correct user_id from runtime context
- MemoryMiddleware queues with the correct user_id from run metadata
- Lead agent prompt injection uses the run owner's user_id (not global memory)
- User A memory is not injected into user B prompt
"""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from deerflow.agents.middlewares.memory_middleware import MemoryMiddleware, MemoryMiddlewareState
from deerflow.config.memory_config import MemoryConfig

USER_A = "user-aaaa-1111"
USER_B = "user-bbbb-2222"


def _memory_config(**overrides) -> MemoryConfig:
    config = MemoryConfig()
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def _state_with_messages() -> MemoryMiddlewareState:
    """Return a minimal state with one human + one AI message."""
    return MemoryMiddlewareState(
        messages=[
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there"),
        ]
    )


def _make_runtime(context: dict | None) -> Runtime:
    return Runtime(context=context)


# ---------------------------------------------------------------------------
# Strict mode: no user_id → skip queue
# ---------------------------------------------------------------------------


class TestMemoryMiddlewareStrictMode:
    """MemoryMiddleware must not write to global memory when user_id is absent."""

    def test_skips_queue_when_user_id_missing_from_context_and_metadata(self, monkeypatch):
        """No user_id anywhere → queue.add must NOT be called."""
        middleware = MemoryMiddleware()
        state = _state_with_messages()
        runtime = _make_runtime(context={"thread_id": "thread-1"})

        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_memory_config",
            lambda: _memory_config(enabled=True),
        )
        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-1"}, "metadata": {}},
        )

        mock_queue = MagicMock()
        with patch("deerflow.agents.middlewares.memory_middleware.get_memory_queue", return_value=mock_queue):
            result = middleware.after_agent(state=state, runtime=runtime)

        assert result is None
        mock_queue.add.assert_not_called()

    def test_skips_queue_when_context_is_none_and_metadata_has_no_user_id(self, monkeypatch):
        """Runtime context is None and metadata has no user_id → skip."""
        middleware = MemoryMiddleware()
        state = _state_with_messages()
        runtime = _make_runtime(context=None)

        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_memory_config",
            lambda: _memory_config(enabled=True),
        )
        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-1"}, "metadata": {}},
        )

        mock_queue = MagicMock()
        with patch("deerflow.agents.middlewares.memory_middleware.get_memory_queue", return_value=mock_queue):
            result = middleware.after_agent(state=state, runtime=runtime)

        assert result is None
        mock_queue.add.assert_not_called()


# ---------------------------------------------------------------------------
# Correct user_id propagation
# ---------------------------------------------------------------------------


class TestMemoryMiddlewareUserIdPropagation:
    """MemoryMiddleware must pass the correct user_id to the queue."""

    def test_queues_with_user_id_from_runtime_context(self, monkeypatch):
        """user_id in runtime.context is used for the queue entry."""
        middleware = MemoryMiddleware()
        state = _state_with_messages()
        runtime = _make_runtime(context={"thread_id": "thread-1", "user_id": USER_A})

        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_memory_config",
            lambda: _memory_config(enabled=True),
        )
        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-1"}, "metadata": {}},
        )

        mock_queue = MagicMock()
        with patch("deerflow.agents.middlewares.memory_middleware.get_memory_queue", return_value=mock_queue):
            middleware.after_agent(state=state, runtime=runtime)

        mock_queue.add.assert_called_once()
        call_kwargs = mock_queue.add.call_args.kwargs
        assert call_kwargs["user_id"] == USER_A
        assert call_kwargs["thread_id"] == "thread-1"

    def test_queues_with_user_id_from_run_metadata(self, monkeypatch):
        """user_id in run metadata is used when not in runtime.context."""
        middleware = MemoryMiddleware()
        state = _state_with_messages()
        runtime = _make_runtime(context={"thread_id": "thread-1"})

        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_memory_config",
            lambda: _memory_config(enabled=True),
        )
        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-1"}, "metadata": {"user_id": USER_B}},
        )

        mock_queue = MagicMock()
        with patch("deerflow.agents.middlewares.memory_middleware.get_memory_queue", return_value=mock_queue):
            middleware.after_agent(state=state, runtime=runtime)

        mock_queue.add.assert_called_once()
        call_kwargs = mock_queue.add.call_args.kwargs
        assert call_kwargs["user_id"] == USER_B

    def test_runtime_context_user_id_takes_precedence_over_metadata(self, monkeypatch):
        """runtime.context user_id wins over metadata user_id."""
        middleware = MemoryMiddleware()
        state = _state_with_messages()
        runtime = _make_runtime(context={"thread_id": "thread-1", "user_id": USER_A})

        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_memory_config",
            lambda: _memory_config(enabled=True),
        )
        monkeypatch.setattr(
            "deerflow.agents.middlewares.memory_middleware.get_config",
            lambda: {"configurable": {"thread_id": "thread-1"}, "metadata": {"user_id": USER_B}},
        )

        mock_queue = MagicMock()
        with patch("deerflow.agents.middlewares.memory_middleware.get_memory_queue", return_value=mock_queue):
            middleware.after_agent(state=state, runtime=runtime)

        mock_queue.add.assert_called_once()
        call_kwargs = mock_queue.add.call_args.kwargs
        assert call_kwargs["user_id"] == USER_A


# ---------------------------------------------------------------------------
# Prompt injection isolation: user A memory not injected into user B prompt
# ---------------------------------------------------------------------------


class TestMemoryPromptInjectionIsolation:
    """Lead agent prompt injection must use the run owner's user_id."""

    def test_get_memory_context_uses_provided_user_id(self):
        """_get_memory_context passes user_id to get_memory_data."""
        from deerflow.agents.lead_agent.prompt import _get_memory_context

        memory_a = {
            "version": "1.0",
            "lastUpdated": "",
            "user": {"workContext": {"summary": "User A context", "updatedAt": ""}, "personalContext": {"summary": "", "updatedAt": ""}, "topOfMind": {"summary": "", "updatedAt": ""}},
            "history": {"recentMonths": {"summary": "", "updatedAt": ""}, "earlierContext": {"summary": "", "updatedAt": ""}, "longTermBackground": {"summary": "", "updatedAt": ""}},
            "facts": [{"content": "User A fact", "category": "knowledge", "confidence": 0.9}],
        }
        memory_b = {
            "version": "1.0",
            "lastUpdated": "",
            "user": {"workContext": {"summary": "User B context", "updatedAt": ""}, "personalContext": {"summary": "", "updatedAt": ""}, "topOfMind": {"summary": "", "updatedAt": ""}},
            "history": {"recentMonths": {"summary": "", "updatedAt": ""}, "earlierContext": {"summary": "", "updatedAt": ""}, "longTermBackground": {"summary": "", "updatedAt": ""}},
            "facts": [{"content": "User B fact", "category": "knowledge", "confidence": 0.9}],
        }

        def _get_memory_data(user_id=None):
            if user_id == USER_A:
                return memory_a
            if user_id == USER_B:
                return memory_b
            return {}

        with (
            patch("deerflow.config.memory_config.get_memory_config") as mock_cfg,
            patch("deerflow.agents.memory.updater.get_memory_storage") as mock_storage,
        ):
            mock_cfg.return_value.enabled = True
            mock_cfg.return_value.injection_enabled = True
            mock_cfg.return_value.max_injection_tokens = 2000
            mock_storage.return_value.load.side_effect = _get_memory_data

            context_a = _get_memory_context(user_id=USER_A)
            context_b = _get_memory_context(user_id=USER_B)

        assert "User A fact" in context_a
        assert "User B fact" not in context_a

        assert "User B fact" in context_b
        assert "User A fact" not in context_b

    def test_user_a_memory_not_injected_into_user_b_prompt(self):
        """apply_prompt_template with user_b does not include user_a memory."""
        from deerflow.agents.lead_agent.prompt import apply_prompt_template

        memory_a = {
            "version": "1.0",
            "lastUpdated": "",
            "user": {"workContext": {"summary": "", "updatedAt": ""}, "personalContext": {"summary": "", "updatedAt": ""}, "topOfMind": {"summary": "", "updatedAt": ""}},
            "history": {"recentMonths": {"summary": "", "updatedAt": ""}, "earlierContext": {"summary": "", "updatedAt": ""}, "longTermBackground": {"summary": "", "updatedAt": ""}},
            "facts": [{"content": "SECRET_USER_A_FACT", "category": "knowledge", "confidence": 0.95}],
        }
        memory_b = {
            "version": "1.0",
            "lastUpdated": "",
            "user": {"workContext": {"summary": "", "updatedAt": ""}, "personalContext": {"summary": "", "updatedAt": ""}, "topOfMind": {"summary": "", "updatedAt": ""}},
            "history": {"recentMonths": {"summary": "", "updatedAt": ""}, "earlierContext": {"summary": "", "updatedAt": ""}, "longTermBackground": {"summary": "", "updatedAt": ""}},
            "facts": [{"content": "SECRET_USER_B_FACT", "category": "knowledge", "confidence": 0.95}],
        }

        def _get_memory_data(user_id=None):
            if user_id == USER_A:
                return memory_a
            if user_id == USER_B:
                return memory_b
            return {}

        with (
            patch("deerflow.config.memory_config.get_memory_config") as mock_cfg,
            patch("deerflow.agents.memory.updater.get_memory_storage") as mock_storage,
            patch("deerflow.agents.lead_agent.prompt.get_skills_prompt_section", return_value=""),
            patch("deerflow.agents.lead_agent.prompt.get_agent_soul", return_value=""),
            patch("deerflow.agents.lead_agent.prompt.get_deferred_tools_prompt_section", return_value=""),
        ):
            mock_cfg.return_value.enabled = True
            mock_cfg.return_value.injection_enabled = True
            mock_cfg.return_value.max_injection_tokens = 2000
            mock_storage.return_value.load.side_effect = _get_memory_data

            prompt_b = apply_prompt_template(user_id=USER_B)

        assert "SECRET_USER_A_FACT" not in prompt_b
        assert "SECRET_USER_B_FACT" in prompt_b
