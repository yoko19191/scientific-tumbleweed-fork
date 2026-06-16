"""Single source of truth for the MCP-tool metadata tag."""

from __future__ import annotations

from langchain.tools import BaseTool

MCP_TOOL_METADATA_KEY = "deerflow_mcp"


def tag_mcp_tool(tool: BaseTool) -> BaseTool:
    """Mark ``tool`` as MCP-sourced. Mutates in place and returns the tool."""
    tool.metadata = {**(tool.metadata or {}), MCP_TOOL_METADATA_KEY: True}
    return tool


def is_mcp_tool(tool: BaseTool) -> bool:
    """Return whether ``tool`` carries the MCP-source tag."""
    return (getattr(tool, "metadata", None) or {}).get(MCP_TOOL_METADATA_KEY) is True
