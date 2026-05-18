"""Markdown/JSON conversion helpers for ComfyClaw nodes."""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Any


class PairObject(list):
    """JSON object represented as ordered key/value pairs, including duplicates."""


def _object_pairs_hook(pairs):
    return PairObject(pairs)


def parse_json_pairs(json_text: str) -> Any:
    return json.loads(json_text, object_pairs_hook=_object_pairs_hook)


def _is_object(value: Any) -> bool:
    return isinstance(value, (dict, PairObject))


def _iter_object(value: Any):
    if isinstance(value, PairObject):
        return value
    return value.items()


def _json_compatible(value: Any) -> Any:
    if isinstance(value, PairObject):
        return OrderedDict((str(key), _json_compatible(child)) for key, child in value)
    if isinstance(value, list):
        return [_json_compatible(child) for child in value]
    if isinstance(value, dict):
        return OrderedDict((str(key), _json_compatible(child)) for key, child in value.items())
    return value


def _serialize_json_pairs(value: Any, indent: int = 0) -> str:
    if isinstance(value, PairObject):
        if not value:
            return "{}"
        child_indent = indent + 2
        lines = []
        for key, child in value:
            rendered_key = json.dumps(str(key), ensure_ascii=False)
            rendered_child = _serialize_json_pairs(child, child_indent)
            lines.append(f"{' ' * child_indent}{rendered_key}: {rendered_child}")
        return "{\n" + ",\n".join(lines) + f"\n{' ' * indent}" + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        child_indent = indent + 2
        lines = [f"{' ' * child_indent}{_serialize_json_pairs(child, child_indent)}" for child in value]
        return "[\n" + ",\n".join(lines) + f"\n{' ' * indent}" + "]"
    if isinstance(value, dict):
        return _serialize_json_pairs(PairObject(list(value.items())), indent)
    return json.dumps(value, ensure_ascii=False)


def escaped_json_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)[1:-1]


def unescape_json_string(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == '"' and stripped[-1] == '"':
        parsed = json.loads(stripped)
    else:
        parsed = json.loads(f'"{value}"')
    if not isinstance(parsed, str):
        raise ValueError("escaped_json must decode to a string.")
    return parsed


def _scalar_to_markdown(value: Any) -> str:
    if isinstance(value, str):
        return escaped_json_string(value)
    return json.dumps(_json_compatible(value), ensure_ascii=False)


def _append_hash_spacing(lines: list[str], key: str) -> None:
    if key.startswith("#") and lines and lines[-1] != "":
        lines.append("")


def _render_markdown_object(value: Any, lines: list[str]) -> None:
    for raw_key, child in _iter_object(value):
        key = str(raw_key)
        _append_hash_spacing(lines, key)
        if _is_object(child):
            lines.append(key)
            _render_markdown_object(child, lines)
            continue

        rendered_child = _scalar_to_markdown(child)
        lines.append(key if rendered_child == "" else f"{key} {rendered_child}")


def json_pairs_to_markdown(data: Any) -> str:
    if not _is_object(data):
        raise ValueError("JSON root must be an object.")
    lines: list[str] = []
    _render_markdown_object(data, lines)
    return "\n".join(lines).rstrip() + ("\n" if lines else "")


def _heading_level(line: str) -> int:
    level = 0
    for char in line:
        if char != "#":
            break
        level += 1
    return level


def _ensure_container(entry: dict[str, Any]) -> PairObject:
    if entry["level"] == 0:
        return entry["container"]
    if entry["container"] is None:
        entry["container"] = PairObject()
        entry["parent"][entry["index"]] = (entry["key"], entry["container"])
    return entry["container"]


def _add_markdown_pair(container: PairObject, line: str) -> None:
    key, separator, value = line.partition(" ")
    if not separator:
        container.append((key, ""))
        return
    try:
        container.append((key, unescape_json_string(value)))
    except Exception:
        container.append((key, value))


def markdown_to_json_text(markdown_text: str) -> str:
    root = PairObject()
    stack: list[dict[str, Any]] = [{"level": 0, "key": None, "parent": None, "container": root}]

    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            raw_level = _heading_level(line)
            effective_level = min(raw_level, stack[-1]["level"] + 1)
            while stack[-1]["level"] >= effective_level:
                stack.pop()
            parent_container = _ensure_container(stack[-1])
            parent_container.append((line, ""))
            stack.append(
                {
                    "level": effective_level,
                    "key": line,
                    "parent": parent_container,
                    "index": len(parent_container) - 1,
                    "container": None,
                }
            )
            continue

        current_container = _ensure_container(stack[-1])
        _add_markdown_pair(current_container, line)

    return _serialize_json_pairs(root)
