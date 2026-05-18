"""JSON_To_YAML node."""

from __future__ import annotations

from .common import parse_json_string, require_string, string_input
from .yaml_common import serialize_yaml


class JSONToYAML:
    """Convert JSON text to YAML text."""

    CATEGORY = "ComfyClaw/YAML"
    FUNCTION = "convert_json"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("yaml_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
            }
        }

    def convert_json(self, json_input):
        checked_json, json_error = require_string(json_input, "json_input")
        if json_error:
            return ("", json_error)
        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return ("", f"Invalid JSON input: {exc}")
        try:
            return (serialize_yaml(data), "")
        except Exception as exc:
            return ("", f"YAML output failed: {exc}")
