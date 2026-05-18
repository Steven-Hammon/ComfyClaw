"""Random_from_List node."""

from __future__ import annotations

from .common import collect_ordered_inputs, flexible_optional_inputs, int_input, require_string, string_input


class RandomFromList:
    """Select one non-empty input string using a seed value."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "select_text"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("string_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_1": string_input(""),
                "seed": int_input(0, min=0, max=999999999999999),
            },
            "optional": flexible_optional_inputs(),
        }

    @classmethod
    def IS_CHANGED(cls, seed=0, **kwargs):
        return seed

    def select_text(self, text_1, seed=0, **kwargs):
        inputs = [text_1] + collect_ordered_inputs(kwargs, "text_")
        if not inputs:
            return ("", "No input strings were provided.")

        values: list[str] = []
        for index, value in enumerate(inputs, start=1):
            checked_value, error = require_string(value, f"text_{index}")
            if error:
                return ("", error)
            if checked_value == "":
                continue
            values.append(checked_value)

        if not values:
            return ("", "No non-empty input strings were provided.")
        if not isinstance(seed, int):
            return ("", "seed must be an integer.")

        selected = values[seed % len(values)]
        return (selected, "")
