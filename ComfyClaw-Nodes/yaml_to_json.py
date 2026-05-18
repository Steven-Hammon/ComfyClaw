"""YAML_To_JSON node."""

from __future__ import annotations

from .common import require_string, serialize_json, string_input
from .yaml_common import parse_yaml_string


class YAMLToJSON:
    """Convert YAML text to formatted JSON text."""

    CATEGORY = "ComfyClaw/YAML"
    FUNCTION = "convert_yaml"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "yaml_input": string_input(""),
            }
        }

    def convert_yaml(self, yaml_input):
        checked_yaml, yaml_error = require_string(yaml_input, "yaml_input")
        if yaml_error:
            return ("", yaml_error)
        try:
            data = parse_yaml_string(checked_yaml)
        except Exception as exc:
            return ("", f"Invalid YAML input: {exc}")
        return (serialize_json(data), "")
