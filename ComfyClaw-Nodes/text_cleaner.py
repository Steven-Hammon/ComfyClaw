"""Text_Cleaner node."""

from __future__ import annotations

from .common import bool_input, decode_common_escapes, join_messages, require_string, string_input


class TextCleaner:
    """Trim text to a section bounded by start and end markers."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "clean_text"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_input": string_input(""),
                "start_text": string_input("", multiline=False),
                "end_text": string_input("", multiline=False),
                "include_start_end": bool_input(True, label_on="include", label_off="exclude"),
            }
        }

    def clean_text(self, string_input, start_text, end_text, include_start_end=True):
        checked_input, input_error = require_string(string_input, "string_input")
        checked_start, start_error = require_string(start_text, "start_text")
        checked_end, end_error = require_string(end_text, "end_text")
        if input_error or start_error or end_error:
            return ("", join_messages(input_error, start_error, end_error))
        if not isinstance(include_start_end, bool):
            return ("", "include_start_end must be a boolean.")

        checked_start = decode_common_escapes(checked_start)
        checked_end = decode_common_escapes(checked_end)

        if checked_input == "":
            return ("", "string_input was empty.")

        errors: list[str] = []
        start_index = checked_input.find(checked_start) if checked_start else 0
        end_index = checked_input.rfind(checked_end) if checked_end else len(checked_input)
        start_found = not checked_start or start_index != -1
        end_found = not checked_end or end_index != -1

        if not start_found:
            errors.append("start_text was not found.")
            start_index = 0
        if not end_found:
            errors.append("end_text was not found.")
            end_index = len(checked_input)

        end_exclusive_index = end_index + len(checked_end) if checked_end and end_found else end_index

        if checked_start and checked_end and start_found and end_found and start_index > end_exclusive_index:
            errors.append("start_text appeared after end_text; using the full input with repaired boundaries.")
            extracted = checked_input
        else:
            if include_start_end:
                extracted = checked_input[start_index:end_exclusive_index]
            else:
                inner_start_index = start_index + len(checked_start) if checked_start and start_found else start_index
                inner_end_index = end_index if checked_end and end_found else end_exclusive_index
                extracted = checked_input[inner_start_index:inner_end_index]

        return (extracted, "; ".join(errors))
