"""Tool search: deferred tool discovery at runtime.

Deferred MCP tools are named in the prompt but their full schemas are withheld
from model binding until the agent asks ``tool_search`` for them. The deferred
catalog is a build-time closure and promotion is stored in per-thread graph
state, so there is no request ContextVar to lose across turns or subagent
re-entry.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from functools import cached_property
from typing import Annotated

from langchain.tools import BaseTool
from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langchain_core.utils.function_calling import convert_to_openai_function
from langgraph.types import Command

from deerflow.tools.mcp_metadata import is_mcp_tool

logger = logging.getLogger(__name__)

MAX_RESULTS = 5


def _compile_catalog_regex(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return re.compile(re.escape(pattern), re.IGNORECASE)


@dataclass(frozen=True)
class DeferredToolCatalog:
    """Immutable searchable catalog of deferred tools."""

    tools: tuple[BaseTool, ...]

    @cached_property
    def names(self) -> frozenset[str]:
        return frozenset(tool.name for tool in self.tools)

    @cached_property
    def hash(self) -> str:
        canonical = [
            {"name": tool.name, "schema": convert_to_openai_function(tool)}
            for tool in sorted(self.tools, key=lambda t: t.name)
        ]
        blob = json.dumps(canonical, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def search(self, query: str) -> list[BaseTool]:
        query = query.strip()
        if not query:
            return []

        if query.startswith("select:"):
            wanted = {name.strip() for name in query[7:].split(",")}
            return [tool for tool in self.tools if tool.name in wanted][:MAX_RESULTS]

        if query.startswith("+"):
            parts = query[1:].split(None, 1)
            if not parts:
                return []
            required = parts[0].lower()
            candidates = [tool for tool in self.tools if required in tool.name.lower()]
            if len(parts) > 1:
                candidates.sort(key=lambda tool: _catalog_regex_score(parts[1], tool), reverse=True)
            return candidates[:MAX_RESULTS]

        regex = _compile_catalog_regex(query)
        scored: list[tuple[int, BaseTool]] = []
        for candidate in self.tools:
            searchable = f"{candidate.name} {candidate.description or ''}"
            if regex.search(searchable):
                scored.append((2 if regex.search(candidate.name) else 1, candidate))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [tool for _, tool in scored][:MAX_RESULTS]


def _catalog_regex_score(pattern: str, tool: BaseTool) -> int:
    regex = _compile_catalog_regex(pattern)
    return len(regex.findall(f"{tool.name} {tool.description or ''}"))


@dataclass(frozen=True)
class DeferredToolSetup:
    """Deferred-tool support for one agent build."""

    tool_search_tool: BaseTool | None
    deferred_names: frozenset[str]
    catalog_hash: str | None


def build_tool_search_tool(catalog: DeferredToolCatalog) -> BaseTool:
    catalog_hash = catalog.hash

    @tool
    def tool_search(query: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
        """Fetch full schema definitions for deferred tools so they can be called.

        Query forms:
        - ``select:Read,Edit`` fetches exact tool names
        - ``notebook jupyter`` keyword/regex searches names and descriptions
        - ``+slack send`` requires ``slack`` in the name and ranks by the rest
        """
        matched = catalog.search(query)[:MAX_RESULTS]
        if not matched:
            content = f"No tools found matching: {query}"
            names: list[str] = []
        else:
            content = json.dumps(
                [convert_to_openai_function(tool) for tool in matched],
                indent=2,
                ensure_ascii=False,
            )
            names = [tool.name for tool in matched]
        return Command(
            update={
                "promoted": {"catalog_hash": catalog_hash, "names": names},
                "messages": [
                    ToolMessage(
                        content=content,
                        tool_call_id=tool_call_id,
                        name="tool_search",
                    )
                ],
            }
        )

    return tool_search


def build_deferred_tool_setup(filtered_tools: list[BaseTool], *, enabled: bool) -> DeferredToolSetup:
    """Build deferred-tool setup from a policy-filtered tool list."""
    if not enabled:
        return DeferredToolSetup(None, frozenset(), None)
    deferred = [tool for tool in filtered_tools if is_mcp_tool(tool)]
    if not deferred:
        return DeferredToolSetup(None, frozenset(), None)
    catalog = DeferredToolCatalog(tuple(deferred))
    return DeferredToolSetup(build_tool_search_tool(catalog), catalog.names, catalog.hash)


def assemble_deferred_tools(filtered_tools: list[BaseTool], *, enabled: bool) -> tuple[list[BaseTool], DeferredToolSetup]:
    """Append tool_search after policy filtering and fail closed on wiring drift."""
    deferred_setup = build_deferred_tool_setup(filtered_tools, enabled=enabled)
    if enabled and not deferred_setup.deferred_names and any(is_mcp_tool(tool) for tool in filtered_tools):
        raise RuntimeError(
            "tool_search enabled and MCP tools survived policy filtering, but no deferred set was recovered "
            "- refusing to bind MCP schemas (fail-closed)."
        )
    final_tools = list(filtered_tools)
    if deferred_setup.tool_search_tool:
        final_tools.append(deferred_setup.tool_search_tool)
    return final_tools, deferred_setup


def get_deferred_tools_prompt_section(*, deferred_names: frozenset[str] = frozenset()) -> str:
    """Render names only; schemas remain hidden until ``tool_search`` promotes them."""
    if not deferred_names:
        return ""
    names = "\n".join(sorted(deferred_names))
    return f"<available-deferred-tools>\n{names}\n</available-deferred-tools>"
