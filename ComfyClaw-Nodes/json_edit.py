"""JSON_Edit node."""

from __future__ import annotations

from .common import get_parent_and_key, parse_json_string, parse_jsonish_value, parse_key_path, require_string, serialize_json, string_input


class JSONEdit:
    """Replace a value at an existing JSON key path."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "edit_value"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
                "key_path": string_input("", multiline=False),
                "value_text": string_input(""),
            }
        }

    def edit_value(self, json_input, key_path, value_text):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(key_path, "key_path")
        checked_value, value_error = require_string(value_text, "value_text")
        if json_error or path_error or value_error:
            return ("", "; ".join(error for error in (json_error, path_error, value_error) if error))
        if not checked_path.strip():
            return (checked_json, "key_path cannot be empty.")
        if checked_value == "":
            return (checked_json, "value_text cannot be empty.")

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return (checked_json, f"Invalid JSON input: {exc}")

        path_parts = parse_key_path(checked_path.strip())
        try:
            parent, target = get_parent_and_key(data, path_parts)
        except KeyError:
            return (checked_json, f"Key path not found: {checked_path}")

        replacement = parse_jsonish_value(checked_value)
        if isinstance(target, int):
            if not isinstance(parent, list) or target < 0 or target >= len(parent):
                return (checked_json, f"Key path not found: {checked_path}")
            parent[target] = replacement
        else:
            if not isinstance(parent, dict) or target not in parent:
                return (checked_json, f"Key path not found: {checked_path}")
            parent[target] = replacement
        return (serialize_json(data), "")
