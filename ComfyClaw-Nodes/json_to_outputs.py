"""JSON_to_outputs node."""

from __future__ import annotations

from typing import Any

from .common import MAX_DYNAMIC_SLOTS, flexible_optional_inputs, parse_json_string, require_string, string_input, to_plain_text

OUTPUT_MODES = ("key", "value", "key/value")


class JSONToOutputs:
    """Walk JSON entries in order and expose selected keys or values as outputs."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "json_to_outputs"
    RETURN_TYPES = tuple(["STRING"] * MAX_DYNAMIC_SLOTS + ["STRING"])
    RETURN_NAMES = tuple([f"output_{index}" for index in range(MAX_DYNAMIC_SLOTS)] + ["error_string"])

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
            },
            "optional": flexible_optional_inputs(),
        }

    def json_to_outputs(self, json_input, **kwargs):
        checked_json, json_error = require_string(json_input, "json_input")
        if json_error:
            return self._blank_outputs(json_error)

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return self._blank_outputs(f"Invalid JSON input: {exc}")

        modes, mode_error = self._collect_modes(kwargs)
        if mode_error:
            return self._blank_outputs(mode_error)

        entries = list(self._walk_entries(data))
        outputs = [""] * MAX_DYNAMIC_SLOTS
        for index, mode in enumerate(modes):
            if mode is None or index >= len(entries):
                continue
            key, value = entries[index]
            outputs[index] = self._format_entry(key, value, mode)

        return tuple(outputs + [""])

    def _collect_modes(self, kwargs: dict[str, Any]) -> tuple[list[str | None], str]:
        modes: list[str | None] = [None] * MAX_DYNAMIC_SLOTS
        found_any = False
        for key, value in kwargs.items():
            if not isinstance(key, str) or not key.startswith("output_") or not key.endswith("_mode"):
                continue
            index_text = key[len("output_") : -len("_mode")]
            if not index_text.isdigit():
                continue
            index = int(index_text)
            if index < 0 or index >= MAX_DYNAMIC_SLOTS:
                continue
            if not isinstance(value, str):
                return ([], f"{key} must be a string.")
            mode = value.strip().lower()
            if mode not in OUTPUT_MODES:
                return ([], f"{key} must be one of: {', '.join(OUTPUT_MODES)}.")
            modes[index] = mode
            found_any = True
        if not found_any:
            modes[0] = "value"
        return (modes, "")

    def _walk_entries(self, value: Any):
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                yield (key_text, item)
                if isinstance(item, (dict, list)):
                    yield from self._walk_entries(item)
            return

        if isinstance(value, list):
            for index, item in enumerate(value):
                key_text = str(index)
                yield (key_text, item)
                if isinstance(item, (dict, list)):
                    yield from self._walk_entries(item)
            return

        yield ("", value)

    def _format_entry(self, key: str, value: Any, mode: str) -> str:
        value_text = to_plain_text(value)
        if mode == "key":
            return key
        if mode == "key/value":
            if key == "":
                return value_text
            if value_text == "":
                return key
            return f"{key} {value_text}"
        return value_text

    def _blank_outputs(self, error: str):
        return tuple([""] * MAX_DYNAMIC_SLOTS + [error])
