"""String_To_Escaped_JSON node."""

from __future__ import annotations

from .common import require_string, string_input
from .markdown_json_common import escaped_json_string


class StringToEscapedJSON:
    """Escape a plain string so it can be pasted inside a JSON string value."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "escape_string"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("escaped_json", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_input": string_input(""),
            }
        }

    def escape_string(self, string_input):
        checked_string, string_error = require_string(string_input, "string_input")
        if string_error:
            return ("", string_error)
        return (escaped_json_string(checked_string), "")
