"""JSON_Mass_Math node."""

from __future__ import annotations

import builtins

from .common import combo_input, int_input, parse_json_string, parse_key_path, require_string, serialize_json, string_input
from .json_mass_common import OPERATIONS, apply_operation, clamp, coerce_int, find_relative_targets, validate_bounds


class JSONMassMath:
    """Apply integer math to every matching sub-key value in a JSON object."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "mass_math"
    RETURN_TYPES = ("STRING", "INT", "STRING")
    RETURN_NAMES = ("json_output", "lowest_value", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
                "sub_key_path": string_input("", multiline=False),
                "operation": combo_input(OPERATIONS, default="add"),
                "int": int_input(0),
                "min": int_input(0),
                "max": int_input(999999),
            }
        }

    def mass_math(self, json_input, sub_key_path, operation="add", int=0, min=0, max=999999):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(sub_key_path, "sub_key_path")
        if json_error or path_error:
            return ("", 0, "; ".join(error for error in (json_error, path_error) if error))
        if not checked_path.strip():
            return (checked_json, 0, "sub_key_path cannot be empty.")
        if not isinstance(operation, str) or operation not in OPERATIONS:
            return (checked_json, 0, f"operation must be one of: {', '.join(OPERATIONS)}.")
        if not isinstance(int, builtins.int) or isinstance(int, bool):
            return (checked_json, 0, "int must be an integer.")
        bounds_error = validate_bounds(min, max)
        if bounds_error:
            return (checked_json, 0, bounds_error)

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return (checked_json, 0, f"Invalid JSON input: {exc}")

        path_parts = parse_key_path(checked_path.strip())
        targets = find_relative_targets(data, path_parts)
        if not targets:
            return (checked_json, 0, f"No matching sub_key_path found: {checked_path}")

        lowest_value: int | None = None
        for parent, key, target_path in targets:
            original, value_error = coerce_int(parent[key], target_path)
            if value_error:
                return (checked_json, 0, value_error)
            adjusted, math_error = apply_operation(original, operation, int)
            if math_error:
                return (checked_json, 0, math_error)
            adjusted = clamp(adjusted, min, max)
            parent[key] = str(adjusted)
            if lowest_value is None or adjusted < lowest_value:
                lowest_value = adjusted

        return (serialize_json(data), lowest_value if lowest_value is not None else 0, "")
