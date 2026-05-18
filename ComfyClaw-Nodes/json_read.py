"""JSON_Read node."""

from __future__ import annotations

from .common import combo_input, int_input, parse_json_string, parse_key_path, require_string, serialize_json, string_input, to_plain_text, traverse_path


def _indexed_items(target):
    if isinstance(target, dict):
        return list(target.items())
    if isinstance(target, list):
        return [(str(index), value) for index, value in enumerate(target)]
    return []


def _leaf_items(target):
    items = []

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if isinstance(child, (dict, list)):
                    visit(child)
                else:
                    items.append((str(key), child))
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                if isinstance(child, (dict, list)):
                    visit(child)
                else:
                    items.append((str(index), child))

    visit(target)
    return items


def _all_items(target):
    items = []

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                items.append((str(key), child))
                if isinstance(child, (dict, list)):
                    visit(child)
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                items.append((str(index), child))
                if isinstance(child, (dict, list)):
                    visit(child)

    visit(target)
    return items


def _serialize_key_value(key, value):
    return serialize_json({str(key): value})


class JSONRead:
    """Read a value from JSON using a dot-separated key path or ordered object index."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "read_value"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("key", "value_text", "value_json", "key/value_json", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
                "key_path": string_input("", multiline=False),
                "index": int_input(0, min=0),
                "read_mode": combo_input(["key_path", "index"], default="key_path"),
                "index_mode": combo_input(["root", "leaves", "all"], default="root"),
            }
        }

    def read_value(self, json_input, key_path, index=0, read_mode="key_path", index_mode="root"):
        checked_json, json_error = require_string(json_input, "json_input")
        checked_path, path_error = require_string(key_path, "key_path")
        if json_error or path_error:
            return ("", "", "", "", "; ".join(error for error in (json_error, path_error) if error))
        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return ("", "", "", "", f"Invalid JSON input: {exc}")

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
                return ("", "", "", "", f"Target at key_path is not a JSON object or array: {target_path}")

            if index_mode == "leaves":
                items = _leaf_items(target)
            elif index_mode == "all":
                items = _all_items(target)
            else:
                items = _indexed_items(target)
            if index < 0 or index >= len(items):
                return ("", "", "", "", f"Key path not found: {checked_path}")

            key, value = items[index]
            return (str(key), to_plain_text(value), serialize_json(value), _serialize_key_value(key, value), "")

        if not checked_path.strip():
            return ("", "", "", "", "key_path cannot be empty.")

        path_parts = parse_key_path(checked_path.strip())
        try:
            value = traverse_path(data, path_parts)
        except KeyError:
            return ("", "", "", "", f"Key path not found: {checked_path}")

        key = str(path_parts[-1])
        return (key, to_plain_text(value), serialize_json(value), _serialize_key_value(key, value), "")

