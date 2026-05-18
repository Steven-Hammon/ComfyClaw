"""JSON_insert_key node."""

from __future__ import annotations

from .common import (
    coerce_object_path_parts,
    combo_input,
    get_parent_and_key,
    int_input,
    parse_json_string,
    parse_jsonish_value,
    parse_key_path,
    require_string,
    serialize_json,
    string_input,
    traverse_path,
)


def _nested_value(path_parts, value):
    nested_value = value
    for part in reversed(path_parts[1:]):
        nested_value = {part: nested_value}
    return path_parts[0], nested_value


def _insert_into_object(target, target_key, new_key, new_value, mode):
    ordered_output = {}
    inserted = False
    for existing_key, existing_value in target.items():
        if existing_key == target_key and mode == "before":
            ordered_output[new_key] = new_value
            inserted = True
        ordered_output[existing_key] = existing_value
        if existing_key == target_key and mode == "after":
            ordered_output[new_key] = new_value
            inserted = True
    if not inserted:
        return False
    target.clear()
    target.update(ordered_output)
    return True


class JSONInsertKey:
    """Insert a new root key before or after another root key."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "insert_key"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
                "key_path": string_input("", multiline=False),
                "index": int_input(0, min=0),
                "new_key_path": string_input("", multiline=False),
                "value_text": string_input(""),
                "mode": combo_input(["before", "after"], default="after"),
                "insert_mode": combo_input(["key_path", "index"], default="key_path"),
            }
        }

    def insert_key(self, json_input, key_path, index=0, new_key_path="", value_text="", mode="after", insert_mode="key_path"):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(key_path, "key_path")
        checked_new_key_path, new_key_path_error = require_string(new_key_path, "new_key_path")
        checked_value, value_error = require_string(value_text, "value_text")
        if json_error or path_error or new_key_path_error or value_error:
            return ("", "; ".join(error for error in (json_error, path_error, new_key_path_error, value_error) if error))

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return (checked_json, f"Invalid JSON input: {exc}")

        if not isinstance(data, dict):
            return (checked_json, "Root JSON is not a JSON object.")

        if insert_mode == "index":
            if not isinstance(index, int):
                return (checked_json, "index must be an integer.")
            try:
                path_parts = parse_key_path(checked_path.strip())
                target_object = traverse_path(data, path_parts) if path_parts else data
            except KeyError:
                return (checked_json, f"Key path not found: {checked_path}")
            if not isinstance(target_object, dict):
                target_path = checked_path.strip() or "<root>"
                return (checked_json, f"Target at key_path is not a JSON object: {target_path}")
            ordered_keys = list(target_object.keys())
            if index < 0 or index >= len(ordered_keys):
                return (checked_json, f"Key path not found: {checked_path}")
            target_key = ordered_keys[index]
        else:
            if not checked_path.strip():
                return (checked_json, "key_path cannot be empty.")
            target_parts = parse_key_path(checked_path.strip())
            try:
                target_object, target_key = get_parent_and_key(data, target_parts)
            except KeyError:
                return (checked_json, f"Key path not found: {checked_path}")
            if not isinstance(target_object, dict) or target_key not in target_object:
                return (checked_json, f"Key path not found: {checked_path}")

        if not checked_new_key_path.strip():
            return (checked_json, "new_key_path cannot be empty.")

        new_parts = coerce_object_path_parts(parse_key_path(checked_new_key_path.strip()))
        if not new_parts:
            return (checked_json, "new_key_path must use JSON object keys only.")

        new_key, new_value = _nested_value(new_parts, parse_jsonish_value(checked_value))
        if new_key in target_object:
            return (checked_json, f"Key already exists at target path: {new_key}")

        if not _insert_into_object(target_object, target_key, new_key, new_value, mode):
            return (checked_json, f"Key path not found: {checked_path}")

        return (serialize_json(data), "")
