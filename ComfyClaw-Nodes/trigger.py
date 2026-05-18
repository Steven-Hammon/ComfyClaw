"""Trigger node."""

from __future__ import annotations

from .common import any_type, custom_input


class Trigger:
    """Emit an empty string and report whether any payload was received."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "trigger"
    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("trigger_string", "triggered")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": custom_input(any_type),
            }
        }

    def trigger(self, input=None):
        return ("", input not in (None, ""))
