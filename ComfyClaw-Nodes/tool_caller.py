"""Tool_Caller node."""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from .common import bool_input, int_input, require_string, string_input


_TOOL_SESSIONS: dict[str, "_ToolSession"] = {}
_TOOL_SESSIONS_LOCK = threading.Lock()
_ARG_PATTERN = re.compile(r"(^|\s)--(?P<name>[A-Za-z0-9_][A-Za-z0-9_-]*)")
_OUTPUT_IDLE_SECONDS = 0.25


@dataclass
class _ToolSession:
    process: subprocess.Popen[str]
    stdout_queue: Queue[str | None]
    stderr_queue: Queue[str | None]
    lock: threading.Lock = field(default_factory=threading.Lock)


def _reader_worker(stream, output_queue: Queue[str | None]):
    try:
        while True:
            chunk = stream.read(1)
            if chunk == "":
                break
            output_queue.put(chunk)
    finally:
        output_queue.put(None)


def _get_session_owner(unique_id) -> str:
    if unique_id is None:
        return "default"
    return str(unique_id)


def _session_key(owner: str, python_path: Path, tool_path: Path) -> str:
    return f"{owner}|{python_path}|{tool_path}"


def _close_session_by_key(session_key: str):
    with _TOOL_SESSIONS_LOCK:
        session = _TOOL_SESSIONS.pop(session_key, None)
    if session is None:
        return

    if session.process.poll() is None:
        try:
            session.process.terminate()
            session.process.wait(timeout=2)
        except Exception:
            try:
                session.process.kill()
            except Exception:
                pass

    for stream in (session.process.stdin, session.process.stdout, session.process.stderr):
        try:
            if stream:
                stream.close()
        except Exception:
            pass


def _close_stale_sessions(owner: str, active_key: str):
    stale_keys = []
    with _TOOL_SESSIONS_LOCK:
        for session_key in _TOOL_SESSIONS:
            if session_key.startswith(f"{owner}|") and session_key != active_key:
                stale_keys.append(session_key)
    for session_key in stale_keys:
        _close_session_by_key(session_key)


def _close_all_sessions():
    for session_key in list(_TOOL_SESSIONS):
        _close_session_by_key(session_key)


def _resolve_existing_path(path_text: str, field_name: str) -> tuple[Path | None, str]:
    path = Path(path_text).expanduser()
    if not path.exists():
        return None, f"{field_name} not found: {path}"
    return path.resolve(), ""


def _resolve_venv_python(venv_path_text: str) -> tuple[Path | None, str]:
    path, error = _resolve_existing_path(venv_path_text, "venv_path")
    if error or path is None:
        return None, error

    if path.is_file():
        return path, ""

    candidates = []
    if os.name == "nt":
        candidates.extend((path / "Scripts" / "python.exe", path / "Scripts" / "python"))
    candidates.extend((path / "bin" / "python", path / "bin" / "python3"))

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve(), ""
    return None, f"Python executable not found in venv_path: {path}"


def _strip_one_leading_separator(value: str) -> str:
    return value.lstrip(" \t")


def _parse_args(args_text: str) -> dict[str, str]:
    matches = list(_ARG_PATTERN.finditer(args_text))
    args: dict[str, str] = {}
    for index, match in enumerate(matches):
        value_start = match.end()
        value_end = matches[index + 1].start() if index + 1 < len(matches) else len(args_text)
        value = _strip_one_leading_separator(args_text[value_start:value_end])
        args[match.group("name")] = value
    return args


def _parse_tool_call(tool_call: str) -> dict[str, Any]:
    text = tool_call.lstrip()
    if ":" in text:
        tool_text, args_text = text.split(":", 1)
        tool = tool_text.strip().split(None, 1)[0] if tool_text.strip() else ""
    else:
        parts = text.split(None, 1)
        tool = parts[0] if parts else ""
        args_text = parts[1] if len(parts) > 1 else ""

    if not tool:
        raise ValueError("tool_call requires a tool name.")
    return {"tool": tool, "args": _parse_args(args_text)}


def _make_payload_line(tool_call: str, convert_to_json: bool) -> str:
    if not convert_to_json:
        return tool_call
    payload = _parse_tool_call(tool_call)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _drain_stderr(session: _ToolSession) -> str:
    lines: list[str] = []
    while True:
        try:
            item = session.stderr_queue.get_nowait()
        except Empty:
            break
        if item is None:
            continue
        lines.append(item)
    return "".join(lines).strip()


def _get_or_create_session(owner: str, python_path: Path, tool_path: Path) -> tuple[_ToolSession | None, str, str]:
    session_key = _session_key(owner, python_path, tool_path)
    with _TOOL_SESSIONS_LOCK:
        session = _TOOL_SESSIONS.get(session_key)
        if session is not None and session.process.poll() is None:
            return session, session_key, ""

        if session is not None:
            _TOOL_SESSIONS.pop(session_key, None)

    _close_stale_sessions(owner, session_key)

    try:
        process = subprocess.Popen(
            [str(python_path), str(tool_path), "--interactive"],
            cwd=str(tool_path.parent),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as exc:
        return None, session_key, f"Could not start tool process: {exc}"

    if process.stdin is None or process.stdout is None or process.stderr is None:
        try:
            process.kill()
        except Exception:
            pass
        return None, session_key, "Could not open tool process pipes."

    stdout_queue: Queue[str | None] = Queue()
    stderr_queue: Queue[str | None] = Queue()
    threading.Thread(
        target=_reader_worker,
        args=(process.stdout, stdout_queue),
        name=f"ComfyClawToolCallerStdout-{owner}",
        daemon=True,
    ).start()
    threading.Thread(
        target=_reader_worker,
        args=(process.stderr, stderr_queue),
        name=f"ComfyClawToolCallerStderr-{owner}",
        daemon=True,
    ).start()

    session = _ToolSession(process=process, stdout_queue=stdout_queue, stderr_queue=stderr_queue)
    with _TOOL_SESSIONS_LOCK:
        _TOOL_SESSIONS[session_key] = session
    return session, session_key, ""


def _extract_tool_output(line: str) -> str:
    cleaned_line = line.rstrip("\r\n")
    try:
        response = json.loads(cleaned_line)
    except json.JSONDecodeError:
        return cleaned_line
    if isinstance(response, dict) and "result" in response:
        result = response.get("result")
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)
    if isinstance(response, str):
        return response
    return json.dumps(response, ensure_ascii=False)


def _read_tool_response(session: _ToolSession, timeout: int) -> str:
    chunks: list[str] = []
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError

        wait_time = min(remaining, _OUTPUT_IDLE_SECONDS) if chunks else remaining
        try:
            chunk = session.stdout_queue.get(timeout=wait_time)
        except Empty:
            if chunks:
                return "".join(chunks)
            raise TimeoutError

        if chunk is None:
            if chunks:
                return "".join(chunks)
            stderr_text = _drain_stderr(session)
            if stderr_text:
                raise RuntimeError(f"Tool process ended unexpectedly: {stderr_text}")
            raise RuntimeError("Tool process ended unexpectedly.")

        chunks.append(chunk)


class ToolCaller:
    """Call an interactive run_tool.py subprocess over newline-delimited JSON."""

    CATEGORY = "ComfyClaw/System"
    FUNCTION = "call_tool"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("tool_output", "error_string")
    OUTPUT_NODE = True
    SEARCH_ALIASES = ["tool caller", "run tool", "interactive tool"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "tool_path": string_input("", multiline=False),
                "venv_path": string_input("", multiline=False),
                "tool_call": string_input(""),
                "convert_to_json": bool_input(True),
                "timeout": int_input(30, min=1),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def call_tool(self, tool_path, venv_path, tool_call, convert_to_json=True, timeout=30, unique_id=None):
        checked_tool_path, tool_path_error = require_string(tool_path, "tool_path")
        checked_venv_path, venv_path_error = require_string(venv_path, "venv_path")
        checked_tool_call, tool_call_error = require_string(tool_call, "tool_call")
        if tool_path_error or venv_path_error or tool_call_error:
            return ("", "; ".join(error for error in (tool_path_error, venv_path_error, tool_call_error) if error))
        if not checked_tool_path.strip():
            return ("", "tool_path cannot be empty.")
        if not checked_venv_path.strip():
            return ("", "venv_path cannot be empty.")
        if not checked_tool_call.strip():
            return ("", "tool_call requires an input.")
        if not isinstance(convert_to_json, bool):
            return ("", "convert_to_json must be a boolean.")
        if not isinstance(timeout, int) or timeout <= 0:
            return ("", "timeout must be a positive integer.")

        resolved_tool_path, tool_path_error = _resolve_existing_path(checked_tool_path.strip(), "tool_path")
        if tool_path_error or resolved_tool_path is None:
            return ("", tool_path_error)
        if not resolved_tool_path.is_file():
            return ("", f"tool_path is not a file: {resolved_tool_path}")

        python_path, venv_error = _resolve_venv_python(checked_venv_path.strip())
        if venv_error or python_path is None:
            return ("", venv_error)

        try:
            payload_line = _make_payload_line(checked_tool_call, convert_to_json)
        except Exception as exc:
            return ("", f"Could not parse tool_call: {exc}")

        owner = _get_session_owner(unique_id)
        session, session_key, session_error = _get_or_create_session(owner, python_path, resolved_tool_path)
        if session_error or session is None:
            return ("", session_error)

        with session.lock:
            try:
                _drain_stderr(session)
                if session.process.stdin is None or session.process.poll() is not None:
                    raise RuntimeError("Tool process is unavailable.")

                session.process.stdin.write(payload_line)
                if not payload_line.endswith("\n"):
                    session.process.stdin.write("\n")
                session.process.stdin.flush()
                response_text = _read_tool_response(session, timeout)
                return (_extract_tool_output(response_text), "")
            except TimeoutError:
                _close_session_by_key(session_key)
                return ("", f"tool timed out after {timeout} seconds.")
            except Exception as exc:
                _close_session_by_key(session_key)
                return ("", f"Could not call tool: {exc}")
