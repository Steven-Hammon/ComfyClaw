"""Prompt_Combine node."""

from __future__ import annotations

from .common import MAX_DYNAMIC_SLOTS, collect_ordered_inputs, flexible_optional_inputs, require_string, string_input


class PromptCombine:
    """Combine multiple text fragments into one string."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "combine"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("combined_string", "error_string")
    SEARCH_ALIASES = ["text concat", "join text", "merge strings"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_1": string_input(""),
            },
            "optional": flexible_optional_inputs(),
        }

    def combine(self, text_1, **kwargs):
        pieces = [text_1] + collect_ordered_inputs(kwargs, "text_")
        cleaned: list[str] = []
        for index, piece in enumerate(pieces, start=1):
            value, error = require_string(piece, f"text_{index}")
            if error:
                return ("", error)
            cleaned.append(value)
        return ("".join(cleaned), "")
