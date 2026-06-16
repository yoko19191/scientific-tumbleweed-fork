"""Middleware that enforces a per-result budget on tool outputs."""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import replace as dc_replace
from typing import TYPE_CHECKING, Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command

from deerflow.config.tool_output_config import ToolOutputConfig
from deerflow.sandbox.sandbox_provider import get_sandbox_provider

if TYPE_CHECKING:
    from deerflow.sandbox.sandbox import Sandbox

logger = logging.getLogger(__name__)

_VIRTUAL_OUTPUTS_BASE = "/mnt/user-data/outputs"
_EXT_MAP: dict[str, str] = {
    "bash": "log",
    "bash_tool": "log",
    "web_fetch": "log",
}


def _message_text(content: Any) -> str | None:
    """Extract text from ToolMessage content, skipping multimodal content."""
    if isinstance(content, str):
        return content
    if content is None:
        return None
    if isinstance(content, list):
        pieces: list[str] = []
        for part in content:
            if isinstance(part, str):
                pieces.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                pieces.append(part["text"])
            else:
                return None
        return "\n".join(pieces) if pieces else None
    return None


def _snap_to_line_boundary(text: str, pos: int) -> int:
    if pos <= 0 or pos >= len(text):
        return pos
    half = pos // 2
    newline = text.rfind("\n", half, pos)
    return newline + 1 if newline >= 0 else pos


def _sanitize_tool_name(name: str) -> str:
    base = os.path.basename(name)
    safe = base.replace("..", "").replace("/", "_").replace("\\", "_")
    return safe or "unknown"


def _build_externalized_filename(*, tool_name: str, tool_call_id: str) -> str:
    safe_name = _sanitize_tool_name(tool_name)
    safe_call_id = _sanitize_tool_name(tool_call_id)[:24]
    ext = _EXT_MAP.get(tool_name, "txt")
    short_id = uuid.uuid4().hex[:12]
    if safe_call_id:
        return f"{safe_name}-{safe_call_id}-{short_id}.{ext}"
    return f"{safe_name}-{short_id}.{ext}"


def _externalize(
    content: str,
    *,
    tool_name: str,
    tool_call_id: str,
    outputs_path: str,
    storage_subdir: str,
) -> str | None:
    if os.path.isabs(storage_subdir) or ".." in storage_subdir:
        return None
    storage_dir = os.path.join(outputs_path, storage_subdir)
    try:
        os.makedirs(storage_dir, exist_ok=True)
    except OSError:
        return None

    filename = _build_externalized_filename(tool_name=tool_name, tool_call_id=tool_call_id)
    filepath = os.path.join(storage_dir, filename)
    if not os.path.abspath(filepath).startswith(os.path.abspath(storage_dir)):
        return None

    try:
        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write(content)
    except OSError:
        return None

    return f"{_VIRTUAL_OUTPUTS_BASE}/{storage_subdir}/{filename}"


def _externalize_to_sandbox(
    content: str,
    *,
    tool_name: str,
    tool_call_id: str,
    storage_subdir: str,
    sandbox: Sandbox,
) -> str | None:
    if os.path.isabs(storage_subdir) or ".." in storage_subdir:
        return None
    filename = _build_externalized_filename(tool_name=tool_name, tool_call_id=tool_call_id)
    virtual_dir = f"{_VIRTUAL_OUTPUTS_BASE}/{storage_subdir}"
    virtual_path = f"{virtual_dir}/{filename}"
    try:
        sandbox.execute_command(f"mkdir -p {shlex.quote(virtual_dir)}")
        sandbox.write_file(virtual_path, content)
        check = sandbox.execute_command(f"test -s {shlex.quote(virtual_path)} && echo OK || echo MISSING")
        if not isinstance(check, str) or check.strip() != "OK":
            logger.warning("Sandbox externalize validation failed: path=%s check=%r", virtual_path, check)
            return None
    except Exception:
        logger.exception("Failed to externalize %s output to sandbox (call_id=%s)", tool_name, tool_call_id)
        return None
    return virtual_path


def _build_preview(
    content: str,
    *,
    tool_name: str,
    virtual_path: str,
    head_chars: int,
    tail_chars: int,
) -> str:
    total = len(content)
    head_end = _snap_to_line_boundary(content, min(head_chars, total))
    tail_start = max(head_end, total - tail_chars)
    tail_start_snapped = _snap_to_line_boundary(content, tail_start)
    if tail_start_snapped > head_end:
        tail_start = tail_start_snapped

    head = content[:head_end]
    tail = content[tail_start:] if tail_start < total else ""
    omitted = total - len(head) - len(tail)
    ref = (
        f"\n\n[Full {tool_name} output saved to {virtual_path} "
        f"({total} chars, ~{total // 4} tokens). Use read_file with start_line "
        f"and end_line to access specific sections. {omitted} chars omitted from this preview.]\n\n"
    )
    return "".join([head, ref, tail])


def _build_fallback(
    content: str,
    *,
    tool_name: str,
    max_chars: int,
    head_chars: int,
    tail_chars: int,
) -> str:
    total = len(content)
    if max_chars <= 0 or total <= max_chars:
        return content

    marker_template = (
        "\n\n[... {n} chars omitted from {tn} output. Persistent storage unavailable. "
        "Consider narrowing the query or using more specific parameters.]\n\n"
    )
    marker_overhead = len(marker_template.format(n=total, tn=tool_name))
    if marker_overhead >= max_chars:
        return content[:max_chars]

    budget = max_chars - marker_overhead
    effective_head = min(head_chars, budget)
    effective_tail = min(tail_chars, max(0, budget - effective_head))

    head_end = _snap_to_line_boundary(content, min(effective_head, total))
    tail_start = max(head_end, total - effective_tail)
    tail_start_snapped = _snap_to_line_boundary(content, tail_start)
    if tail_start_snapped > head_end:
        tail_start = tail_start_snapped

    head = content[:head_end]
    tail = content[tail_start:] if tail_start < total else ""
    omitted = total - len(head) - len(tail)
    marker = marker_template.format(n=omitted, tn=tool_name)
    return "".join([head, marker, tail])


def _resolve_outputs_path(request: ToolCallRequest) -> str | None:
    runtime = getattr(request, "runtime", None)
    state = getattr(runtime, "state", None)
    if not isinstance(state, dict):
        return None
    thread_data = state.get("thread_data")
    if not isinstance(thread_data, dict):
        return None
    outputs_path = thread_data.get("outputs_path")
    return outputs_path if isinstance(outputs_path, str) else None


def _provider_variant_from_runtime(runtime: Any) -> str | None:
    if runtime is None:
        return None
    context = getattr(runtime, "context", None)
    if isinstance(context, dict):
        variant = context.get("sandbox_provider_variant") or context.get("agent_variant")
        if isinstance(variant, str):
            return variant
    runtime_config = getattr(runtime, "config", None)
    if isinstance(runtime_config, dict):
        configurable = runtime_config.get("configurable", {})
        if isinstance(configurable, dict):
            variant = configurable.get("sandbox_provider_variant") or configurable.get("agent_variant")
            if isinstance(variant, str):
                return variant
    return None


def _resolve_sandbox_context(request: ToolCallRequest) -> tuple[Sandbox | None, bool]:
    runtime = getattr(request, "runtime", None)
    state = getattr(runtime, "state", None)
    if not isinstance(state, dict):
        return None, False
    sandbox_state = state.get("sandbox")
    if not isinstance(sandbox_state, dict):
        return None, False
    sandbox_id = sandbox_state.get("sandbox_id")
    if not sandbox_id:
        return None, False
    try:
        provider = get_sandbox_provider(variant=_provider_variant_from_runtime(runtime))
        return provider.get(sandbox_id), bool(getattr(provider, "uses_thread_data_mounts", False))
    except Exception:
        logger.exception("Failed to look up sandbox %s for tool-output externalization", sandbox_id)
        return None, False


def _budget_content(
    content: str,
    *,
    tool_name: str,
    tool_call_id: str,
    outputs_path: str | None,
    config: ToolOutputConfig,
    sandbox: Sandbox | None = None,
    uses_thread_data_mounts: bool = False,
) -> str | None:
    threshold = config.tool_overrides.get(tool_name, config.externalize_min_chars)
    if threshold <= 0 and config.fallback_max_chars <= 0:
        return None
    if len(content) <= threshold and len(content) <= config.fallback_max_chars:
        return None

    if threshold > 0 and len(content) > threshold:
        virtual_path: str | None = None
        if sandbox is not None:
            if uses_thread_data_mounts:
                if outputs_path:
                    virtual_path = _externalize(
                        content,
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        outputs_path=outputs_path,
                        storage_subdir=config.storage_subdir,
                    )
            else:
                virtual_path = _externalize_to_sandbox(
                    content,
                    tool_name=tool_name,
                    tool_call_id=tool_call_id,
                    storage_subdir=config.storage_subdir,
                    sandbox=sandbox,
                )
        elif outputs_path:
            virtual_path = _externalize(
                content,
                tool_name=tool_name,
                tool_call_id=tool_call_id,
                outputs_path=outputs_path,
                storage_subdir=config.storage_subdir,
            )

        if virtual_path is not None:
            return _build_preview(
                content,
                tool_name=tool_name,
                virtual_path=virtual_path,
                head_chars=config.preview_head_chars,
                tail_chars=config.preview_tail_chars,
            )

    if config.fallback_max_chars > 0 and len(content) > config.fallback_max_chars:
        return _build_fallback(
            content,
            tool_name=tool_name,
            max_chars=config.fallback_max_chars,
            head_chars=config.fallback_head_chars,
            tail_chars=config.fallback_tail_chars,
        )

    return None


def _patch_tool_message(
    msg: ToolMessage,
    config: ToolOutputConfig,
    outputs_path: str | None,
    sandbox: Sandbox | None = None,
    uses_thread_data_mounts: bool = False,
) -> ToolMessage:
    tool_name = msg.name or "unknown"
    if tool_name in config.exempt_tools:
        return msg

    text = _message_text(msg.content)
    if text is None:
        return msg

    replacement = _budget_content(
        text,
        tool_name=tool_name,
        tool_call_id=msg.tool_call_id or "",
        outputs_path=outputs_path,
        config=config,
        sandbox=sandbox,
        uses_thread_data_mounts=uses_thread_data_mounts,
    )
    if replacement is None:
        return msg

    update: dict[str, Any] = {"content": replacement}
    if getattr(msg, "response_metadata", None):
        update["response_metadata"] = dict(msg.response_metadata)
    if getattr(msg, "additional_kwargs", None):
        update["additional_kwargs"] = dict(msg.additional_kwargs)
    return msg.model_copy(update=update)


def _effective_trigger(tool_name: str, config: ToolOutputConfig) -> int:
    candidates: list[int] = []
    externalize = config.tool_overrides.get(tool_name, config.externalize_min_chars)
    if externalize > 0:
        candidates.append(externalize)
    if config.fallback_max_chars > 0:
        candidates.append(config.fallback_max_chars)
    return min(candidates) if candidates else -1


def _tool_message_over_budget(msg: ToolMessage, config: ToolOutputConfig) -> bool:
    if (msg.name or "") in config.exempt_tools:
        return False
    trigger = _effective_trigger(msg.name or "", config)
    if trigger < 0:
        return False
    text = _message_text(msg.content)
    return text is not None and len(text) > trigger


def _needs_budget(result: ToolMessage | Command, config: ToolOutputConfig) -> bool:
    if isinstance(result, ToolMessage):
        return _tool_message_over_budget(result, config)
    update = getattr(result, "update", None)
    if isinstance(update, dict):
        return any(isinstance(msg, ToolMessage) and _tool_message_over_budget(msg, config) for msg in update.get("messages", []))
    return False


def _patch_result(
    result: ToolMessage | Command,
    config: ToolOutputConfig,
    outputs_path: str | None,
    sandbox: Sandbox | None = None,
    uses_thread_data_mounts: bool = False,
) -> ToolMessage | Command:
    if isinstance(result, ToolMessage):
        return _patch_tool_message(result, config, outputs_path, sandbox, uses_thread_data_mounts)

    update = getattr(result, "update", None)
    if not isinstance(update, dict):
        return result
    messages = update.get("messages")
    if not isinstance(messages, list):
        return result

    changed = False
    new_messages: list[Any] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            patched = _patch_tool_message(msg, config, outputs_path, sandbox, uses_thread_data_mounts)
            changed = changed or patched is not msg
            new_messages.append(patched)
        else:
            new_messages.append(msg)

    if not changed:
        return result
    return dc_replace(result, update={**update, "messages": new_messages})


def _patch_model_messages(messages: list[Any], config: ToolOutputConfig) -> list[Any] | None:
    if not any(isinstance(msg, ToolMessage) and _tool_message_over_budget(msg, config) for msg in messages):
        return None

    changed = False
    updated: list[Any] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            patched = _patch_tool_message(msg, config, outputs_path=None)
            changed = changed or patched is not msg
            updated.append(patched)
        else:
            updated.append(msg)
    return updated if changed else None


class ToolOutputBudgetMiddleware(AgentMiddleware[AgentState]):
    """Externalize or truncate oversized tool outputs before they hit model context."""

    def __init__(self, config: ToolOutputConfig | None = None) -> None:
        super().__init__()
        self._config = config if config is not None else ToolOutputConfig()

    @classmethod
    def from_app_config(cls, app_config: Any) -> ToolOutputBudgetMiddleware:
        tool_output = getattr(app_config, "tool_output", None)
        if isinstance(tool_output, ToolOutputConfig):
            return cls(config=tool_output)
        return cls()

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        result = handler(request)
        if not self._config.enabled or not _needs_budget(result, self._config):
            return result
        sandbox, uses_thread_data_mounts = _resolve_sandbox_context(request)
        return _patch_result(
            result,
            self._config,
            _resolve_outputs_path(request),
            sandbox,
            uses_thread_data_mounts,
        )

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        result = await handler(request)
        if not self._config.enabled or not _needs_budget(result, self._config):
            return result
        outputs_path = _resolve_outputs_path(request)
        sandbox, uses_thread_data_mounts = _resolve_sandbox_context(request)
        return await asyncio.to_thread(_patch_result, result, self._config, outputs_path, sandbox, uses_thread_data_mounts)

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        if self._config.enabled:
            messages = getattr(request, "messages", None)
            if isinstance(messages, list):
                patched = _patch_model_messages(messages, self._config)
                if patched is not None:
                    request = request.override(messages=patched)
        return handler(request)

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        if self._config.enabled:
            messages = getattr(request, "messages", None)
            if isinstance(messages, list):
                patched = _patch_model_messages(messages, self._config)
                if patched is not None:
                    request = request.override(messages=patched)
        return await handler(request)
