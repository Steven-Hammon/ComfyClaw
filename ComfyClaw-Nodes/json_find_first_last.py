"""JSON_Find_First_Last node."""

from __future__ import annotations

from .common import combo_input, match_text, parse_json_string, require_string, string_input, to_plain_text


MATCH_TYPE_MAP = {
    "Contains": "contains",
    "Starts With": "starts_with",
    "Ends With": "ends_with",
    "Equals": "equals",
}


class JSONFindFirstLast:
    """Find the first or last matching root key/value pair in an ordered JSON object."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "find_pair"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("Output_key", "Output_value", "Error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": string_input(""),
                "Find_Mode": combo_input(["First", "Last"], default="First"),
                "Search_In": combo_input(["Key", "Value"], default="Value"),
                "Condition": combo_input(["Does", "Doesn't"], default="Does"),
                "Match_Type": combo_input(["Contains", "Starts With", "Ends With", "Equals"], default="Contains"),
                "Rule_Text": string_input(""),
            }
        }

    def find_pair(
        self,
        input_text,
        Find_Mode="First",
        Search_In="Value",
        Condition="Does",
        Match_Type="Contains",
        Rule_Text="",
    ):
        checked_json, json_error = require_string(input_text, "input_text")
        checked_rule, rule_error = require_string(Rule_Text, "Rule_Text")
        if json_error or rule_error:
            return ("", "", "; ".join(error for error in (json_error, rule_error) if error))

        if Find_Mode not in {"First", "Last"}:
            return ("", "", "Find_Mode must be First or Last.")
        if Search_In not in {"Key", "Value"}:
            return ("", "", "Search_In must be Key or Value.")
        if Condition not in {"Does", "Doesn't"}:
            return ("", "", "Condition must be Does or Doesn't.")
        if Match_Type not in MATCH_TYPE_MAP:
            return ("", "", "Match_Type must be Contains, Starts With, Ends With, or Equals.")

        try:
            data = parse_json_string(checked_json)
        except Exception as exc:
            return ("", "", f"Invalid JSON input: {exc}")

        if not isinstance(data, dict):
            return ("", "", "Root JSON is not a JSON object.")

        entries = list(data.items())
        if Find_Mode == "Last":
            entries.reverse()

        match_type = MATCH_TYPE_MAP[Match_Type]
        for key, value in entries:
            candidate = key if Search_In == "Key" else to_plain_text(value)
            does_match = match_text(candidate, checked_rule, match_type)
            if Condition == "Doesn't":
                does_match = not does_match
            if does_match:
                return (key, to_plain_text(value), "")

        return ("", "", "No matching root key/value pair found.")
