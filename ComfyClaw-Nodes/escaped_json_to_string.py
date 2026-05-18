"""Escaped_JSON_To_String node."""

from __future__ import annotations

from .common import require_string, string_input
from .markdown_json_common import unescape_json_string


class EscapedJSONToString:
    """Decode JSON-string escapes back to plain text."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "unescape_json"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("string_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "escaped_json": string_input(""),
            }
        }

    def unescape_json(self, escaped_json):
        checked_json, json_error = require_string(escaped_json, "escaped_json")
        if json_error:
            return ("", json_error)
        try:
            return (unescape_json_string(checked_json), "")
        except Exception as exc:
            return ("", f"Invalid escaped JSON string: {exc}")
