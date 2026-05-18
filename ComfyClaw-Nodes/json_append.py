"""JSON_Append node."""

from __future__ import annotations

from .common import coerce_object_path_parts, parse_json_string, parse_jsonish_value, parse_key_path, require_string, serialize_json, string_input


class JSONAppend:
    """Append a new key/value pair to an ordered JSON object path."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "append_value"
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

    def append_value(self, json_input, key_path, value_text):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(key_path, "key_path")
        checked_value, value_error = require_string(value_text, "value_text")
        if json_error or path_error or value_error:
            return ("", "; ".join(error for error in (json_error, path_error, value_error) if error))
        if not checked_path.strip():
            return (checked_json, "key_path cannot be empty.")

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return (checked_json, f"Invalid JSON input: {exc}")

        if not isinstance(data, dict):
            return (checked_json, "Root JSON is not a JSON object.")

        path_parts = coerce_object_path_parts(parse_key_path(checked_path.strip()))
        if not path_parts:
            return (checked_json, "key_path must use JSON object keys only.")

        parent = data
        for depth, part in enumerate(path_parts[:-1], start=1):
            if part not in parent:
                parent[part] = {}
            elif not isinstance(parent[part], dict):
                parent_path = ".".join(path_parts[:depth])
                return (checked_json, f"Value at key_path is not a JSON object: {parent_path}")
            parent = parent[part]

        leaf_key = path_parts[-1]
        if leaf_key in parent:
            return (checked_json, f"Key path already exists: {checked_path.strip()}")

        parent[leaf_key] = parse_jsonish_value(checked_value)
        return (serialize_json(data), "")
