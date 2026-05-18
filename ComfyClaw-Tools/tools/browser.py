from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / "settings.json"
SERVER_FILE = ROOT / "browser_server.py"
TRUNCATED_SUFFIX = "\n...[truncated]"
SERVER_START_TIMEOUT_SECONDS = 5
SERVER_RETRY_SECONDS = 0.5


ACTION_ARGUMENTS = {
    "goto": {"url"},
    "click": {"selector"},
    "type": {"selector", "text"},
    "press": {"selector", "key"},
    "state": set(),
    "screenshot": {"out"},
    "end": set(),
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

        parsed_args[key[2:]] = raw_args[index + 1]
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


def load_settings() -> dict[str, object]:
    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

    for key in {"TruncatedCharacters", "BrowserPort", "BrowserTimeoutMs"}:
        if key not in data:
            raise ValueError(f"settings.json missing required key: {key}")
        if not isinstance(data[key], int):
            raise ValueError(f"settings.json {key} must be an integer")

    if data["TruncatedCharacters"] < 0:
        raise ValueError("settings.json TruncatedCharacters must be 0 or greater")
    if data["BrowserPort"] <= 0:
        raise ValueError("settings.json BrowserPort must be greater than 0")
    if data["BrowserTimeoutMs"] <= 0:
        raise ValueError("settings.json BrowserTimeoutMs must be greater than 0")

    return data


def truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit == 0:
        return TRUNCATED_SUFFIX.lstrip()
    return text[:limit] + TRUNCATED_SUFFIX


def post_command(settings: dict[str, object], action: str, command_args: dict[str, str]) -> dict[str, object]:
    port = int(settings["BrowserPort"])
    timeout_seconds = (int(settings["BrowserTimeoutMs"]) * 2) / 1000
    body = json.dumps({"action": action, "args": command_args}).encode("utf-8")
    request = urllib.request.Request(
        f"http://localhost:{port}/command",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def start_browser_server() -> None:
    if sys.platform.startswith("win"):
        subprocess.Popen(
            [sys.executable, str(SERVER_FILE)],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
            cwd=str(ROOT),
        )
        return

    subprocess.Popen(
        [sys.executable, str(SERVER_FILE)],
        start_new_session=True,
        close_fds=True,
        cwd=str(ROOT),
    )


def post_command_with_autostart(settings: dict[str, object], action: str, command_args: dict[str, str]) -> dict[str, object]:
    try:
        return post_command(settings, action, command_args)
    except urllib.error.URLError as original_error:
        start_browser_server()
        deadline = time.monotonic() + SERVER_START_TIMEOUT_SECONDS
        last_error = original_error

        while time.monotonic() < deadline:
            time.sleep(SERVER_RETRY_SECONDS)
            try:
                return post_command(settings, action, command_args)
            except urllib.error.URLError as exc:
                last_error = exc

        raise last_error


def quote_text(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace('"', '\\"')


def format_page_state(data: dict[str, object]) -> str:
    elements = data.get("interactive_elements", [])
    lines = [
        "=== PAGE STATE ===",
        f"URL: {data.get('url', '')}",
        f"Title: {data.get('title', '')}",
        "",
        "--- VISIBLE TEXT ---",
        str(data.get("visible_text", "")),
        "",
        "--- INTERACTIVE ELEMENTS ---",
    ]

    if isinstance(elements, list):
        for index, item in enumerate(elements):
            if not isinstance(item, dict):
                continue

            element_id = item.get("id", index)
            tag = item.get("tag", "")
            text = quote_text(item.get("text", ""))
            selector = item.get("selector", "")
            element_type = item.get("type")
            line = f'[{element_id}] {tag} | "{text}" | {selector}'
            if element_type:
                line += f" | type={element_type}"
            lines.append(line)

    lines.append("==================")
    return "\n".join(lines)


def format_response(data: dict[str, object]) -> str:
    if data.get("status") == "error":
        lines = [f"Error: {data.get('error', 'unknown error')}"]
        if {"url", "title", "visible_text", "interactive_elements"}.issubset(data):
            lines.extend(["", format_page_state(data)])
        elif "state_error" in data:
            lines.append(f"State Error: {data['state_error']}")
        return "\n".join(lines)

    if "saved_to" in data:
        return f"Saved to {data['saved_to']}"

    if "message" in data:
        return str(data["message"])

    return format_page_state(data)


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    action_rules: dict[str, tuple[set[str], set[str]]] = {
        "goto": ({"url"}, {"url"}),
        "click": ({"selector"}, {"selector"}),
        "type": ({"selector", "text"}, {"selector", "text"}),
        "press": ({"selector", "key"}, {"selector", "key"}),
        "state": (set(), set()),
        "screenshot": ({"out"}, set()),
        "end": (set(), set()),
    }

    if action not in action_rules:
        return f"Error: unknown action {action}"

    allowed, required = action_rules[action]
    error = validate_args(parsed_args, allowed, required)
    if error:
        return error

    try:
        settings = load_settings()
        command_args = dict(parsed_args)
        if action == "screenshot" and "out" not in command_args:
            command_args["out"] = "screenshot.png"

        response = post_command_with_autostart(settings, action, command_args)
        formatted = format_response(response)
        return truncate_text(formatted, int(settings["TruncatedCharacters"]))
    except TimeoutError:
        return "Error: browser server timed out"
    except urllib.error.URLError:
        return "Error: browser server is not running and could not be started automatically"
    except Exception as exc:
        return f"Error: {exc}"
