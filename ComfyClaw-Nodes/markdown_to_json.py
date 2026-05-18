"""Markdown_TO_JSON node."""

from __future__ import annotations

from .common import require_string, string_input
from .markdown_json_common import markdown_to_json_text


class MarkdownToJSON:
    """Convert lightweight heading-based Markdown sections to JSON."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "convert_markdown"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "markdown_input": string_input(""),
            }
        }

    def convert_markdown(self, markdown_input):
        checked_markdown, markdown_error = require_string(markdown_input, "markdown_input")
        if markdown_error:
            return ("", markdown_error)
        try:
            return (markdown_to_json_text(checked_markdown), "")
        except Exception as exc:
            return ("", f"Markdown conversion failed: {exc}")
