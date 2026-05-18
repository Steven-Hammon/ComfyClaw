"""JSON_Count_Keys node."""

from __future__ import annotations

from typing import Any

from .common import combo_input, parse_json_string, parse_key_path, require_string, string_input, traverse_path


class JSONCountKeys:
    """Count keys on a JSON object at a specific path."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "count_keys"
    RETURN_TYPES = ("INT", "STRING")
    RETURN_NAMES = ("key_count", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
                "key_path": string_input("", multiline=False),
                "count_mode": combo_input(["Root", "All"], default="Root"),
            }
        }

    def count_keys(self, json_input, key_path="", count_mode="Root"):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(key_path, "key_path")
        if json_error or path_error:
            return (0, "; ".join(error for error in (json_error, path_error) if error))

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return (0, f"Invalid JSON input: {exc}")

        try:
            target = traverse_path(data, parse_key_path(checked_path.strip())) if checked_path.strip() else data
        except KeyError:
            return (0, f"Key path not found: {checked_path}")

        if not isinstance(target, dict):
            target_path = checked_path.strip() or "<root>"
            return (0, f"Target at key_path is not a JSON object: {target_path}")

        if count_mode == "All":
            return (self._count_all_keys(target), "")
        if count_mode != "Root":
            return (0, "count_mode must be Root or All.")

        return (len(target), "")

    def _count_all_keys(self, value: Any) -> int:
        if isinstance(value, dict):
            return len(value) + sum(self._count_all_keys(item) for item in value.values())
        if isinstance(value, list):
            return sum(self._count_all_keys(item) for item in value)
        return 0
