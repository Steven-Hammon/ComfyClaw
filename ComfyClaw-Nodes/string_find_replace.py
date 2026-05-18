"""String_Find_Replace node."""

from __future__ import annotations

from .common import decode_common_escapes, join_messages, require_string, string_input


class StringFindReplace:
    """Replace every instance of one substring with another."""

    CATEGORY = "ComfyClaw/Core"
    FUNCTION = "replace_text"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string_input": string_input(""),
                "find_text": string_input("", multiline=False),
                "replace_text": string_input("", multiline=False),
            }
        }

    def replace_text(self, string_input, find_text, replace_text):
        checked_input, input_error = require_string(string_input, "string_input")
        checked_find, find_error = require_string(find_text, "find_text")
        checked_replace, replace_error = require_string(replace_text, "replace_text")
        if input_error or find_error or replace_error:
            return ("", join_messages(input_error, find_error, replace_error))
        if checked_find == "":
            return ("", "find_text cannot be empty.")

        decoded_find = decode_common_escapes(checked_find)
        decoded_replace = decode_common_escapes(checked_replace)
        return (checked_input.replace(decoded_find, decoded_replace), "")
