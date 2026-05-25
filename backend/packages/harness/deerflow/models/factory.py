import logging

from langchain.chat_models import BaseChatModel

from deerflow.config import get_app_config
from deerflow.models.anthropic_streaming_compat import patch_langchain_anthropic_streaming_dict_metadata
from deerflow.reflection import resolve_class
from deerflow.tracing import build_tracing_callbacks

logger = logging.getLogger(__name__)


def _deep_merge_dicts(base: dict | None, override: dict) -> dict:
    """Recursively merge two dictionaries without mutating the inputs."""
    merged = dict(base or {})
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _vllm_disable_chat_template_kwargs(chat_template_kwargs: dict) -> dict:
    """Build the disable payload for vLLM/Qwen chat template kwargs."""
    disable_kwargs: dict[str, bool] = {}
    if "thinking" in chat_template_kwargs:
        disable_kwargs["thinking"] = False
    if "enable_thinking" in chat_template_kwargs:
        disable_kwargs["enable_thinking"] = False
    return disable_kwargs


def _uses_anthropic_request_shape(model_use: str) -> bool:
    """Return whether the model constructor emits Anthropic Messages API payloads."""
    return model_use in {
        "langchain_anthropic:ChatAnthropic",
        "deerflow.models.claude_provider:ClaudeChatModel",
    }


def _is_deepseek_model(model_name: str) -> bool:
    """Return whether the model name indicates a DeepSeek model."""
    return model_name.lower().startswith("deepseek-")


_DEEPSEEK_VALID_EFFORTS = {"high", "max"}
_ANTHROPIC_VALID_EFFORTS = {"low", "medium", "high", "max"}

_DEEPSEEK_EFFORT_MAP = {
    "minimal": "high",
    "low": "high",
    "medium": "high",
    "xhigh": "max",
}


def _deepseek_effort(reasoning_effort: str) -> str | None:
    """Normalise a frontend effort label to a value DeepSeek accepts.

    DeepSeek API only has two meaningful levels: high and max.
    low/medium/minimal all map to high; xhigh maps to max.
    """
    if reasoning_effort in _DEEPSEEK_VALID_EFFORTS:
        return reasoning_effort
    return _DEEPSEEK_EFFORT_MAP.get(reasoning_effort)


def _anthropic_effort(reasoning_effort: str | None) -> str | None:
    """Return a ChatAnthropic-native effort value if valid."""
    if reasoning_effort in _ANTHROPIC_VALID_EFFORTS:
        return reasoning_effort
    return None


def _enable_stream_usage_by_default(model_use_path: str, model_settings_from_config: dict) -> None:
    """Enable stream usage for OpenAI-compatible models unless explicitly configured.

    LangChain only auto-enables ``stream_usage`` for OpenAI models when no custom
    base URL or client is configured. DeerFlow frequently uses OpenAI-compatible
    gateways, so token usage tracking would otherwise stay empty and the
    TokenUsageMiddleware would have nothing to log.
    """
    if model_use_path != "langchain_openai:ChatOpenAI":
        return
    if "stream_usage" in model_settings_from_config:
        return
    if "base_url" in model_settings_from_config or "openai_api_base" in model_settings_from_config:
        model_settings_from_config["stream_usage"] = True


def create_chat_model(name: str | None = None, thinking_enabled: bool = False, **kwargs) -> BaseChatModel:
    """Create a chat model instance from the config.

    Args:
        name: The name of the model to create. If None, the first model in the config will be used.

    Returns:
        A chat model instance.
    """
    config = kwargs.pop("app_config", None) or get_app_config()
    if name is None:
        name = config.models[0].name
    model_config = config.get_model_config(name)
    if model_config is None:
        raise ValueError(f"Model {name} not found in config") from None
    if _uses_anthropic_request_shape(model_config.use):
        patch_langchain_anthropic_streaming_dict_metadata()
    model_class = resolve_class(model_config.use, BaseChatModel)
    model_settings_from_config = model_config.model_dump(
        exclude_none=True,
        exclude={
            "use",
            "name",
            "display_name",
            "description",
            "supports_thinking",
            "supports_reasoning_effort",
            "reasoning_effort_levels",
            "default_reasoning_effort",
            "when_thinking_enabled",
            "when_thinking_disabled",
            "thinking",
            "supports_vision",
        },
    )
    # Compute effective when_thinking_enabled by merging in the `thinking` shortcut field.
    # The `thinking` shortcut is equivalent to setting when_thinking_enabled["thinking"].
    has_thinking_settings = (model_config.when_thinking_enabled is not None) or (model_config.thinking is not None)
    effective_wte: dict = dict(model_config.when_thinking_enabled) if model_config.when_thinking_enabled else {}
    if model_config.thinking is not None:
        merged_thinking = {**(effective_wte.get("thinking") or {}), **model_config.thinking}
        effective_wte = {**effective_wte, "thinking": merged_thinking}
    if thinking_enabled and has_thinking_settings:
        if not model_config.supports_thinking:
            raise ValueError(f"Model {name} does not support thinking. Set `supports_thinking` to true in the `config.yaml` to enable thinking.") from None
        if effective_wte:
            model_settings_from_config.update(effective_wte)
        if _is_deepseek_model(model_config.model):
            for param in ("temperature", "top_p", "presence_penalty", "frequency_penalty"):
                model_settings_from_config.pop(param, None)
                kwargs.pop(param, None)
    if not thinking_enabled:
        if model_config.when_thinking_disabled is not None:
            # User-provided disable settings take full precedence
            model_settings_from_config.update(model_config.when_thinking_disabled)
        elif has_thinking_settings and effective_wte.get("extra_body", {}).get("thinking", {}).get("type"):
            # OpenAI-compatible gateway: thinking is nested under extra_body
            model_settings_from_config["extra_body"] = _deep_merge_dicts(
                model_settings_from_config.get("extra_body"),
                {"thinking": {"type": "disabled"}},
            )
            model_settings_from_config["reasoning_effort"] = "minimal"
        elif has_thinking_settings and (disable_chat_template_kwargs := _vllm_disable_chat_template_kwargs(effective_wte.get("extra_body", {}).get("chat_template_kwargs") or {})):
            # vLLM uses chat template kwargs to switch thinking on/off.
            model_settings_from_config["extra_body"] = _deep_merge_dicts(
                model_settings_from_config.get("extra_body"),
                {"chat_template_kwargs": disable_chat_template_kwargs},
            )
        elif has_thinking_settings and effective_wte.get("thinking", {}).get("type"):
            # Native langchain_anthropic: thinking is a direct constructor parameter
            model_settings_from_config["thinking"] = {"type": "disabled"}
    effective_supports_reasoning_effort = model_config.effective_supports_reasoning_effort()
    if not effective_supports_reasoning_effort:
        kwargs.pop("reasoning_effort", None)
        model_settings_from_config.pop("reasoning_effort", None)

    if effective_supports_reasoning_effort and _uses_anthropic_request_shape(model_config.use):
        explicit_effort = kwargs.pop("reasoning_effort", None)
        configured_effort = model_settings_from_config.pop("effort", None)
        model_settings_from_config.pop("reasoning_effort", None)
        configured_output_config = model_settings_from_config.pop("output_config", None)
        if configured_output_config:
            model_settings_from_config["model_kwargs"] = _deep_merge_dicts(
                model_settings_from_config.get("model_kwargs"),
                {"output_config": configured_output_config},
            )
        selected_effort = (
            _anthropic_effort(explicit_effort)
            or _anthropic_effort(configured_effort)
            or _anthropic_effort(model_config.effective_default_reasoning_effort())
        )
        if selected_effort:
            model_settings_from_config["effort"] = selected_effort

    # For DeepSeek OpenAI-compatible models: map reasoning_effort to accepted values
    if (
        effective_supports_reasoning_effort
        and not _uses_anthropic_request_shape(model_config.use)
        and _is_deepseek_model(model_config.model)
    ):
        explicit_effort = kwargs.pop("reasoning_effort", None)
        if thinking_enabled:
            if explicit_effort:
                mapped = _deepseek_effort(explicit_effort)
                if mapped:
                    model_settings_from_config["reasoning_effort"] = mapped
                else:
                    model_settings_from_config.pop("reasoning_effort", None)
            elif "reasoning_effort" not in model_settings_from_config:
                model_settings_from_config["reasoning_effort"] = "high"
        else:
            model_settings_from_config.pop("reasoning_effort", None)

    _enable_stream_usage_by_default(model_config.use, model_settings_from_config)

    # For Codex Responses API models: map thinking mode to reasoning_effort
    from deerflow.models.openai_codex_provider import CodexChatModel

    if issubclass(model_class, CodexChatModel):
        # The ChatGPT Codex endpoint currently rejects max_tokens/max_output_tokens.
        model_settings_from_config.pop("max_tokens", None)

        # Use explicit reasoning_effort from frontend if provided (low/medium/high)
        explicit_effort = kwargs.pop("reasoning_effort", None)
        if not thinking_enabled:
            model_settings_from_config["reasoning_effort"] = "none"
        elif explicit_effort and explicit_effort in ("low", "medium", "high", "xhigh"):
            model_settings_from_config["reasoning_effort"] = explicit_effort
        elif "reasoning_effort" not in model_settings_from_config:
            model_settings_from_config["reasoning_effort"] = "medium"

    model_instance = model_class(**{**model_settings_from_config, **kwargs})

    callbacks = build_tracing_callbacks()
    if callbacks:
        existing_callbacks = model_instance.callbacks or []
        model_instance.callbacks = [*existing_callbacks, *callbacks]
        logger.debug(f"Tracing attached to model '{name}' with providers={len(callbacks)}")
    return model_instance
