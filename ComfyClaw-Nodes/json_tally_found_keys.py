"""JSON_Tally_Found_Keys node."""

from __future__ import annotations

from typing import Any

from .common import coerce_object_path_parts, parse_json_string, parse_key_path, require_string, serialize_json, string_input
from .json_mass_common import coerce_int, format_path


def _build_nested_value(path_parts: list[str], value: str) -> dict[str, Any]:
    nested: Any = value
    for part in reversed(path_parts):
        nested = {part: nested}
    return nested


def _get_or_create_parent(data: dict[str, Any], path_parts: list[str]) -> tuple[dict[str, Any] | None, str]:
    current: Any = data
    for part in path_parts[:-1]:
        if not isinstance(current, dict):
            return None, f"Value at {part} must be a JSON object."
        if part not in current:
            current[part] = {}
        elif not isinstance(current[part], dict):
            return None, f"Value at {part} must be a JSON object."
        current = current[part]
    if not isinstance(current, dict):
        return None, f"Value at {format_path(path_parts[:-1])} must be a JSON object."
    return current, ""


class JSONTallyFoundKeys:
    """Increment destination counters for root keys found in a source JSON object."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "tally_found_keys"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_source": string_input(""),
                "json_destination": string_input(""),
                "sub_key_path": string_input("", multiline=False),
            }
        }

    def tally_found_keys(self, json_source, json_destination, sub_key_path):
        checked_source, source_error = require_string(json_source, "json_source")
        checked_destination, destination_error = require_string(json_destination, "json_destination")
        checked_path, path_error = require_string(sub_key_path, "sub_key_path")
        if source_error or destination_error or path_error:
            return ("", "; ".join(error for error in (source_error, destination_error, path_error) if error))
        if not checked_path.strip():
            return (checked_destination, "sub_key_path cannot be empty.")

        try:
            source_data = parse_json_string(checked_source)
        except Exception as exc:
            return (checked_destination, f"Invalid json_source: {exc}")
        try:
            destination_data = parse_json_string(checked_destination)
        except Exception as exc:
            return (checked_destination, f"Invalid json_destination: {exc}")

        if not isinstance(source_data, dict):
            return (checked_destination, "Root json_source is not a JSON object.")
        if not isinstance(destination_data, dict):
            return (checked_destination, "Root json_destination is not a JSON object.")

        path_parts = coerce_object_path_parts(parse_key_path(checked_path.strip()))
        if not path_parts:
            return (checked_destination, "sub_key_path cannot be empty.")

        for root_key in source_data:
            if root_key not in destination_data:
                destination_data[root_key] = _build_nested_value(path_parts, "1")
                continue

            root_value = destination_data[root_key]
            if not isinstance(root_value, dict):
                return (checked_destination, f"Value at {root_key} must be a JSON object.")

            parent, parent_error = _get_or_create_parent(root_value, path_parts)
            if parent_error:
                return (checked_destination, f"{root_key}.{parent_error}")
            assert parent is not None

            leaf_key = path_parts[-1]
            if leaf_key not in parent:
                parent[leaf_key] = "1"
                continue

            count, count_error = coerce_int(parent[leaf_key], f"{root_key}.{format_path(path_parts)}")
            if count_error:
                return (checked_destination, count_error)
            parent[leaf_key] = str(count + 1)

        return (serialize_json(destination_data), "")
