"""MCP_List_Tools node."""

from __future__ import annotations

from .common import custom_input, int_input, serialize_json
from .mcp_support import mcp_request
from .providers import MCPProvider


class MCPListTools:
    """Fetch the available MCP tool descriptions."""

    CATEGORY = "ComfyClaw/MCP"
    FUNCTION = "list_tools"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("tools_json_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mcp_provider": custom_input("MCP_PROVIDER"),
                "timeout": int_input(30, min=1),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def list_tools(self, mcp_provider, timeout=30):
        if not isinstance(mcp_provider, MCPProvider):
            return ("", "mcp_provider is missing or invalid.")
        if not isinstance(timeout, int) or timeout <= 0:
            return ("", "timeout must be a positive integer.")

        try:
            result = mcp_request(mcp_provider, "tools/list", {}, float(timeout))
        except Exception as exc:
            return ("", f"Could not list MCP tools: {exc}")

        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            return ("", "MCP tools/list did not return a tools array.")
        return (serialize_json(tools), "")
