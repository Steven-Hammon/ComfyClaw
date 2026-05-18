"""JSON_Mass_Remove node."""

from __future__ import annotations

import builtins

from .common import combo_input, int_input, parse_json_string, parse_key_path, require_string, serialize_json, string_input
from .json_mass_common import LOGIC_OPERATORS, coerce_int, compare_value, find_relative_targets


class JSONMassRemove:
    """Remove root keys matching a nested integer comparison until a root-key limit is reached."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "mass_remove"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
                "max_rootkeys": int_input(0, min=0),
                "sub_key_path": string_input("", multiline=False),
                "logic": combo_input(LOGIC_OPERATORS, default="<"),
                "int": int_input(0),
            }
        }

    def mass_remove(self, json_input, max_rootkeys=0, sub_key_path="", logic="<", int=0):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(sub_key_path, "sub_key_path")
        if json_error or path_error:
            return ("", "; ".join(error for error in (json_error, path_error) if error))
        if not isinstance(max_rootkeys, builtins.int) or isinstance(max_rootkeys, bool):
            return (checked_json, "max_rootkeys must be an integer.")
        if max_rootkeys < 0:
            return (checked_json, "max_rootkeys cannot be negative.")
        if not checked_path.strip():
            return (checked_json, "sub_key_path cannot be empty.")
        if not isinstance(logic, str) or logic not in LOGIC_OPERATORS:
            return (checked_json, f"logic must be one of: {', '.join(LOGIC_OPERATORS)}.")
        if not isinstance(int, builtins.int) or isinstance(int, bool):
            return (checked_json, "int must be an integer.")

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return (checked_json, f"Invalid JSON input: {exc}")
        if not isinstance(data, dict):
            return (checked_json, "Root JSON is not a JSON object.")

        path_parts = parse_key_path(checked_path.strip())
        for root_key in list(data.keys()):
            if len(data) <= max_rootkeys:
                break

            matches = find_relative_targets(data[root_key], path_parts)
            should_remove = False
            for parent, key, target_path in matches:
                value, value_error = coerce_int(parent[key], f"{root_key}.{target_path}")
                if value_error:
                    return (checked_json, value_error)
                matched, logic_error = compare_value(value, logic, int)
                if logic_error:
                    return (checked_json, logic_error)
                if matched:
                    should_remove = True
                    break

            if should_remove:
                del data[root_key]

        if len(data) > max_rootkeys:
            return (serialize_json(data), "Could not reduce root key count to max_rootkeys; no more matching root keys.")
        return (serialize_json(data), "")
