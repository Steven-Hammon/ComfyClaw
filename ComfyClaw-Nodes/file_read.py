"""File_Read node."""

from __future__ import annotations

from .common import read_text_file, require_string, resolve_text_path, string_input


class FileRead:
    """Read raw text from a file path."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "read_file"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("file_text", "error_string")
    SEARCH_ALIASES = ["read file", "load text file"]

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"file_path": string_input("", multiline=False)}}

    @classmethod
    def IS_CHANGED(cls, file_path):
        # File contents can change outside ComfyUI without any widget/input value changing.
        # Returning NaN tells ComfyUI to always treat the node as changed.
        return float("nan")

    def read_file(self, file_path):
        checked_path, error = require_string(file_path, "file_path")
        if error:
            return ("", error)
        if not checked_path.strip():
            return ("", "file_path cannot be empty.")
        path = resolve_text_path(checked_path.strip())
        if not path.exists():
            return ("", f"File not found: {path}")
        if not path.is_file():
            return ("", f"Path is not a file: {path}")
        try:
            return (read_text_file(path), "")
        except Exception as exc:  # pragma: no cover - filesystem dependent
            return ("", f"Could not read file: {exc}")
