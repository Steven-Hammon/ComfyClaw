"""YAML_Read node."""

from __future__ import annotations

from .common import combo_input, int_input, parse_key_path, require_string, string_input, to_plain_text, traverse_path
from .json_read import _all_items, _indexed_items, _leaf_items
from .yaml_common import parse_yaml_string, serialize_yaml


def _serialize_key_value_yaml(key, value):
    return serialize_yaml({str(key): value})


class YAMLRead:
    """Read a value from YAML using a dot-separated key path or ordered object index."""

    CATEGORY = "ComfyClaw/YAML"
    FUNCTION = "read_value"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("key", "value_text", "value_yaml", "key/value_yaml", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "yaml_input": string_input(""),
                "key_path": string_input("", multiline=False),
                "index": int_input(0, min=0),
                "read_mode": combo_input(["key_path", "index"], default="key_path"),
                "index_mode": combo_input(["root", "leaves", "all"], default="root"),
            }
        }

    def read_value(self, yaml_input, key_path, index=0, read_mode="key_path", index_mode="root"):
        checked_yaml, yaml_error = require_string(yaml_input, "yaml_input")
        checked_path, path_error = require_string(key_path, "key_path")
        if yaml_error or path_error:
            return ("", "", "", "", "; ".join(error for error in (yaml_error, path_error) if error))
        try:
            data = parse_yaml_string(checked_yaml)
        except Exception as exc:
            return ("", "", "", "", f"Invalid YAML input: {exc}")

        if read_mode == "index":
            if not isinstance(index, int):
                return ("", "", "", "", "index must be an integer.")
            if index_mode not in {"root", "leaves", "all"}:
                return ("", "", "", "", "index_mode must be root, leaves, or all.")
            try:
                path_parts = parse_key_path(checked_path.strip())
                target = traverse_path(data, path_parts) if path_parts else data
            except KeyError:
                return ("", "", "", "", f"Key path not found: {checked_path}")

            if not isinstance(target, (dict, list)):
                target_path = checked_path.strip() or "<root>"
                return ("", "", "", "", f"Target at key_path is not a YAML object or array: {target_path}")

            if index_mode == "leaves":
                items = _leaf_items(target)
            elif index_mode == "all":
                items = _all_items(target)
            else:
                items = _indexed_items(target)
            if index < 0 or index >= len(items):
                return ("", "", "", "", f"Key path not found: {checked_path}")

            key, value = items[index]
            return (str(key), to_plain_text(value), serialize_yaml(value), _serialize_key_value_yaml(key, value), "")

        if not checked_path.strip():
            return ("", "", "", "", "key_path cannot be empty.")

        path_parts = parse_key_path(checked_path.strip())
        try:
            value = traverse_path(data, path_parts)
        except KeyError:
            return ("", "", "", "", f"Key path not found: {checked_path}")

        key = str(path_parts[-1])
        return (key, to_plain_text(value), serialize_yaml(value), _serialize_key_value_yaml(key, value), "")
