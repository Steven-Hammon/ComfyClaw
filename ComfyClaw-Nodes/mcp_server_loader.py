"""MCP_Server_Loader node."""

from __future__ import annotations

from .common import is_valid_url, normalize_base_url, string_input
from .providers import MCPProvider


class MCPServerLoader:
    """Configure an MCP server provider."""

    CATEGORY = "ComfyClaw/MCP"
    FUNCTION = "load_server"
    RETURN_TYPES = ("MCP_PROVIDER", "STRING")
    RETURN_NAMES = ("mcp_provider", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mcp_server_url": string_input("http://127.0.0.1:8080", multiline=False),
                "api_key": string_input("", multiline=False),
            }
        }

    def load_server(self, mcp_server_url, api_key=""):
        if not isinstance(mcp_server_url, str) or not isinstance(api_key, str):
            return (None, "mcp_server_url and api_key must be strings.")
        if not mcp_server_url.strip():
            return (None, "mcp_server_url cannot be empty.")
        if not is_valid_url(mcp_server_url.strip()):
            return (None, "mcp_server_url must be a valid http or https URL.")
        provider = MCPProvider(server_url=normalize_base_url(mcp_server_url.strip()), api_key=api_key.strip())
        return (provider, "")
