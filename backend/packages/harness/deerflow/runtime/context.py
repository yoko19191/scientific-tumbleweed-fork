"""Canonical runtime context passed into LangGraph ``Runtime.context``."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeContext:
    """Resolved runtime context for one agent run."""

    thread_id: str
    run_id: str
    user_id: str | None = None
    agent_name: str | None = None
    app_config: Any | None = None
    values: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(
        cls,
        *,
        thread_id: str,
        run_id: str,
        config: Mapping[str, Any],
        app_config: Any | None = None,
    ) -> RuntimeContext:
        raw_context = config.get("context")
        context_values = dict(raw_context) if isinstance(raw_context, Mapping) else {}
        metadata = config.get("metadata") if isinstance(config.get("metadata"), Mapping) else {}
        configurable = config.get("configurable") if isinstance(config.get("configurable"), Mapping) else {}

        user_id = context_values.get("user_id")
        if user_id is None:
            user_id = metadata.get("user_id")

        agent_name = context_values.get("agent_name")
        if agent_name is None:
            agent_name = configurable.get("agent_name")

        return cls(
            thread_id=thread_id,
            run_id=run_id,
            user_id=str(user_id) if user_id is not None else None,
            agent_name=str(agent_name) if agent_name is not None else None,
            app_config=app_config,
            values=context_values,
        )

    def to_dict(self) -> dict[str, Any]:
        data = dict(self.values)
        data["thread_id"] = self.thread_id
        data["run_id"] = self.run_id
        if self.user_id is not None:
            data["user_id"] = self.user_id
        if self.agent_name is not None:
            data["agent_name"] = self.agent_name
        if self.app_config is not None:
            data["app_config"] = self.app_config
        return data


def install_runtime_context(config: dict[str, Any], runtime_context: RuntimeContext) -> None:
    """Install canonical context into a RunnableConfig dict."""
    config["context"] = runtime_context.to_dict()
