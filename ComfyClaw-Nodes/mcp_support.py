"""Helpers for basic MCP streamable HTTP interactions."""

from __future__ import annotations

from .common import DEFAULT_MCP_PROTOCOL_VERSION, http_post_json
from .providers import MCPProvider


def initialize_mcp_session(provider: MCPProvider, timeout: float) -> tuple[dict, dict[str, str], str]:
    headers = {"MCP-Protocol-Version": DEFAULT_MCP_PROTOCOL_VERSION}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"

    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": DEFAULT_MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "ComfyClaw", "version": "0.1.0"},
        },
    }
    response, response_headers = http_post_json(provider.server_url, init_payload, headers=headers, timeout=timeout)
    if not isinstance(response, dict) or "result" not in response:
        raise RuntimeError("MCP initialize did not return a valid JSON-RPC result.")

    result = response["result"]
    negotiated_version = DEFAULT_MCP_PROTOCOL_VERSION
    if isinstance(result, dict) and isinstance(result.get("protocolVersion"), str):
        negotiated_version = result["protocolVersion"]

    session_headers = dict(headers)
    session_headers["MCP-Protocol-Version"] = negotiated_version
    session_id = response_headers.get("Mcp-Session-Id") or response_headers.get("MCP-Session-Id")
    if session_id:
        session_headers["MCP-Session-Id"] = session_id

    initialized_payload = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    http_post_json(provider.server_url, initialized_payload, headers=session_headers, timeout=timeout)
    return result if isinstance(result, dict) else {}, session_headers, negotiated_version


def mcp_request(provider: MCPProvider, method: str, params: dict, timeout: float) -> dict:
    _, headers, _ = initialize_mcp_session(provider, timeout)
    payload = {"jsonrpc": "2.0", "id": 2, "method": method, "params": params}
    response, _ = http_post_json(provider.server_url, payload, headers=headers, timeout=timeout)
    if not isinstance(response, dict):
        raise RuntimeError("MCP request did not return a JSON-RPC object.")
    if "error" in response:
        error = response["error"]
        if isinstance(error, dict):
            message = error.get("message") or error.get("data") or "Unknown MCP error."
            raise RuntimeError(str(message))
        raise RuntimeError(str(error))
    if "result" not in response:
        raise RuntimeError("MCP response did not include a result.")
    result = response["result"]
    return result if isinstance(result, dict) else {"value": result}
