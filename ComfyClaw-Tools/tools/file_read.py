from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path


ACTION_ARGUMENTS = {
    "full": {"path", "encoding", "include_line_numbers"},
    "slice": {"path", "start_line", "end_line", "encoding", "include_line_numbers"},
    "head": {"path", "lines", "encoding", "include_line_numbers"},
    "tail": {"path", "lines", "encoding", "include_line_numbers"},
    "search": {"path", "pattern", "encoding", "include_line_numbers", "use_regex"},
    "metadata": {"path"},
}


def parse_command(args: list[str]):
    if not args:
        return None, None, "ERROR: missing action"

    action = args[0]
    parsed_args: dict[str, str] = {}
    raw_args = args[1:]
    index = 0

    while index < len(raw_args):
        key = raw_args[index]
        if not key.startswith("--"):
            return None, None, f"ERROR: invalid argument {key}"
        if index + 1 >= len(raw_args):
            return None, None, f"ERROR: missing value for {key}"

        clean_key = key[2:].lower().replace("-", "_")
        parsed_args[clean_key] = raw_args[index + 1]
        index += 2

    return action, parsed_args, None


def validate_args(parsed_args: dict[str, str], allowed: set[str], required: set[str]):
    for key in parsed_args:
        if key not in allowed:
            return f"ERROR: unknown argument --{key}"

    for key in required:
        if key not in parsed_args:
            return f"ERROR: missing required argument --{key}"

    return None


def get_bool(parsed_args: dict[str, str], key: str, default: bool) -> bool:
    if key not in parsed_args:
        return default

    value = parsed_args[key].strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{key} must be true or false")


def get_int(parsed_args: dict[str, str], key: str, default: int | None = None) -> int:
    if key not in parsed_args:
        if default is None:
            raise ValueError(f"missing required argument --{key}")
        return default

    try:
        value = int(parsed_args[key])
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc

    if value < 1:
        raise ValueError(f"{key} must be 1 or greater")

    return value


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def read_text(path: Path, encoding: str) -> str:
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"path is not a file: {path}")
    return path.read_text(encoding=encoding)


def numbered_lines(lines: list[str], start_line: int) -> str:
    if not lines:
        return ""

    end_line = start_line + len(lines) - 1
    width = len(str(end_line))
    numbered = [
        f"{line_number:>{width}}\t{line}"
        for line_number, line in enumerate(lines, start=start_line)
    ]
    return "\n".join(numbered)


def maybe_number_lines(lines: list[str], start_line: int, include_line_numbers: bool) -> str:
    if include_line_numbers:
        return numbered_lines(lines, start_line)
    return "\n".join(lines)


def detect_encoding(path: Path) -> str:
    try:
        import chardet

        raw = path.read_bytes()
        result = chardet.detect(raw)
        encoding = result.get("encoding")
        if encoding:
            return str(encoding)
    except Exception:
        pass

    return "utf-8"


def line_count(path: Path, encoding: str) -> int:
    try:
        text = path.read_text(encoding=encoding, errors="replace")
    except LookupError:
        text = path.read_text(encoding="utf-8", errors="replace")
    return len(text.splitlines())


def metadata(path: Path) -> str:
    exists = path.exists()
    lines = [f"exists: {str(exists).lower()}", f"path: {path}"]

    if not exists:
        lines.extend(
            [
                "size_bytes: 0",
                "total_lines: 0",
                "last_modified: ",
                "detected_encoding: utf-8",
            ]
        )
        return "\n".join(lines)

    if not path.is_file():
        lines.extend(
            [
                "size_bytes: 0",
                "total_lines: 0",
                "last_modified: ",
                "detected_encoding: utf-8",
                "note: path is not a file",
            ]
        )
        return "\n".join(lines)

    stat = path.stat()
    detected = detect_encoding(path)
    modified = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(sep=" ", timespec="seconds")

    lines.extend(
        [
            f"size_bytes: {stat.st_size}",
            f"total_lines: {line_count(path, detected)}",
            f"last_modified: {modified}",
            f"detected_encoding: {detected}",
        ]
    )
    return "\n".join(lines)


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    try:
        if action == "full":
            error = validate_args(parsed_args, {"path", "encoding", "include_line_numbers"}, {"path"})
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            encoding = parsed_args.get("encoding", "utf-8")
            include_line_numbers = get_bool(parsed_args, "include_line_numbers", False)
            text = read_text(path, encoding)
            if include_line_numbers:
                return numbered_lines(text.splitlines(), 1)
            return text

        if action == "slice":
            error = validate_args(
                parsed_args,
                {"path", "start_line", "end_line", "encoding", "include_line_numbers"},
                {"path", "start_line", "end_line"},
            )
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            encoding = parsed_args.get("encoding", "utf-8")
            start_line = get_int(parsed_args, "start_line")
            end_line = get_int(parsed_args, "end_line")
            if end_line < start_line:
                return "ERROR: end_line must be greater than or equal to start_line"

            include_line_numbers = get_bool(parsed_args, "include_line_numbers", False)
            all_lines = read_text(path, encoding).splitlines()
            selected = all_lines[start_line - 1 : end_line]
            return maybe_number_lines(selected, start_line, include_line_numbers)

        if action == "head":
            error = validate_args(parsed_args, {"path", "lines", "encoding", "include_line_numbers"}, {"path"})
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            encoding = parsed_args.get("encoding", "utf-8")
            count = get_int(parsed_args, "lines", 20)
            include_line_numbers = get_bool(parsed_args, "include_line_numbers", False)
            selected = read_text(path, encoding).splitlines()[:count]
            return maybe_number_lines(selected, 1, include_line_numbers)

        if action == "tail":
            error = validate_args(parsed_args, {"path", "lines", "encoding", "include_line_numbers"}, {"path"})
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            encoding = parsed_args.get("encoding", "utf-8")
            count = get_int(parsed_args, "lines", 20)
            include_line_numbers = get_bool(parsed_args, "include_line_numbers", False)
            all_lines = read_text(path, encoding).splitlines()
            selected = all_lines[-count:]
            start_line = max(1, len(all_lines) - len(selected) + 1)
            return maybe_number_lines(selected, start_line, include_line_numbers)

        if action == "search":
            error = validate_args(
                parsed_args,
                {"path", "pattern", "encoding", "include_line_numbers", "use_regex"},
                {"path", "pattern"},
            )
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            encoding = parsed_args.get("encoding", "utf-8")
            pattern = parsed_args["pattern"]
            include_line_numbers = get_bool(parsed_args, "include_line_numbers", True)
            use_regex = get_bool(parsed_args, "use_regex", False)
            all_lines = read_text(path, encoding).splitlines()
            matches: list[tuple[int, str]] = []

            if use_regex:
                regex = re.compile(pattern)
                for line_number, line in enumerate(all_lines, start=1):
                    if regex.search(line):
                        matches.append((line_number, line))
            else:
                for line_number, line in enumerate(all_lines, start=1):
                    if pattern in line:
                        matches.append((line_number, line))

            if not matches:
                return "No matches found"

            if include_line_numbers:
                width = len(str(matches[-1][0]))
                return "\n".join(f"{line_number:>{width}}\t{line}" for line_number, line in matches)

            return "\n".join(line for _, line in matches)

        if action == "metadata":
            error = validate_args(parsed_args, {"path"}, {"path"})
            if error:
                return error

            return metadata(resolve_path(parsed_args["path"]))

        return f"ERROR: unknown action {action}"
    except Exception as exc:
        return f"ERROR: {exc}"


if __name__ == "__main__":
    print(run(sys.argv[1:]))
