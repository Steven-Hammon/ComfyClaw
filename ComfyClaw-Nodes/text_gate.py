"""Text_Gate node."""

from __future__ import annotations

from .common import MAX_DYNAMIC_SLOTS, bool_input, flexible_optional_inputs, join_messages, match_text, require_string, string_input


class TextGate:
    """Allow or block a string using simple match rules."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "gate"
    RETURN_TYPES = ("STRING", "STRING", "BOOLEAN")
    RETURN_NAMES = ("string_output", "error_string", "is_match")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": string_input(""),
                "mode": bool_input(False, label_on="allow", label_off="deny"),
                "override_text": string_input(""),
                "use_override": bool_input(False, label_on="yes", label_off="no"),
            },
            "optional": flexible_optional_inputs(),
        }

    def gate(self, input_string="", mode=False, override_text="", use_override=False, **kwargs):
        checked_input, input_error = require_string(input_string, "input_string")
        override_value, override_error = require_string(override_text, "override_text")
        if input_error or override_error:
            return ("", join_messages(input_error, override_error), False)

        matches = []
        for index in range(1, MAX_DYNAMIC_SLOTS + 1):
            rule_text_key = f"rule_{index}_text"
            if rule_text_key not in kwargs:
                continue
            rule_type = kwargs.get(f"rule_{index}_type", "contains")
            rule_text = kwargs.get(rule_text_key)
            if rule_text is None:
                continue
            if not isinstance(rule_text, str):
                return ("", f"rule_{index}_text must be a string.", False)
            if not isinstance(rule_type, str):
                return ("", f"rule_{index}_type must be a string.", False)
            if rule_text == "":
                if checked_input == "":
                    matches.append(index)
                continue
            if match_text(checked_input, rule_text, rule_type):
                matches.append(index)

        allow_mode = bool(mode)
        has_match = bool(matches)
        if allow_mode:
            if has_match:
                return ((override_value if use_override else checked_input), "", True)
            return ("", "", False)

        if has_match:
            return ("", "", True)
        return ((override_value if use_override else checked_input), "", False)
