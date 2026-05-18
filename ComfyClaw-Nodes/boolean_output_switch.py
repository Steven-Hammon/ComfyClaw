"""Boolean_Output_Switch node."""

from __future__ import annotations

try:
    from comfy_execution.graph import ExecutionBlocker
except Exception:  # pragma: no cover - used outside a full ComfyUI runtime.

    class ExecutionBlocker:
        """Minimal fallback so local tests can run without ComfyUI installed."""

        def __init__(self, message):
            self.message = message


from .common import any_type, bool_input, custom_input


class BooleanOutputSwitch:
    """Route one payload to the true or false output using a boolean."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "switch_output"
    RETURN_TYPES = (any_type, any_type, "INT", "STRING")
    RETURN_NAMES = ("on_true", "on_false", "index_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input": custom_input(any_type),
                "boolean": bool_input(False),
            }
        }

    def switch_output(self, input=None, boolean=False):
        if not isinstance(boolean, bool):
            message = "boolean must be a boolean."
            return (ExecutionBlocker(message), ExecutionBlocker(message), ExecutionBlocker(message), message)

        blocked = ExecutionBlocker(None)
        if boolean:
            return (input, blocked, 0, "")
        return (blocked, input, 1, "")
