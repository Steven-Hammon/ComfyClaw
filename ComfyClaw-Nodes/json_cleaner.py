"""JSON_Cleaner node."""

from __future__ import annotations

import json
import re
from typing import Any

from .common import serialize_json, string_input


PYTHON_LITERAL_REPLACEMENTS = {"True": "true", "False": "false", "None": "null"}
UNQUOTED_KEY_PATTERN = re.compile(r'(?P<prefix>[{,]\s*)(?P<key>[A-Za-z_][A-Za-z0-9_-]*)(?P<suffix>\s*:)')


def _dedupe_actions(actions: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for action in actions:
        if action in seen:
            continue
        seen.add(action)
        deduped.append(action)
    return deduped


def _repair_message(actions: list[str]) -> str:
    if not actions:
        return ""
    return "JSON repaired: " + "; ".join(_dedupe_actions(actions)) + "."


def _try_parse(candidate: str) -> tuple[bool, Any, json.JSONDecodeError | None]:
    try:
        return True, json.loads(candidate), None
    except json.JSONDecodeError as exc:
        return False, None, exc


def _strip_code_fences(text: str) -> tuple[str, bool]:
    stripped = re.sub(r"^\s*```(?:json|JSON)?\s*", "", text)
    stripped = re.sub(r"\s*```\s*$", "", stripped)
    stripped = stripped.replace("```json", "").replace("```JSON", "").replace("```", "")
    return stripped, stripped != text


def _extract_json_candidate(text: str) -> str:
    starts = [index for index in (text.find("{"), text.find("[")) if index != -1]
    if not starts:
        return ""
    start = min(starts)
    stack: list[str] = []
    quote = ""
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue

        if char in {'"', "'"}:
            quote = char
        elif char in "{[":
            stack.append(char)
        elif char in "}]":
            if stack and ((stack[-1] == "{" and char == "}") or (stack[-1] == "[" and char == "]")):
                stack.pop()
                if not stack:
                    return text[start : index + 1]
            elif not stack:
                return text[start:index]

    return text[start:].strip()


def _remove_comments(text: str) -> tuple[str, bool]:
    output = []
    quote = ""
    escaped = False
    changed = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if quote:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue

        if char in {'"', "'"}:
            quote = char
            output.append(char)
            index += 1
            continue

        if char == "/" and next_char == "/":
            changed = True
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue

        if char == "/" and next_char == "*":
            changed = True
            index += 2
            while index + 1 < len(text) and not (text[index] == "*" and text[index + 1] == "/"):
                index += 1
            index = min(index + 2, len(text))
            continue

        output.append(char)
        index += 1

    return "".join(output), changed


def _replace_python_literals(text: str) -> tuple[str, bool]:
    output = []
    quote = ""
    escaped = False
    changed = False
    index = 0

    while index < len(text):
        char = text[index]

        if quote:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            index += 1
            continue

        if char in {'"', "'"}:
            quote = char
            output.append(char)
            index += 1
            continue

        if char.isalpha():
            end = index + 1
            while end < len(text) and (text[end].isalnum() or text[end] == "_"):
                end += 1
            word = text[index:end]
            replacement = PYTHON_LITERAL_REPLACEMENTS.get(word)
            if replacement is not None:
                output.append(replacement)
                changed = True
            else:
                output.append(word)
            index = end
            continue

        output.append(char)
        index += 1

    return "".join(output), changed


def _convert_single_quoted_strings(text: str) -> tuple[str, bool]:
    output = []
    quote = ""
    escaped = False
    changed = False
    index = 0

    while index < len(text):
        char = text[index]

        if quote == '"':
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quote = ""
            index += 1
            continue

        if char == '"':
            quote = '"'
            output.append(char)
            index += 1
            continue

        if char != "'":
            output.append(char)
            index += 1
            continue

        changed = True
        index += 1
        value = []
        while index < len(text):
            current = text[index]
            if current == "\\" and index + 1 < len(text):
                next_char = text[index + 1]
                if next_char in {"\\", "'"}:
                    value.append(next_char)
                else:
                    value.append("\\")
                    value.append(next_char)
                index += 2
                continue
            if current == "'":
                index += 1
                break
            value.append(current)
            index += 1
        output.append(json.dumps("".join(value), ensure_ascii=False))

    return "".join(output), changed


def _escape_invalid_backslashes(text: str) -> tuple[str, bool]:
    output = []
    in_string = False
    changed = False
    index = 0
    valid_escapes = {'"', "\\", "/", "b", "f", "n", "r", "t"}

    while index < len(text):
        char = text[index]
        if not in_string:
            output.append(char)
            if char == '"':
                in_string = True
            index += 1
            continue

        if char == '"':
            output.append(char)
            in_string = False
            index += 1
            continue

        if char != "\\":
            output.append(char)
            index += 1
            continue

        next_char = text[index + 1] if index + 1 < len(text) else ""
        if next_char in valid_escapes:
            output.append(char)
        elif next_char == "u" and re.match(r"^[0-9a-fA-F]{4}", text[index + 2 : index + 6]):
            output.append(char)
        else:
            output.append("\\\\")
            changed = True
        index += 1

    return "".join(output), changed


def _escape_newlines_in_strings(text: str) -> tuple[str, bool]:
    output = []
    in_string = False
    escaped = False
    changed = False

    for char in text:
        if in_string:
            if escaped:
                output.append(char)
                escaped = False
            elif char == "\\":
                output.append(char)
                escaped = True
            elif char == '"':
                output.append(char)
                in_string = False
            elif char == "\n":
                output.append("\\n")
                changed = True
            elif char == "\r":
                output.append("\\r")
                changed = True
            else:
                output.append(char)
            continue

        output.append(char)
        if char == '"':
            in_string = True

    return "".join(output), changed


def _quote_unquoted_keys(text: str) -> tuple[str, bool]:
    changed = False
    previous = text
    while True:
        updated = UNQUOTED_KEY_PATTERN.sub(r'\g<prefix>"\g<key>"\g<suffix>', previous)
        if updated == previous:
            return updated, changed
        changed = True
        previous = updated


def _add_missing_commas(text: str) -> tuple[str, bool]:
    lines = text.splitlines()
    fixed_lines: list[str] = []
    changed = False
    value_end_pattern = re.compile(r'(?:["}\]\d]|true|false|null)\s*$')
    next_value_pattern = re.compile(r'\s*(?:"[^"]+"\s*:|[A-Za-z_][A-Za-z0-9_-]*\s*:|[{\["\d-]|true|false|null)')

    for index, line in enumerate(lines):
        stripped = line.rstrip()
        fixed_lines.append(stripped)
        if index == len(lines) - 1:
            continue
        next_line = lines[index + 1].lstrip()
        if not stripped or not next_line:
            continue
        if stripped.endswith(("{", "[", ",", ":")):
            continue
        if next_line.startswith(("}", "]")):
            continue
        if value_end_pattern.search(stripped) and next_value_pattern.match(next_line):
            fixed_lines[-1] = stripped + ","
            changed = True

    return "\n".join(fixed_lines), changed


def _closing_for(opener: str) -> str:
    return "}" if opener == "{" else "]"


def _balance_brackets(text: str) -> tuple[str, bool]:
    output = []
    stack: list[str] = []
    in_string = False
    escaped = False
    changed = False

    for char in text:
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            output.append(char)
        elif char in "{[":
            stack.append(char)
            output.append(char)
        elif char in "}]":
            while stack and _closing_for(stack[-1]) != char:
                output.append(_closing_for(stack.pop()))
                changed = True
            if stack and _closing_for(stack[-1]) == char:
                stack.pop()
                output.append(char)
            else:
                changed = True
        else:
            output.append(char)

    if in_string:
        output.append('"')
        changed = True
    while stack:
        output.append(_closing_for(stack.pop()))
        changed = True

    return "".join(output), changed


def _repair_json(candidate: str) -> tuple[str, list[str]]:
    actions: list[str] = []
    repaired = candidate.strip()

    updated = repaired.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    if updated != repaired:
        actions.append("normalized smart quotes")
        repaired = updated

    updated, changed = _remove_comments(repaired)
    if changed:
        actions.append("removed comments")
        repaired = updated

    updated = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", repaired)
    if updated != repaired:
        actions.append("removed control characters")
        repaired = updated

    updated, changed = _convert_single_quoted_strings(repaired)
    if changed:
        actions.append("converted single-quoted strings")
        repaired = updated

    updated, changed = _escape_invalid_backslashes(repaired)
    if changed:
        actions.append("escaped invalid backslashes")
        repaired = updated

    updated, changed = _escape_newlines_in_strings(repaired)
    if changed:
        actions.append("escaped newlines inside strings")
        repaired = updated

    updated, changed = _replace_python_literals(repaired)
    if changed:
        actions.append("converted Python literals")
        repaired = updated

    updated, changed = _quote_unquoted_keys(repaired)
    if changed:
        actions.append("quoted unquoted keys")
        repaired = updated

    updated = re.sub(r",(\s*[}\]])", r"\1", repaired)
    if updated != repaired:
        actions.append("removed trailing commas")
        repaired = updated

    updated = re.sub(r",\s*,+", ",", repaired)
    if updated != repaired:
        actions.append("removed duplicate commas")
        repaired = updated

    updated, changed = _add_missing_commas(repaired)
    if changed:
        actions.append("added missing commas")
        repaired = updated

    updated = re.sub(r",(\s*[}\]])", r"\1", repaired)
    if updated != repaired:
        actions.append("removed trailing commas")
        repaired = updated

    updated, changed = _balance_brackets(repaired)
    if changed:
        actions.append("balanced brackets")
        repaired = updated

    updated = re.sub(r",(\s*[}\]])", r"\1", repaired)
    if updated != repaired:
        actions.append("removed trailing commas")
        repaired = updated

    return repaired, actions


def _trim_dangling_prefix(text: str) -> str:
    trimmed = text.rstrip()
    while trimmed and trimmed[-1] in ",:":
        trimmed = trimmed[:-1].rstrip()
    return trimmed


def _salvage_prefix(candidate: str, exc: json.JSONDecodeError | None) -> tuple[Any | None, list[str]]:
    stripped = candidate.strip()
    try:
        parsed, end = json.JSONDecoder().raw_decode(stripped)
        if stripped[end:].strip():
            return parsed, [f"salvaged valid prefix ending at character {end}"]
    except json.JSONDecodeError:
        pass

    search_limit = min(len(candidate), getattr(exc, "pos", len(candidate)) if exc is not None else len(candidate))
    prefix = candidate[:search_limit]
    cut_points = [match.start() for match in re.finditer(r"[,}\]\n]", prefix)]

    for cut_point in reversed(cut_points[-250:]):
        trimmed = _trim_dangling_prefix(candidate[:cut_point])
        if not trimmed:
            continue
        balanced, _ = _balance_brackets(trimmed)
        balanced = re.sub(r",(\s*[}\]])", r"\1", balanced)
        parse_ok, parsed, _ = _try_parse(balanced)
        if parse_ok:
            return parsed, [f"partially salvaged JSON before character {cut_point}"]

    return None, []


class JSONCleaner:
    """Extract and repair a JSON object from messy text."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "clean_json"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"string_input": string_input("")}}

    def clean_json(self, string_input):
        if not isinstance(string_input, str):
            try:
                return (serialize_json(string_input), "string_input was not a string; serialized input as JSON.")
            except TypeError:
                return ("{}", "string_input was not a string and could not be serialized; returned empty JSON object.")
        if string_input == "":
            return ("{}", "string_input was empty; returned empty JSON object.")

        prepared, stripped_fences = _strip_code_fences(string_input)
        parse_source = prepared.strip()
        parse_ok, parsed, _ = _try_parse(parse_source)
        if parse_ok:
            return (serialize_json(parsed), "JSON repaired: removed markdown code fences." if stripped_fences else "")

        candidate = _extract_json_candidate(prepared)
        if not candidate:
            return ("{}", "No JSON object or array was found in string_input; returned empty JSON object.")

        parse_ok, parsed, _ = _try_parse(candidate)
        if parse_ok:
            return (serialize_json(parsed), "")

        repaired, actions = _repair_json(candidate)
        parse_ok, parsed, repair_error = _try_parse(repaired)
        if parse_ok:
            return (serialize_json(parsed), _repair_message(actions))

        salvaged, salvage_actions = _salvage_prefix(repaired, repair_error)
        if salvaged is not None:
            return (serialize_json(salvaged), _repair_message(actions + salvage_actions))

        error_detail = f": {repair_error}" if repair_error else ""
        return ("{}", f"Could not repair JSON{error_detail}; returned empty JSON object.")
