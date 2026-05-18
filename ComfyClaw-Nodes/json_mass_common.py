"""Shared helpers for JSON mass editing nodes."""

from __future__ import annotations

from typing import Any, Iterable

PathPart = str | int
TargetRef = tuple[Any, PathPart, str]

OPERATIONS = ("add", "subtract", "multiply", "divide", "modulo", "power")
LOGIC_OPERATORS = (">", "<", ">=", "<=", "=")


def format_path(parts: Iterable[PathPart]) -> str:
    return ".".join(str(part) for part in parts)


def coerce_int(value: Any, path: str) -> tuple[int, str]:
    if isinstance(value, bool):
        return 0, f"Value at {path} must be an integer."
    if isinstance(value, int):
        return value, ""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return int(stripped), ""
            except ValueError:
                pass
    return 0, f"Value at {path} must be an integer."


def try_coerce_int(value: Any) -> tuple[int, bool]:
    value_int, error = coerce_int(value, "<value>")
    return value_int, error == ""


def validate_bounds(min_value: Any, max_value: Any) -> str:
    if not isinstance(min_value, int) or isinstance(min_value, bool):
        return "min must be an integer."
    if not isinstance(max_value, int) or isinstance(max_value, bool):
        return "max must be an integer."
    if min_value > max_value:
        return "min cannot be greater than max."
    return ""


def clamp(value: int, min_value: int, max_value: int) -> int:
    return min(max(value, min_value), max_value)


def apply_operation(left: int, operation: str, right: int) -> tuple[int, str]:
    if operation == "add":
        return left + right, ""
    if operation == "subtract":
        return left - right, ""
    if operation == "multiply":
        return left * right, ""
    if operation == "divide":
        if right == 0:
            return 0, "Cannot divide by zero."
        return int(left / right), ""
    if operation == "modulo":
        if right == 0:
            return 0, "Cannot modulo by zero."
        return left % right, ""
    if operation == "power":
        return left**right, ""
    return 0, f"operation must be one of: {', '.join(OPERATIONS)}."


def compare_value(left: int, logic: str, right: int) -> tuple[bool, str]:
    if logic == ">":
        return left > right, ""
    if logic == "<":
        return left < right, ""
    if logic == ">=":
        return left >= right, ""
    if logic == "<=":
        return left <= right, ""
    if logic == "=":
        return left == right, ""
    return False, f"logic must be one of: {', '.join(LOGIC_OPERATORS)}."


def _dict_key(data: dict[Any, Any], part: PathPart) -> PathPart | None:
    if part in data:
        return part
    if isinstance(part, int) and str(part) in data:
        return str(part)
    return None


def _get_child(data: Any, part: PathPart) -> tuple[Any, str]:
    if isinstance(data, dict):
        key = _dict_key(data, part)
        if key is None:
            return None, "missing"
        return data[key], ""
    if isinstance(data, list) and isinstance(part, int) and 0 <= part < len(data):
        return data[part], ""
    return None, "missing"


def get_target(data: Any, path_parts: list[PathPart]) -> tuple[Any, PathPart, str]:
    if not path_parts:
        return None, "", "path cannot be empty."
    parent = data
    for part in path_parts[:-1]:
        parent, error = _get_child(parent, part)
        if error:
            return None, "", error

    final_part = path_parts[-1]
    if isinstance(parent, dict):
        key = _dict_key(parent, final_part)
        if key is None:
            return None, "", "missing"
        return parent, key, ""
    if isinstance(parent, list) and isinstance(final_part, int) and 0 <= final_part < len(parent):
        return parent, final_part, ""
    return None, "", "missing"


def find_relative_targets(data: Any, path_parts: list[PathPart]) -> list[TargetRef]:
    targets: list[TargetRef] = []
    seen: set[tuple[int, str]] = set()

    def visit(value: Any, prefix: list[PathPart]) -> None:
        if not isinstance(value, (dict, list)):
            return

        parent, key, error = get_target(value, path_parts)
        if not error:
            target_path = prefix + path_parts
            seen_key = (id(parent), repr(key))
            if seen_key not in seen:
                seen.add(seen_key)
                targets.append((parent, key, format_path(target_path)))

        if isinstance(value, dict):
            for child_key, child_value in value.items():
                visit(child_value, prefix + [child_key])
        else:
            for index, child_value in enumerate(value):
                visit(child_value, prefix + [index])

    visit(data, [])
    return targets


def iter_leaf_paths(data: Any, prefix: tuple[PathPart, ...] = ()) -> Iterable[tuple[tuple[PathPart, ...], Any]]:
    if isinstance(data, dict):
        for key, value in data.items():
            yield from iter_leaf_paths(value, prefix + (key,))
        return
    if isinstance(data, list):
        for index, value in enumerate(data):
            yield from iter_leaf_paths(value, prefix + (index,))
        return
    yield prefix, data
