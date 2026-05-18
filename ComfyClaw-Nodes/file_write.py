"""File_Write node."""

from __future__ import annotations

from .common import combo_input, require_string, resolve_text_path, string_input


class FileWrite:
    """Write text to a file path."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "write_file"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_text", "error_string")
    OUTPUT_NODE = True
    SEARCH_ALIASES = ["write file", "save text file"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": string_input("", multiline=False),
                "text_input": string_input(""),
                "mode": combo_input(["overwrite", "append"], default="overwrite"),
                "success_text": string_input(""),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def write_file(self, file_path, text_input, mode="overwrite", success_text=""):
        checked_path, path_error = require_string(file_path, "file_path")
        checked_text, text_error = require_string(text_input, "text_input")
        checked_success, success_error = require_string(success_text, "success_text")
        if path_error or text_error or success_error:
            return ("", "; ".join(error for error in (path_error, text_error, success_error) if error))
        if not checked_path.strip():
            return ("", "file_path cannot be empty.")
        if mode not in {"overwrite", "append"}:
            return ("", "mode must be overwrite or append.")

        path = resolve_text_path(checked_path.strip())
        parent = path.parent
        if not parent.exists():
            return ("", f"Directory does not exist: {parent}")

        file_mode = "w" if mode == "overwrite" else "a"
        try:
            with path.open(file_mode, encoding="utf-8") as handle:
                handle.write(checked_text)
        except Exception as exc:  # pragma: no cover - filesystem dependent
            return ("", f"Could not write file: {exc}")
        return (checked_success, "")
