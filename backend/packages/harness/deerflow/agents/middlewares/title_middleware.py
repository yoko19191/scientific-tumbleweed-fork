"""Middleware for automatic thread title generation."""

import logging
from typing import TYPE_CHECKING, NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langgraph.runtime import Runtime

from deerflow.agents import title_agent
from deerflow.agents.middlewares.dynamic_context_middleware import is_dynamic_context_reminder
from deerflow.config.title_config import get_title_config
from deerflow.models import create_chat_model

if TYPE_CHECKING:
    from deerflow.config.app_config import AppConfig
    from deerflow.config.title_config import TitleConfig

logger = logging.getLogger(__name__)


class TitleMiddlewareState(AgentState):
    """Compatible with the `ThreadState` schema."""

    title: NotRequired[str | None]


class TitleMiddleware(AgentMiddleware[TitleMiddlewareState]):
    """Automatically generate a title for the thread after the first user message."""

    state_schema = TitleMiddlewareState

    def __init__(self, *, app_config: "AppConfig | None" = None, title_config: "TitleConfig | None" = None):
        super().__init__()
        self._app_config = app_config
        self._title_config = title_config

    def _get_title_config(self) -> "TitleConfig":
        if self._title_config is not None:
            return self._title_config
        if self._app_config is not None:
            return self._app_config.title
        return get_title_config()

    def _normalize_content(self, content: object) -> str:
        return title_agent.normalize_content(content)

    @staticmethod
    def _is_user_message_for_title(message: object) -> bool:
        return getattr(message, "type", None) == "human" and not is_dynamic_context_reminder(message)

    def _should_generate_title(self, state: TitleMiddlewareState) -> bool:
        """Check if we should generate a title for this thread."""
        config = self._get_title_config()
        if not config.enabled:
            return False

        # Check if thread already has a title in state
        if state.get("title"):
            return False

        # Check if this is the first turn (has at least one user message and one assistant response)
        messages = state.get("messages", [])
        if len(messages) < 2:
            return False

        # Count user and assistant messages
        user_messages = [m for m in messages if self._is_user_message_for_title(m)]
        assistant_messages = [m for m in messages if m.type == "ai"]

        # Generate title after first complete exchange
        return len(user_messages) == 1 and len(assistant_messages) >= 1

    def _extract_title_messages(self, state: TitleMiddlewareState) -> tuple[str, str]:
        messages = state.get("messages", [])

        user_msg_content = next((m.content for m in messages if self._is_user_message_for_title(m)), "")
        assistant_msg_content = next((m.content for m in messages if m.type == "ai"), "")

        user_msg = self._normalize_content(user_msg_content)
        assistant_msg = self._normalize_content(assistant_msg_content)
        return user_msg, assistant_msg

    def _build_title_prompt(self, state: TitleMiddlewareState) -> tuple[str, str]:
        """Extract user/assistant messages and build the title prompt.

        Returns (prompt_string, user_msg) so callers can use user_msg as fallback.
        """
        config = self._get_title_config()
        user_msg, assistant_msg = self._extract_title_messages(state)
        prompt = title_agent.build_title_prompt(user_msg, assistant_msg, config)
        return prompt, user_msg

    def _strip_think_tags(self, text: str) -> str:
        return title_agent.strip_think_tags(text)

    def _parse_title(self, content: object) -> str:
        return title_agent.parse_title(content, self._get_title_config())

    def _fallback_title(self, user_msg: str) -> str:
        return title_agent.fallback_title(user_msg, self._get_title_config())

    def _generate_title_result(self, state: TitleMiddlewareState) -> dict | None:
        """Generate a local fallback title without blocking on an LLM call."""
        if not self._should_generate_title(state):
            return None

        user_msg, _ = self._extract_title_messages(state)
        return {"title": self._fallback_title(user_msg)}

    async def _agenerate_title_result(self, state: TitleMiddlewareState) -> dict | None:
        """Generate a title asynchronously and fall back locally on failure."""
        if not self._should_generate_title(state):
            return None

        config = self._get_title_config()
        user_msg, assistant_msg = self._extract_title_messages(state)
        title = await title_agent.generate_title(
            user_msg,
            assistant_msg,
            config,
            app_config=self._app_config,
            model_factory=create_chat_model,
        )
        return {"title": title}

    @override
    def after_model(self, state: TitleMiddlewareState, runtime: Runtime) -> dict | None:
        return self._generate_title_result(state)

    @override
    async def aafter_model(self, state: TitleMiddlewareState, runtime: Runtime) -> dict | None:
        return await self._agenerate_title_result(state)
