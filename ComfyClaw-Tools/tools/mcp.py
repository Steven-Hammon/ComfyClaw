from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from typing import Any

from tool_settings import truncate_text


PROTOCOL_VERSION = "2025-06-18"

ACTION_ARGUMENTS = {
    "list": {"server", "token", "timeout", "protocol_version"},
    "call": {"server", "tool", "name", "arguments", "token", "timeout", "protocol_version"},
}


def parse_command(args: list[str]):
    if not args:
        return None, None, "Error: missing action"

    action = args[0]
    parsed_args: dict[str, str] = {}
    raw_args = args[1:]
    index = 0

    while index < len(raw_args):
        key = raw_args[index]
        if not key.startswith("--"):
            return None, None, f"Error: invalid argument {key}"
        if index + 1 >= len(raw_args):
            return None, None, f"Error: missing value for {key}"

        clean_key = key[2:].lower().replace("-", "_")
        parsed_args[clean_key] = raw_args[index + 1]
        index += 2

    return action, parsed_args, None


def validate_args(parsed_args: dict[str, str], allowed: set[str], required: set[str]):
    for key in parsed_args:
        if key not in allowed:
            return f"Error: unknown argument --{key}"

    for key in required:
        if key not in parsed_args:
            return f"Error: missing required argument --{key}"

    return None


def get_timeout(parsed_args: dict[str, str]) -> int:
    if "timeout" not in parsed_args:
        return 30

    try:
        timeout = int(parsed_args["timeout"])
    except ValueError as exc:
        raise ValueError("timeout must be an integer") from exc

    if timeout < 1:
        raise ValueError("timeout must be 1 or greater")

    return timeout


def decode_json_text(value: str) -> Any:
    text = value.strip()
    attempts = [text]

    if '\\"' in text:
        attempts.append(text.replace('\\"', '"'))

    try:
        attempts.append(bytes(text, "utf-8").decode("unicode_escape"))
    except Exception:
        pass

    last_error: Exception | None = None
    for attempt in attempts:
        try:
            loaded = json.loads(attempt)
            if isinstance(loaded, str):
                loaded = json.loads(loaded)
            return loaded
        except Exception as exc:
            last_error = exc

    raise ValueError(f"invalid JSON: {last_error}")


def parse_tool_call(parsed_args: dict[str, str]) -> tuple[str, dict[str, Any]]:
    if "tool" in parsed_args:
        tool_call = decode_json_text(parsed_args["tool"])
        if not isinstance(tool_call, dict):
            raise ValueError("tool must be a JSON object")

        name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        if not isinstance(name, str) or not name:
            raise ValueError("tool JSON must include a non-empty name")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise ValueError("tool JSON arguments must be an object")
        return name, arguments

    if "name" not in parsed_args:
        raise ValueError("missing required argument --tool or --name")

    name = parsed_args["name"].strip()
    if not name:
        raise ValueError("name must not be empty")

    if "arguments" not in parsed_args or not parsed_args["arguments"].strip():
        return name, {}

    arguments = decode_json_text(parsed_args["arguments"])
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be a JSON object")

    return name, arguments


def parse_sse_or_json(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return {}

    if text.startswith("data:") or "\ndata:" in text:
        payloads: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    payloads.append(data)

        if not payloads:
            return {}
        return json.loads(payloads[-1])

    return json.loads(text)


def post_json(
    server: str,
    payload: dict[str, Any],
    timeout: int,
    token: str | None,
    protocol_version: str,
    session_id: str | None = None,
    mcp_name: str | None = None,
) -> tuple[Any, str | None, str]:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": protocol_version,
        "Mcp-Method": payload.get("method", ""),
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    if mcp_name:
        headers["Mcp-Name"] = mcp_name

    request = urllib.request.Request(server, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_body = response.read()
        response_session = response.headers.get("Mcp-Session-Id") or session_id
        response_protocol = response.headers.get("MCP-Protocol-Version") or protocol_version
        return parse_sse_or_json(response_body), response_session, response_protocol


def request_or_error(
    server: str,
    payload: dict[str, Any],
    timeout: int,
    token: str | None,
    protocol_version: str,
    session_id: str | None = None,
    mcp_name: str | None = None,
) -> tuple[Any, str | None, str]:
    response, session_id, protocol_version = post_json(
        server,
        payload,
        timeout,
        token,
        protocol_version,
        session_id=session_id,
        mcp_name=mcp_name,
    )

    if isinstance(response, dict) and "error" in response:
        error = response["error"]
        if isinstance(error, dict):
            message = error.get("message") or json.dumps(error, ensure_ascii=False)
        else:
            message = str(error)
        raise RuntimeError(message)

    return response, session_id, protocol_version


def initialize(server: str, timeout: int, token: str | None, protocol_version: str) -> tuple[str | None, str]:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": protocol_version,
            "capabilities": {},
            "clientInfo": {"name": "Tools1", "version": "1.0.0"},
        },
    }
    response, session_id, negotiated_version = request_or_error(server, payload, timeout, token, protocol_version)

    if isinstance(response, dict):
        result = response.get("result")
        if isinstance(result, dict) and isinstance(result.get("protocolVersion"), str):
            negotiated_version = result["protocolVersion"]

    notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    try:
        post_json(
            server,
            notification,
            timeout,
            token,
            negotiated_version,
            session_id=session_id,
        )
    except urllib.error.HTTPError as exc:
        if exc.code not in {202, 204}:
            raise

    return session_id, negotiated_version


def list_tools(server: str, timeout: int, token: str | None, protocol_version: str) -> dict[str, Any]:
    session_id, protocol_version = initialize(server, timeout, token, protocol_version)
    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    response, _, _ = request_or_error(
        server,
        payload,
        timeout,
        token,
        protocol_version,
        session_id=session_id,
    )
    return response


def call_tool(
    server: str,
    name: str,
    arguments: dict[str, Any],
    timeout: int,
    token: str | None,
    protocol_version: str,
) -> dict[str, Any]:
    session_id, protocol_version = initialize(server, timeout, token, protocol_version)
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    response, _, _ = request_or_error(
        server,
        payload,
        timeout,
        token,
        protocol_version,
        session_id=session_id,
        mcp_name=name,
    )
    return response


def format_tool_list(response: dict[str, Any]) -> str:
    result = response.get("result", response)
    tools = result.get("tools", []) if isinstance(result, dict) else []
    if not tools:
        return json.dumps(response, indent=2, ensure_ascii=False)

    lines = ["MCP TOOLS"]
    for tool in tools:
        if not isinstance(tool, dict):
            continue

        name = str(tool.get("name", "")).strip()
        title = str(tool.get("title", "")).strip()
        description = str(tool.get("description", "")).strip()
        schema = tool.get("inputSchema")

        header = name if not title else f"{name} - {title}"
        lines.append("")
        lines.append(header)
        if description:
            lines.append(description)
        if schema:
            lines.append("INPUT SCHEMA:")
            lines.append(json.dumps(schema, indent=2, ensure_ascii=False))

    return "\n".join(lines).strip()


def format_tool_result(response: dict[str, Any]) -> str:
    result = response.get("result", response)
    if not isinstance(result, dict):
        return json.dumps(response, indent=2, ensure_ascii=False)

    parts: list[str] = []
    content = result.get("content", [])
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                parts.append(str(item))
                continue

            if item.get("type") == "text" and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(json.dumps(item, indent=2, ensure_ascii=False))

    if "structuredContent" in result:
        parts.append("STRUCTURED CONTENT:")
        parts.append(json.dumps(result["structuredContent"], indent=2, ensure_ascii=False))

    if parts:
        return "\n\n".join(parts).strip()

    return json.dumps(result, indent=2, ensure_ascii=False)


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    try:
        if action == "list":
            error = validate_args(parsed_args, ACTION_ARGUMENTS["list"], {"server"})
            if error:
                return error

            response = list_tools(
                parsed_args["server"],
                get_timeout(parsed_args),
                parsed_args.get("token"),
                parsed_args.get("protocol_version", PROTOCOL_VERSION),
            )
            return truncate_text(format_tool_list(response))

        if action == "call":
            error = validate_args(parsed_args, ACTION_ARGUMENTS["call"], {"server"})
            if error:
                return error

            name, arguments = parse_tool_call(parsed_args)
            response = call_tool(
                parsed_args["server"],
                name,
                arguments,
                get_timeout(parsed_args),
                parsed_args.get("token"),
                parsed_args.get("protocol_version", PROTOCOL_VERSION),
            )
            return truncate_text(format_tool_result(response))

        return f"Error: unknown action {action}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        if detail:
            return f"Error: HTTP {exc.code}: {detail}"
        return f"Error: HTTP {exc.code}"
    except Exception as exc:
        return f"Error: {exc}"


if __name__ == "__main__":
    print(run(sys.argv[1:]))
