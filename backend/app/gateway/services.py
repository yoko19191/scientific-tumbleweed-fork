"""Run lifecycle service layer.

Centralizes the business logic for creating runs, formatting SSE
frames, and consuming stream bridge events.  Router modules
(``thread_runs``, ``runs``) are thin HTTP handlers that delegate here.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, Request
from langchain_core.messages import BaseMessage
from langchain_core.messages.utils import convert_to_messages

from app.gateway.deps import get_checkpointer, get_config, get_run_manager, get_store, get_stream_bridge
from deerflow.runtime import (
    END_SENTINEL,
    HEARTBEAT_SENTINEL,
    ConflictError,
    DisconnectMode,
    RunManager,
    RunRecord,
    RunStatus,
    StreamBridge,
    UnsupportedStrategyError,
    format_sse_frame,
    run_agent,
)
from deerflow.runtime.runs.checkpoints import read_thread_checkpoint_values
from deerflow.runtime.runs.naming import resolve_root_run_name

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SSE formatting
# ---------------------------------------------------------------------------


def format_sse(event: str, data: Any, *, event_id: str | None = None) -> str:
    """Format a single SSE frame.

    Field order: ``event:`` -> ``data:`` -> ``id:`` (optional) -> blank line.
    This matches the LangGraph Platform wire format consumed by the
    ``useStream`` React hook and the Python ``langgraph-sdk`` SSE decoder.
    """
    return format_sse_frame(event, data, event_id=event_id)


# ---------------------------------------------------------------------------
# Input / config helpers
# ---------------------------------------------------------------------------


def normalize_stream_modes(raw: list[str] | str | None) -> list[str]:
    """Normalize the stream_mode parameter to a list.

    Default matches what ``useStream`` expects: values + messages-tuple.
    """
    if raw is None:
        return ["values"]
    if isinstance(raw, str):
        return [raw]
    return raw if raw else ["values"]


def normalize_input(raw_input: dict[str, Any] | None) -> dict[str, Any]:
    """Convert LangGraph Platform input format to LangChain state dict.

    Delegates dict→message coercion to ``langchain_core.messages.utils.convert_to_messages``
    so that ``additional_kwargs`` (e.g. uploaded-file metadata — gh #3132), ``id``,
    ``name``, and non-human roles (ai/system/tool) survive unchanged.  An earlier
    hand-rolled version only forwarded ``content`` and collapsed every role to
    ``HumanMessage``, which silently stripped frontend-supplied attachments.

    Malformed message dicts (missing ``role``/``type``/``content``, unsupported
    role, etc.) raise ``HTTPException(400)`` with the offending index, instead
    of bubbling up as a 500.  The gateway is a system boundary, so per-entry
    validation errors are the right shape for clients to retry against.
    """
    if raw_input is None:
        return {}
    messages = raw_input.get("messages")
    if messages and isinstance(messages, list):
        converted: list[Any] = []
        for index, msg in enumerate(messages):
            if isinstance(msg, BaseMessage):
                converted.append(msg)
            elif isinstance(msg, dict):
                try:
                    converted.extend(convert_to_messages([msg]))
                except (ValueError, TypeError, NotImplementedError) as exc:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid message at input.messages[{index}]: {exc}",
                    ) from exc
            else:
                converted.append(msg)
        return {**raw_input, "messages": converted}
    return raw_input


_DEFAULT_ASSISTANT_ID = "chat_lead_agent"
_KNOWN_GRAPH_IDS = {"chat_lead_agent", "computer_lead_agent"}
_MAX_MODEL_NAME_LEN = 128
_RUNTIME_CONTEXT_CONFIG_KEYS = frozenset(
    {
        "model_name",
        "mode",
        "thinking_enabled",
        "reasoning_effort",
        "is_plan_mode",
        "subagent_enabled",
        "max_concurrent_subagents",
        "tone_style",
    }
)


def _coerce_model_name(value: Any) -> str | None:
    """Normalize model_name values before persistence and allowlist checks."""
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    value = value.strip()
    if not value:
        return None
    return value[:_MAX_MODEL_NAME_LEN]


def _extract_requested_model_name(body: Any) -> str | None:
    """Extract model_name from request context/config with body.context precedence."""
    body_context = getattr(body, "context", None)
    if isinstance(body_context, Mapping):
        model_name = _coerce_model_name(body_context.get("model_name"))
        if model_name is not None:
            return model_name

    body_config = getattr(body, "config", None)
    if isinstance(body_config, Mapping):
        config_context = body_config.get("context")
        config_configurable = body_config.get("configurable")
        if isinstance(config_context, Mapping):
            model_name = _coerce_model_name(config_context.get("model_name"))
            if model_name is not None:
                return model_name
        if isinstance(config_configurable, Mapping):
            return _coerce_model_name(config_configurable.get("model_name"))
    return None


def resolve_agent_factory(assistant_id: str | None):
    """Resolve the graph factory for first-class graph ids and custom agents."""
    from deerflow.agents.lead_agent import make_chat_lead_agent, make_computer_lead_agent

    if assistant_id == "computer_lead_agent":
        return make_computer_lead_agent
    if assistant_id == "chat_lead_agent" or assistant_id is None:
        return make_chat_lead_agent
    return make_computer_lead_agent


def build_run_config(
    thread_id: str,
    request_config: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    *,
    assistant_id: str | None = None,
) -> dict[str, Any]:
    """Build a RunnableConfig dict for the agent.

    When *assistant_id* refers to a custom agent (anything other than a known
    graph id / ``None``), the name is forwarded as ``agent_name`` in
    whichever runtime options container is active: ``context`` for
    LangGraph >= 0.6.0 requests, otherwise ``configurable``.
    the computer lead factory reads this key to load the matching
    ``agents/<name>/SOUL.md`` and per-agent config — without it the agent
    silently runs as the default lead agent.

    This mirrors the channel manager's ``_resolve_run_params`` logic so that
    the LangGraph Platform-compatible HTTP API and the IM channel path behave
    identically.
    """
    configurable: dict[str, Any] = {"thread_id": thread_id}
    config: dict[str, Any] = {"configurable": configurable, "recursion_limit": 100}
    if request_config:
        # LangGraph >= 0.6.0 introduced ``context`` as the preferred way to
        # pass thread-level data and rejects requests that include both
        # ``configurable`` and ``context``.  If the caller already sends
        # ``context``, honour it and skip our own ``configurable`` dict.
        if "context" in request_config:
            if "configurable" in request_config:
                logger.warning(
                    "build_run_config: client sent both 'context' and 'configurable'; preferring 'context' (LangGraph >= 0.6.0). thread_id=%s, caller_configurable keys=%s",
                    thread_id,
                    list(request_config.get("configurable", {}).keys()),
                )
            context_value = request_config["context"]
            if context_value is None:
                context = {}
            elif isinstance(context_value, Mapping):
                context = dict(context_value)
            else:
                raise ValueError("request config 'context' must be a mapping or null.")
            config.pop("configurable", None)
            config["context"] = context
        else:
            configurable = {"thread_id": thread_id}
            configurable.update(request_config.get("configurable", {}))
            config["configurable"] = configurable
        for k, v in request_config.items():
            if k not in ("configurable", "context"):
                config[k] = v
    else:
        config["configurable"] = {"thread_id": thread_id}

    # Inject custom agent name when the caller specified a non-default assistant.
    # Honour an explicit agent_name in the active runtime options container.
    if assistant_id and assistant_id not in _KNOWN_GRAPH_IDS:
        normalized = assistant_id.strip().lower().replace("_", "-")
        if not normalized or not re.fullmatch(r"[a-z0-9-]+", normalized):
            raise ValueError(f"Invalid assistant_id {assistant_id!r}: must contain only letters, digits, and hyphens after normalization.")
        if "configurable" in config:
            target = config["configurable"]
        elif "context" in config:
            target = config["context"]
        else:
            target = config.setdefault("configurable", {})
        if target is not None and "agent_name" not in target:
            target["agent_name"] = normalized
        config.setdefault("run_name", resolve_root_run_name(config, normalized))
    if metadata:
        config.setdefault("metadata", {}).update(metadata)
    return config


def apply_runtime_context_overrides(config: dict[str, Any], context: Mapping[str, Any] | None) -> dict[str, Any]:
    """Merge request body context into the active runtime options container.

    If the caller already selected LangGraph ``context`` mode through
    ``config["context"]``, overrides stay in that container. Otherwise they
    are added to ``config["configurable"]`` for backward compatibility.
    """
    if not context:
        return config

    if "context" in config:
        target = config["context"]
        if target is None:
            target = {}
            config["context"] = target
        if not isinstance(target, dict):
            raise ValueError("run config 'context' must be a mapping or null.")
    else:
        target = config.setdefault("configurable", {})
        if not isinstance(target, dict):
            raise ValueError("run config 'configurable' must be a mapping.")

    for key in _RUNTIME_CONTEXT_CONFIG_KEYS:
        if key in context:
            target.setdefault(key, context[key])
    return config


# ---------------------------------------------------------------------------
# Run lifecycle
# ---------------------------------------------------------------------------


async def _upsert_thread_in_store(store, thread_id: str, metadata: dict | None, user_id: str | None) -> None:
    """Create or refresh the thread record in the Store.

    Called from :func:`start_run` so that threads created via the stateless
    ``/runs/stream`` endpoint (which never calls ``POST /threads``) still
    appear in ``/threads/search`` results.
    """
    # Deferred import to avoid circular import with the threads router module.
    from app.gateway.routers.threads import _store_upsert
    from app.gateway.user_prefix import user_threads_namespace

    try:
        threads_ns = user_threads_namespace(user_id) if user_id else ("threads",)
        await _store_upsert(store, thread_id, metadata=metadata, ns=threads_ns)
    except Exception:
        logger.warning("Failed to upsert thread %s in store (non-fatal)", thread_id)


async def _sync_thread_title_after_run(
    run_task: asyncio.Task,
    thread_id: str,
    checkpointer: Any,
    store: Any,
    user_id: str | None = None,
) -> None:
    """Wait for *run_task* to finish, then persist the generated title to the Store.

    TitleMiddleware writes the generated title to the LangGraph agent state
    (checkpointer) but the Gateway's Store record is not updated automatically.
    This coroutine closes that gap by reading the final checkpoint after the
    run completes and syncing ``values.title`` into the Store record so that
    subsequent ``/threads/search`` responses include the correct title.

    Runs as a fire-and-forget :func:`asyncio.create_task`; failures are
    logged at DEBUG level and never propagate.
    """
    # Wait for the background run task to complete (any outcome).
    # asyncio.wait does not propagate task exceptions — it just returns
    # when the task is done, cancelled, or failed.
    await asyncio.wait({run_task})

    # Deferred import to avoid circular import with the threads router module.
    from app.gateway.routers.threads import _store_get, _store_put
    from app.gateway.user_prefix import user_threads_namespace

    try:
        threads_ns = user_threads_namespace(user_id) if user_id else ("threads",)

        channel_values = await read_thread_checkpoint_values(checkpointer, thread_id)
        if channel_values is None:
            return
        title = channel_values.get("title")
        if not title:
            return

        existing = await _store_get(store, thread_id, ns=threads_ns)
        if existing is None:
            return

        updated = dict(existing)
        updated.setdefault("values", {})["title"] = title
        updated["updated_at"] = time.time()
        await _store_put(store, updated, ns=threads_ns)
        logger.debug("Synced title %r for thread %s", title, thread_id)
    except Exception:
        logger.debug("Failed to sync title for thread %s (non-fatal)", thread_id, exc_info=True)


async def start_run(
    body: Any,
    thread_id: str,
    request: Request,
) -> RunRecord:
    """Create a RunRecord and launch the background agent task.

    Parameters
    ----------
    body : RunCreateRequest
        The validated request body (typed as Any to avoid circular import
        with the router module that defines the Pydantic model).
    thread_id : str
        Target thread.
    request : Request
        FastAPI request — used to retrieve singletons from ``app.state``.
    """
    bridge = get_stream_bridge(request)
    run_mgr = get_run_manager(request)
    checkpointer = get_checkpointer(request)
    store = get_store(request)
    app_config = get_config()

    disconnect = DisconnectMode.cancel if body.on_disconnect == "cancel" else DisconnectMode.continue_

    # Resolve authenticated user before creating the run so persisted run rows
    # carry the same ownership boundary as thread records.
    from app.gateway.deps import get_optional_user_from_request

    user = await get_optional_user_from_request(request)
    user_id = str(user.id) if user else None
    if user_id:
        run_metadata = dict(body.metadata) if body.metadata else {}
        run_metadata["user_id"] = user_id
    else:
        run_metadata = body.metadata or {}

    model_name = _extract_requested_model_name(body)
    if model_name and app_config.get_model_config(model_name) is None:
        raise HTTPException(
            status_code=400,
            detail=f"Model {model_name!r} is not in the configured model allowlist",
        )

    try:
        record = await run_mgr.create_or_reject(
            thread_id,
            body.assistant_id,
            on_disconnect=disconnect,
            metadata=run_metadata,
            kwargs={"input": body.input, "config": body.config},
            multitask_strategy=body.multitask_strategy,
            model_name=model_name,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UnsupportedStrategyError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    agent_factory = resolve_agent_factory(body.assistant_id)
    graph_input = normalize_input(body.input)

    # Ensure the thread is visible in /threads/search, even for threads that
    # were never explicitly created via POST /threads (e.g. stateless runs).
    store = get_store(request)
    if store is not None:
        await _upsert_thread_in_store(store, thread_id, body.metadata, user_id)

    config = build_run_config(thread_id, body.config, run_metadata, assistant_id=body.assistant_id)

    # Merge Scientific Tumbleweed-specific context overrides into the active
    # runtime options container. Unknown keys such as body.context.thread_id are
    # intentionally ignored; canonical thread_id/run_id/user_id are resolved by
    # the runtime context interface when the run executes.
    apply_runtime_context_overrides(config, getattr(body, "context", None))

    stream_modes = normalize_stream_modes(body.stream_mode)

    task = asyncio.create_task(
        run_agent(
            bridge,
            run_mgr,
            record,
            checkpointer=checkpointer,
            store=store,
            agent_factory=agent_factory,
            graph_input=graph_input,
            config=config,
            stream_modes=stream_modes,
            stream_subgraphs=body.stream_subgraphs,
            interrupt_before=body.interrupt_before,
            interrupt_after=body.interrupt_after,
            app_config=app_config,
        )
    )
    record.task = task

    # After the run completes, sync the title generated by TitleMiddleware from
    # the checkpointer into the Store record so that /threads/search returns the
    # correct title instead of an empty values dict.
    if store is not None:
        asyncio.create_task(_sync_thread_title_after_run(task, thread_id, checkpointer, store, user_id))

    return record


async def sse_consumer(
    bridge: StreamBridge,
    record: RunRecord,
    request: Request,
    run_mgr: RunManager,
):
    """Async generator that yields SSE frames from the bridge.

    The ``finally`` block implements ``on_disconnect`` semantics:
    - ``cancel``: abort the background task on client disconnect.
    - ``continue``: let the task run; events are discarded.
    """
    last_event_id = request.headers.get("Last-Event-ID")
    try:
        async for entry in bridge.subscribe(record.run_id, last_event_id=last_event_id):
            if await request.is_disconnected():
                break

            if entry is HEARTBEAT_SENTINEL:
                yield ": heartbeat\n\n"
                continue

            if entry is END_SENTINEL:
                yield format_sse("end", None, event_id=entry.id or None)
                return

            yield format_sse(entry.event, entry.data, event_id=entry.id or None)

    finally:
        if record.status in (RunStatus.pending, RunStatus.running):
            if record.on_disconnect == DisconnectMode.cancel:
                await run_mgr.cancel(record.run_id)
