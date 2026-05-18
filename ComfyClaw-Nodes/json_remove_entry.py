"""JSON_Remove_Entry node."""

from __future__ import annotations

from .common import combo_input, get_parent_and_key, int_input, parse_json_string, parse_key_path, require_string, serialize_json, string_input, traverse_path


class JSONRemoveEntry:
    """Delete a key or array entry from JSON."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "remove_entry"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
                "key_path": string_input("", multiline=False),
                "index": int_input(0, min=0),
                "remove_mode": combo_input(["key_path", "index"], default="key_path"),
            }
        }

    def remove_entry(self, json_input, key_path, index=0, remove_mode="key_path"):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(key_path, "key_path")
        if json_error or path_error:
            return ("", "; ".join(error for error in (json_error, path_error) if error))

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return (checked_json, f"Invalid JSON input: {exc}")

        if remove_mode == "index":
            if not isinstance(index, int):
                return ("", "index must be an integer.")
            try:
                path_parts = parse_key_path(checked_path.strip())
                target = traverse_path(data, path_parts) if path_parts else data
            except KeyError:
                return (checked_json, f"Key path not found: {checked_path}")

            if not isinstance(target, dict):
                target_path = checked_path.strip() or "<root>"
                return (checked_json, f"Target at key_path is not a JSON object: {target_path}")

            ordered_keys = list(target.keys())
            if index < 0 or index >= len(ordered_keys):
                return (checked_json, f"Key path not found: {checked_path}")

            del target[ordered_keys[index]]
            return (serialize_json(data), "")

        if not checked_path.strip():
            return (checked_json, "key_path cannot be empty.")
        path_parts = parse_key_path(checked_path.strip())
        try:
            parent, target = get_parent_and_key(data, path_parts)
        except KeyError:
            return (checked_json, f"Key path not found: {checked_path}")

        if isinstance(target, int):
            if not isinstance(parent, list) or target < 0 or target >= len(parent):
                return (checked_json, f"Key path not found: {checked_path}")
            del parent[target]
            return (serialize_json(data), "")

        if not isinstance(parent, dict) or target not in parent:
            return (checked_json, f"Key path not found: {checked_path}")
        del parent[target]
        return (serialize_json(data), "")


