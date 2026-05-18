"""Route node."""

from __future__ import annotations

from .boolean_output_switch import ExecutionBlocker
from .common import MAX_DYNAMIC_SLOTS, combo_input, flexible_optional_inputs, int_input, match_text, require_string, string_input


class Route:
    """Route a string to one or more matching branch outputs."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "route"
    RETURN_TYPES = tuple(["STRING"] * MAX_DYNAMIC_SLOTS + ["INT", "STRING"])
    RETURN_NAMES = tuple([f"branch_{index}" for index in range(1, MAX_DYNAMIC_SLOTS + 1)] + ["index_output", "error_string"])

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_string": string_input(""),
                "default_branch": int_input(0, min=0, max=MAX_DYNAMIC_SLOTS),
                "block_mode": combo_input(["Empty", "block"], default="Empty"),
            },
            "optional": flexible_optional_inputs(),
        }

    def route(self, input_string="", default_branch=0, block_mode="Empty", **kwargs):
        checked_input, input_error = require_string(input_string, "input_string")
        if input_error:
            return tuple([""] * MAX_DYNAMIC_SLOTS + [0, input_error])
        if not isinstance(default_branch, int):
            return tuple([""] * MAX_DYNAMIC_SLOTS + [0, "default_branch must be an integer."])
        if block_mode not in {"Empty", "block"}:
            return tuple([""] * MAX_DYNAMIC_SLOTS + [0, "block_mode must be Empty or block."])

        inactive_output = ExecutionBlocker(None) if block_mode == "block" else ""
        outputs = [inactive_output] * MAX_DYNAMIC_SLOTS
        index_output = 0
        for index in range(1, MAX_DYNAMIC_SLOTS + 1):
            branch_rule = kwargs.get(f"branch_{index}_rule", "")
            branch_type = kwargs.get(f"branch_{index}_type", "contains")
            if branch_rule in (None, ""):
                continue
            if not isinstance(branch_rule, str):
                return tuple([""] * MAX_DYNAMIC_SLOTS + [0, f"branch_{index}_rule must be a string."])
            if not isinstance(branch_type, str):
                return tuple([""] * MAX_DYNAMIC_SLOTS + [0, f"branch_{index}_type must be a string."])
            if match_text(checked_input, branch_rule, branch_type):
                outputs[index - 1] = checked_input
                if index_output == 0:
                    index_output = index

        if index_output == 0 and 1 <= default_branch <= MAX_DYNAMIC_SLOTS:
            outputs[default_branch - 1] = checked_input
            index_output = default_branch

        return tuple(outputs + [index_output, ""])
