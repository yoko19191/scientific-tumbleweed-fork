from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReasoningEffort = Literal["minimal", "low", "medium", "high", "max"]
CLAUDE_4_6_REASONING_EFFORT_LEVELS: list[ReasoningEffort] = ["low", "medium", "high", "max"]


def _model_name_starts_with(value: str, prefix: str) -> bool:
    normalized = value.lower()
    return normalized.startswith(prefix) or normalized.rsplit("/", 1)[-1].startswith(prefix)


class ModelConfig(BaseModel):
    """Config section for a model"""

    name: str = Field(..., description="Unique name for the model")
    display_name: str | None = Field(..., default_factory=lambda: None, description="Display name for the model")
    description: str | None = Field(..., default_factory=lambda: None, description="Description for the model")
    use: str = Field(
        ...,
        description="Class path of the model provider(e.g. langchain_openai.ChatOpenAI)",
    )
    model: str = Field(..., description="Model name")
    model_config = ConfigDict(extra="allow")
    use_responses_api: bool | None = Field(
        default=None,
        description="Whether to route OpenAI ChatOpenAI calls through the /v1/responses API",
    )
    output_version: str | None = Field(
        default=None,
        description="Structured output version for OpenAI responses content, e.g. responses/v1",
    )
    supports_thinking: bool = Field(default_factory=lambda: False, description="Whether the model supports thinking")
    supports_reasoning_effort: bool = Field(default_factory=lambda: False, description="Whether the model supports reasoning effort")
    default_reasoning_effort: ReasoningEffort | None = Field(
        default=None,
        description="Default reasoning effort for this model. If None, frontend chooses a mode-specific default.",
    )
    when_thinking_enabled: dict | None = Field(
        default_factory=lambda: None,
        description="Extra settings to be passed to the model when thinking is enabled",
    )
    when_thinking_disabled: dict | None = Field(
        default_factory=lambda: None,
        description="Extra settings to be passed to the model when thinking is disabled",
    )
    supports_vision: bool = Field(default_factory=lambda: False, description="Whether the model supports vision/image inputs")
    reasoning_effort_levels: list[str] | None = Field(
        default=None,
        description="Allowed reasoning effort levels for this model (e.g. ['high', 'max']). If None, frontend uses default levels.",
    )
    thinking: dict | None = Field(
        default_factory=lambda: None,
        description=(
            "Thinking settings for the model. If provided, these settings will be passed to the model when thinking is enabled. "
            "This is a shortcut for `when_thinking_enabled` and will be merged with `when_thinking_enabled` if both are provided."
        ),
    )

    def is_claude_opus_4_6_family(self) -> bool:
        """Return whether this config targets a Claude Opus 4.6 model family name."""
        return _model_name_starts_with(self.name, "claude-opus-4-6") or _model_name_starts_with(self.model, "claude-opus-4-6")

    def is_claude_sonnet_4_6_family(self) -> bool:
        """Return whether this config targets a Claude Sonnet 4.6 model family name."""
        return _model_name_starts_with(self.name, "claude-sonnet-4-6") or _model_name_starts_with(self.model, "claude-sonnet-4-6")

    def effective_supports_reasoning_effort(self) -> bool:
        """Return effective effort support, including known Claude 4.6 families."""
        return self.supports_reasoning_effort or self.is_claude_opus_4_6_family() or self.is_claude_sonnet_4_6_family()

    def effective_reasoning_effort_levels(self) -> list[str] | None:
        """Return configured or inferred effort levels for clients."""
        if self.reasoning_effort_levels:
            return self.reasoning_effort_levels
        if self.is_claude_opus_4_6_family() or self.is_claude_sonnet_4_6_family():
            return list(CLAUDE_4_6_REASONING_EFFORT_LEVELS)
        return None

    def effective_default_reasoning_effort(self) -> ReasoningEffort | None:
        """Return the configured default if valid, otherwise a Claude 4.6 default."""
        levels = self.effective_reasoning_effort_levels()
        if self.default_reasoning_effort and (levels is None or self.default_reasoning_effort in levels):
            return self.default_reasoning_effort
        if self.is_claude_sonnet_4_6_family():
            return "medium"
        if self.is_claude_opus_4_6_family():
            return "high"
        return None
