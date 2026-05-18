"""Exec node."""

from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import Empty, Queue

from .common import combo_input, int_input, string_input

_OUTPUT_MODES = ["Current Command", "Entire Terminal"]
_SHELL_SESSIONS: dict[str, "_ShellSession"] = {}
_SHELL_SESSIONS_LOCK = threading.Lock()
_WINDOWS_PROMPT_PREFIX = "__COMFYCLAW_PROMPT__"


@dataclass
class _ShellSession:
    process: subprocess.Popen[str]
    output_queue: Queue[str | None]
    history_blocks: list[str] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    current_prompt: str = ""


def _reader_worker(stream, output_queue: Queue[str | None]):
    try:
        while True:
            line = stream.readline()
            if line == "":
                break
            output_queue.put(line)
    finally:
        output_queue.put(None)


def _get_session_key(unique_id) -> str:
    if unique_id is None:
        return "default"
    return str(unique_id)


def _build_shell_command() -> list[str]:
    if os.name == "nt":
        return [os.environ.get("COMSPEC") or "cmd.exe", "/D", "/Q", "/K", "prompt __COMFYCLAW_PROMPT__$P$G"]
    return [os.environ.get("SHELL") or "/bin/sh"]


def _close_session_by_key(session_key: str):
    with _SHELL_SESSIONS_LOCK:
        session = _SHELL_SESSIONS.pop(session_key, None)
    if session is None:
        return

    try:
        if session.process.stdin and session.process.poll() is None:
            session.process.stdin.write("exit\n")
            session.process.stdin.flush()
    except Exception:
        pass

    if session.process.poll() is None:
        try:
            session.process.terminate()
            session.process.wait(timeout=2)
        except Exception:
            try:
                session.process.kill()
            except Exception:
                pass

    for stream in (session.process.stdin, session.process.stdout):
        try:
            if stream:
                stream.close()
        except Exception:
            pass


def _get_or_create_session(unique_id) -> _ShellSession:
    session_key = _get_session_key(unique_id)
    with _SHELL_SESSIONS_LOCK:
        session = _SHELL_SESSIONS.get(session_key)
        if session is not None and session.process.poll() is None:
            return session

        if session is not None:
            _SHELL_SESSIONS.pop(session_key, None)

        process = subprocess.Popen(
            _build_shell_command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("Could not open persistent shell pipes.")

        output_queue: Queue[str | None] = Queue()
        reader = threading.Thread(
            target=_reader_worker,
            args=(process.stdout, output_queue),
            name=f"ComfyClawExecReader-{session_key}",
            daemon=True,
        )
        reader.start()

        session = _ShellSession(process=process, output_queue=output_queue)
        if os.name == "nt":
            session.current_prompt = f"{os.getcwd()}>"
        _SHELL_SESSIONS[session_key] = session
        return session


def _drain_queue(session: _ShellSession):
    while True:
        try:
            item = session.output_queue.get_nowait()
        except Empty:
            return
        if item is None:
            raise RuntimeError("Shell session ended unexpectedly.")
        normalized_item = _normalize_output_line(item)
        if os.name == "nt" and item.startswith(_WINDOWS_PROMPT_PREFIX):
            session.current_prompt = normalized_item.rstrip("\r\n")


def _format_command_block(command_header: str, output_text: str) -> str:
    cleaned_output = output_text.rstrip("\r\n")
    if cleaned_output:
        return f"{command_header}\n{cleaned_output}\n"
    return f"{command_header}\n"


def _normalize_output_line(line: str) -> str:
    if os.name == "nt" and line.startswith(_WINDOWS_PROMPT_PREFIX):
        return line[len(_WINDOWS_PROMPT_PREFIX) :]
    return line


class Exec:
    """Execute commands in a persistent shell and return current or full session output."""

    CATEGORY = "ComfyClaw/System"
    FUNCTION = "run_command"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("terminal_text", "error_string")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "command_text": string_input("", multiline=False),
                "output_mode": combo_input(_OUTPUT_MODES, default="Current Command"),
                "timeout": int_input(30, min=1),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run_command(self, command_text, output_mode="Current Command", timeout=30, unique_id=None):
        if not isinstance(command_text, str) or not command_text.strip():
            return ("", "command_text cannot be empty.")
        if not isinstance(output_mode, str) or output_mode not in _OUTPUT_MODES:
            return ("", f"output_mode must be one of: {', '.join(_OUTPUT_MODES)}.")
        if not isinstance(timeout, int) or timeout <= 0:
            return ("", "timeout must be a positive integer.")

        session_key = _get_session_key(unique_id)
        trimmed_command = command_text.strip()
        if trimmed_command.lower() == "exit":
            exit_prompt = ""
            with _SHELL_SESSIONS_LOCK:
                existing_session = _SHELL_SESSIONS.get(session_key)
                if existing_session is not None:
                    exit_prompt = existing_session.current_prompt
            _close_session_by_key(session_key)
            if os.name == "nt":
                return (f"{exit_prompt or os.getcwd() + '>'}exit\nShell session closed.\n", "")
            return ("> exit\nShell session closed.\n", "")

        try:
            session = _get_or_create_session(unique_id)
            with session.lock:
                _drain_queue(session)
                command_header = f"{session.current_prompt}{command_text}" if os.name == "nt" and session.current_prompt else f"> {command_text}"

                marker = f"__COMFYCLAW_EXEC_DONE_{uuid.uuid4().hex}__"
                if session.process.stdin is None or session.process.poll() is not None:
                    raise RuntimeError("Persistent shell session is unavailable.")

                session.process.stdin.write(command_text)
                if not command_text.endswith("\n"):
                    session.process.stdin.write("\n")
                session.process.stdin.write(f"echo {marker}\n")
                session.process.stdin.flush()

                collected: list[str] = []
                deadline = time.monotonic() + timeout
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    try:
                        item = session.output_queue.get(timeout=remaining)
                    except Empty:
                        raise TimeoutError
                    if item is None:
                        raise RuntimeError("Shell session ended unexpectedly.")
                    normalized_item = _normalize_output_line(item)
                    stripped_line = normalized_item.rstrip("\r\n")
                    if marker in stripped_line:
                        marker_prefix = stripped_line.split(marker, 1)[0]
                        if os.name == "nt" and marker_prefix:
                            session.current_prompt = marker_prefix
                        break
                    if os.name == "nt" and item.startswith(_WINDOWS_PROMPT_PREFIX):
                        session.current_prompt = stripped_line
                        continue
                    collected.append(normalized_item)

                if os.name == "nt" and session.current_prompt:
                    collected.append(f"{session.current_prompt}\n")

                current_block = _format_command_block(command_header, "".join(collected))
                session.history_blocks.append(current_block)
                if output_mode == "Entire Terminal":
                    return ("".join(session.history_blocks), "")
                return (current_block, "")
        except TimeoutError:
            _close_session_by_key(session_key)
            return ("", f"Command timed out after {timeout} seconds and the shell session was closed.")
        except Exception as exc:
            _close_session_by_key(session_key)
            return ("", f"Could not execute command: {exc}")
