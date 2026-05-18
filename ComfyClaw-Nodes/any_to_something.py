"""Any_To_Something node."""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_DOWN, ROUND_HALF_UP
from typing import Any

from .common import any_type, combo_input, custom_input, to_plain_text


FLOAT_MODES = ("ceil", "floor", "round half-up", "round half-down")


def _float_to_int(value: float, float_mode: str) -> int:
    if float_mode == "ceil":
        return math.ceil(value)
    if float_mode == "floor":
        return math.floor(value)
    rounding = ROUND_HALF_UP if float_mode == "round half-up" else ROUND_HALF_DOWN
    return int(Decimal(str(value)).to_integral_value(rounding=rounding))


class AnyToSomething:
    """Expose common typed versions of any input value."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "convert_any"
    RETURN_TYPES = ("STRING", "INT", "FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("string_output", "int_output", "float_output", "boolean_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": custom_input(any_type),
                "float_mode": combo_input(FLOAT_MODES, default="ceil"),
            }
        }

    def convert_any(self, input: Any = None, float_mode: str = "ceil"):
        string_output = to_plain_text(input)
        int_output = ""
        float_output = ""
        boolean_output = ""

        if float_mode not in FLOAT_MODES:
            return (string_output, int_output, float_output, boolean_output, "float_mode must be ceil, floor, round half-up, or round half-down.")

        if isinstance(input, bool):
            boolean_output = input
        elif isinstance(input, int):
            int_output = input
            float_output = float(input)
        elif isinstance(input, float):
            if math.isfinite(input):
                int_output = _float_to_int(input, float_mode)
                float_output = input
        elif isinstance(input, str):
            stripped_input = input.strip()
            normalized_input = stripped_input.lower()
            if normalized_input == "true":
                boolean_output = True
            elif normalized_input == "false":
                boolean_output = False
            else:
                try:
                    parsed_float = float(stripped_input)
                except ValueError:
                    parsed_float = None

                if parsed_float is not None and math.isfinite(parsed_float):
                    float_output = parsed_float
                    int_output = _float_to_int(parsed_float, float_mode)

        return (string_output, int_output, float_output, boolean_output, "")
