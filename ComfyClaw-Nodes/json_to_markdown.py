"""JSON_TO_Markdown node."""

from __future__ import annotations

from .common import require_string, string_input
from .markdown_json_common import json_pairs_to_markdown, parse_json_pairs


class JSONToMarkdown:
    """Convert structured JSON prompt sections to lightweight Markdown."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "convert_json"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("markdown_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
            }
        }

    def convert_json(self, json_input):
        checked_json, json_error = require_string(json_input, "json_input")
        if json_error:
            return ("", json_error)
        try:
            data = parse_json_pairs(checked_json)
            return (json_pairs_to_markdown(data), "")
        except Exception as exc:
            return ("", f"Invalid JSON input: {exc}")
