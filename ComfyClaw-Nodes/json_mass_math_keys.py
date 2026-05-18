"""JSON_Mass_Math_Keys node."""

from __future__ import annotations

from .common import combo_input, int_input, parse_json_string, require_string, serialize_json, string_input
from .json_mass_common import (
    OPERATIONS,
    apply_operation,
    clamp,
    coerce_int,
    format_path,
    get_target,
    iter_leaf_paths,
    try_coerce_int,
    validate_bounds,
)


class JSONMassMathKeys:
    """Use matching integer leaf paths from one JSON object to adjust another."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "mass_math_keys"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_destination": string_input(""),
                "operation": combo_input(OPERATIONS, default="add"),
                "json_source": string_input(""),
                "min": int_input(0),
                "max": int_input(999999),
            }
        }

    def mass_math_keys(self, json_destination, operation="add", json_source="", min=0, max=999999):
        checked_destination, destination_error = require_string(json_destination, "json_destination")
        checked_source, source_error = require_string(json_source, "json_source")
        if destination_error or source_error:
            return ("", "; ".join(error for error in (destination_error, source_error) if error))
        if not isinstance(operation, str) or operation not in OPERATIONS:
            return (checked_destination, f"operation must be one of: {', '.join(OPERATIONS)}.")
        bounds_error = validate_bounds(min, max)
        if bounds_error:
            return (checked_destination, bounds_error)

        try:
            destination_data = parse_json_string(checked_destination)
        except Exception as exc:
            return (checked_destination, f"Invalid json_destination: {exc}")
        try:
            source_data = parse_json_string(checked_source)
        except Exception as exc:
            return (checked_destination, f"Invalid json_source: {exc}")

        for source_path, source_value in iter_leaf_paths(source_data):
            operand, is_integer = try_coerce_int(source_value)
            if not is_integer:
                continue

            parent, key, target_error = get_target(destination_data, list(source_path))
            if target_error:
                continue

            target_path = format_path(source_path)
            original, value_error = coerce_int(parent[key], target_path)
            if value_error:
                return (checked_destination, value_error)
            adjusted, math_error = apply_operation(original, operation, operand)
            if math_error:
                return (checked_destination, math_error)
            parent[key] = str(clamp(adjusted, min, max))

        return (serialize_json(destination_data), "")
