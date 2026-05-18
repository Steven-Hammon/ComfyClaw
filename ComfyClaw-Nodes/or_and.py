"""Or_And node."""

from __future__ import annotations

from .common import bool_input, combo_input, flexible_optional_inputs


def _collect_numbered_inputs(kwargs):
    numbered = []
    for key, value in kwargs.items():
        if not key.startswith("input_"):
            continue
        suffix = key[len("input_") :]
        if not suffix.isdigit():
            continue
        numbered.append((int(suffix), value))
    numbered.sort(key=lambda item: item[0])
    return numbered


class OrAnd:
    """Evaluate a dynamic set of boolean inputs with OR or AND logic."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "evaluate_logic"
    RETURN_TYPES = ("BOOLEAN", "STRING")
    RETURN_NAMES = ("output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "operation": combo_input(["Or", "And"], "Or"),
            },
            "optional": flexible_optional_inputs(
                {
                    "input_1": bool_input(False),
                }
            ),
        }

    def evaluate_logic(self, operation="Or", **kwargs):
        if operation not in {"Or", "And"}:
            return (False, "operation must be Or or And.")

        inputs = _collect_numbered_inputs(kwargs)
        if not inputs:
            inputs = [(1, False)]

        for index, value in inputs:
            if not isinstance(value, bool):
                return (False, f"input_{index} must be a boolean.")

        values = [value for _, value in inputs]
        if operation == "And":
            return (all(values), "")
        return (any(values), "")
