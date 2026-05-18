"""MCP_Call node."""

from __future__ import annotations

import json

from .common import custom_input, int_input, serialize_tool_result, string_input
from .mcp_support import mcp_request
from .providers import MCPProvider


class MCPCall:
    """Execute a single MCP tool call."""

    CATEGORY = "ComfyClaw/MCP"
    FUNCTION = "call_tool"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("tool_result_text", "error_string")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mcp_provider": custom_input("MCP_PROVIDER"),
                "tool_call_json": string_input(""),
                "timeout": int_input(30, min=1),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def call_tool(self, mcp_provider, tool_call_json, timeout=30):
        if not isinstance(mcp_provider, MCPProvider):
            return ("", "mcp_provider is missing or invalid.")
        if not isinstance(tool_call_json, str) or not tool_call_json.strip():
            return ("", "tool_call_json cannot be empty.")
        if not isinstance(timeout, int) or timeout <= 0:
            return ("", "timeout must be a positive integer.")

        try:
            tool_call = json.loads(tool_call_json)
        except Exception as exc:
            return ("", f"tool_call_json is not valid JSON: {exc}")
        if not isinstance(tool_call, dict):
            return ("", "tool_call_json must decode to an object.")

        tool_name = tool_call.get("tool")
        arguments = tool_call.get("arguments", {})
        if not isinstance(tool_name, str) or not tool_name.strip():
            return ("", "tool_call_json must contain a non-empty tool field.")
        if not isinstance(arguments, dict):
            return ("", "tool_call_json arguments must be a JSON object.")

        try:
            result = mcp_request(
                mcp_provider,
                "tools/call",
                {"name": tool_name.strip(), "arguments": arguments},
                float(timeout),
            )
        except Exception as exc:
            return ("", f"MCP tool call failed: {exc}")

        if isinstance(result, dict) and result.get("isError"):
            return ("", serialize_tool_result(result))
        return (serialize_tool_result(result), "")
