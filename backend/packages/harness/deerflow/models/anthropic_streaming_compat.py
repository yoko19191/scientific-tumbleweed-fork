"""Compatibility patches for Anthropic-compatible streaming responses."""

from __future__ import annotations

from typing import Any


class _ModelDumpDict:
    """Small adapter for dicts returned where LangChain expects SDK models."""

    def __init__(self, value: dict[str, Any]) -> None:
        self._value = value

    def model_dump(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._value


class _AttrProxy:
    """Proxy an SDK event while overriding selected attributes."""

    def __init__(self, target: Any, **overrides: Any) -> None:
        self._target = target
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._target, name)


def patch_langchain_anthropic_streaming_dict_metadata() -> None:
    """Allow dict metadata in LangChain Anthropic streaming events.

    Some Anthropic-compatible gateways return ``context_management`` or
    ``delta.container`` as plain dicts in streaming ``message_delta`` events.
    ``langchain-anthropic==1.3.4`` assumes Anthropic SDK model instances and
    calls ``model_dump()``, which raises ``AttributeError`` at the end of the
    stream. This patch adapts only those dict metadata fields and leaves the
    original converter behavior intact for official SDK objects.
    """
    import langchain_anthropic.chat_models as chat_models

    original = chat_models._make_message_chunk_from_anthropic_event
    if getattr(original, "_deerflow_dict_metadata_compat", False):
        return

    def patched_make_message_chunk_from_anthropic_event(event: Any, *args: Any, **kwargs: Any) -> Any:
        if getattr(event, "type", None) != "message_delta":
            return original(event, *args, **kwargs)

        event_for_call = event
        context_management = getattr(event, "context_management", None)
        if isinstance(context_management, dict):
            event_for_call = _AttrProxy(
                event_for_call,
                context_management=_ModelDumpDict(context_management),
            )

        delta = getattr(event, "delta", None)
        container = getattr(delta, "container", None) if delta is not None else None
        if isinstance(container, dict):
            delta_for_call = _AttrProxy(delta, container=_ModelDumpDict(container))
            event_for_call = _AttrProxy(event_for_call, delta=delta_for_call)

        return original(event_for_call, *args, **kwargs)

    patched_make_message_chunk_from_anthropic_event._deerflow_dict_metadata_compat = True  # type: ignore[attr-defined]
    patched_make_message_chunk_from_anthropic_event._deerflow_original = original  # type: ignore[attr-defined]
    chat_models._make_message_chunk_from_anthropic_event = patched_make_message_chunk_from_anthropic_event
