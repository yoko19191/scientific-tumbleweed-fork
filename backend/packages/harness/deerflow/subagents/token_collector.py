"""Callback handler for collecting subagent LLM token usage."""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import BaseCallbackHandler


class SubagentTokenCollector(BaseCallbackHandler):
    """Collect usage_metadata from LLM calls made inside one subagent run."""

    def __init__(self, caller: str) -> None:
        super().__init__()
        self.caller = caller
        self._records: list[dict[str, int | str]] = []
        self._counted_run_ids: set[str] = set()

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: Any,
        **kwargs: Any,
    ) -> None:
        rid = str(run_id)
        if rid in self._counted_run_ids:
            return

        for generation in getattr(response, "generations", []) or []:
            for gen in generation:
                message = getattr(gen, "message", None)
                usage = getattr(message, "usage_metadata", None) if message is not None else None
                usage_dict = dict(usage) if usage else {}
                input_tokens = usage_dict.get("input_tokens", 0) or 0
                output_tokens = usage_dict.get("output_tokens", 0) or 0
                total_tokens = usage_dict.get("total_tokens", 0) or 0
                if total_tokens <= 0:
                    total_tokens = input_tokens + output_tokens
                if total_tokens <= 0:
                    continue

                self._counted_run_ids.add(rid)
                self._records.append(
                    {
                        "source_run_id": rid,
                        "caller": self.caller,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                    }
                )
                return

    def snapshot_records(self) -> list[dict[str, int | str]]:
        """Return collected records without exposing internal mutable state."""
        return list(self._records)
