"""Configuration for tool output budget protection."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ToolOutputConfig(BaseModel):
    """Config section for oversized tool-result protection."""

    enabled: bool = Field(default=True, description="Enable the tool output budget middleware.")
    externalize_min_chars: int = Field(
        default=12_000,
        ge=0,
        description="Character threshold that triggers externalization. Set to 0 to disable externalization.",
    )
    preview_head_chars: int = Field(default=2_000, ge=0, description="Head characters to keep in the preview.")
    preview_tail_chars: int = Field(default=1_000, ge=0, description="Tail characters to keep in the preview.")
    fallback_max_chars: int = Field(default=30_000, ge=0, description="Maximum characters when persistence is unavailable. 0 disables fallback truncation.")
    fallback_head_chars: int = Field(default=8_000, ge=0, description="Head characters for fallback truncation.")
    fallback_tail_chars: int = Field(default=3_000, ge=0, description="Tail characters for fallback truncation.")
    storage_subdir: str = Field(default=".tool-results", description="Subdirectory under the thread outputs path for persisted tool results.")
    exempt_tools: list[str] = Field(
        default_factory=lambda: ["read_file", "read_file_tool"],
        description="Tool names exempt from budget enforcement to avoid persist/read/persist loops.",
    )
    tool_overrides: dict[str, int] = Field(
        default_factory=dict,
        description="Per-tool externalize_min_chars overrides. Keys are tool names; values are char thresholds.",
    )
