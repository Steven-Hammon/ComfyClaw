from __future__ import annotations

import datetime
import shutil
import sys
from pathlib import Path


ACTION_ARGUMENTS = {
    "list": {"path"},
    "tree": {"path", "depth"},
}


def parse_command(args: list[str]):
    if not args:
        return None, None, "Error: missing action"

    action = args[0]
    parsed_args: dict[str, str] = {}
    raw_args = args[1:]
    index = 0

    while index < len(raw_args):
        key = raw_args[index]
        if not key.startswith("--"):
            return None, None, f"Error: invalid argument {key}"
        if index + 1 >= len(raw_args):
            return None, None, f"Error: missing value for {key}"

        clean_key = key[2:].lower().replace("-", "_")
        parsed_args[clean_key] = raw_args[index + 1]
        index += 2

    return action, parsed_args, None


def validate_args(parsed_args: dict[str, str], allowed: set[str], required: set[str]):
    for key in parsed_args:
        if key not in allowed:
            return f"Error: unknown argument --{key}"

    for key in required:
        if key not in parsed_args:
            return f"Error: missing required argument --{key}"

    return None


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() / path).resolve()


def format_time(timestamp: float) -> str:
    return datetime.datetime.fromtimestamp(timestamp).strftime("%m/%d/%Y  %I:%M %p")


def format_bytes(value: int) -> str:
    return f"{value:,}"


def list_directory(path: Path) -> str:
    if not path.exists():
        return f"Error: path not found: {path}"
    if not path.is_dir():
        return f"Error: path is not a directory: {path}"

    entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    lines = [f" Directory of {path}", ""]
    file_count = 0
    dir_count = 0
    total_size = 0

    for entry in entries:
        try:
            stat = entry.stat()
        except OSError:
            continue

        stamp = format_time(stat.st_mtime)
        if entry.is_dir():
            dir_count += 1
            lines.append(f"{stamp}    <DIR>          {entry.name}")
        else:
            file_count += 1
            total_size += stat.st_size
            lines.append(f"{stamp}    {format_bytes(stat.st_size):>14} {entry.name}")

    lines.append("")
    lines.append(f"{file_count:>16} File(s) {format_bytes(total_size):>14} bytes")
    lines.append(f"{dir_count:>16} Dir(s)  {format_bytes(shutil.disk_usage(path).free):>14} bytes free")
    return "\n".join(lines)


def get_depth(parsed_args: dict[str, str]) -> int:
    if "depth" not in parsed_args:
        return 3

    try:
        depth = int(parsed_args["depth"])
    except ValueError:
        raise ValueError("depth must be an integer")

    if depth < 1:
        raise ValueError("depth must be 1 or greater")

    return depth


def append_tree(lines: list[str], path: Path, prefix: str, current_depth: int, max_depth: int) -> None:
    if current_depth >= max_depth:
        return

    try:
        entries = sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
    except OSError as exc:
        lines.append(f"{prefix}[Error: {exc}]")
        return

    for index, entry in enumerate(entries):
        is_last = index == len(entries) - 1
        branch = "+-- " if is_last else "|-- "
        lines.append(f"{prefix}{branch}{entry.name}")

        if entry.is_dir():
            extension = "    " if is_last else "|   "
            append_tree(lines, entry, prefix + extension, current_depth + 1, max_depth)


def tree_directory(path: Path, depth: int) -> str:
    if not path.exists():
        return f"Error: path not found: {path}"
    if not path.is_dir():
        return f"Error: path is not a directory: {path}"

    lines = [str(path)]
    append_tree(lines, path, "", 0, depth)
    return "\n".join(lines)


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    try:
        if action == "list":
            error = validate_args(parsed_args, {"path"}, {"path"})
            if error:
                return error

            return list_directory(resolve_path(parsed_args["path"]))

        if action == "tree":
            error = validate_args(parsed_args, {"path", "depth"}, {"path"})
            if error:
                return error

            return tree_directory(resolve_path(parsed_args["path"]), get_depth(parsed_args))

        return f"Error: unknown action {action}"
    except Exception as exc:
        return f"Error: {exc}"


if __name__ == "__main__":
    print(run(sys.argv[1:]))
