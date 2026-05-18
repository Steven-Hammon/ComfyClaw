from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


ACTION_ARGUMENTS = {
    "overwrite": {"path", "content", "encoding", "create_if_missing", "backup"},
    "append": {"path", "content", "encoding", "create_if_missing"},
    "prepend": {"path", "content", "encoding", "create_if_missing"},
    "insert_at_line": {"path", "content", "line", "encoding", "backup"},
    "find_and_replace": {"path", "find", "replace", "encoding", "use_regex", "replace_all", "backup"},
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


def get_int(parsed_args: dict[str, str], key: str) -> int:
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


def backup_file(path: Path) -> Path | None:
    if not path.exists() or not path.is_file():
        return None

    backup_path = Path(str(path) + ".bak")
    shutil.copy2(path, backup_path)
    return backup_path


def ensure_can_create(path: Path, create_if_missing: bool) -> None:
    if path.exists():
        if not path.is_file():
            raise IsADirectoryError(f"path is not a file: {path}")
        return

    if not create_if_missing:
        raise FileNotFoundError(f"file not found: {path}")

    path.parent.mkdir(parents=True, exist_ok=True)


def read_existing(path: Path, encoding: str, create_if_missing: bool) -> str:
    ensure_can_create(path, create_if_missing)
    if not path.exists():
        return ""
    return path.read_text(encoding=encoding)


def write_text(path: Path, content: str, encoding: str) -> None:
    path.write_text(content, encoding=encoding)


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    try:
        if action == "overwrite":
            error = validate_args(
                parsed_args,
                {"path", "content", "encoding", "create_if_missing", "backup"},
                {"path", "content"},
            )
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            content = parsed_args["content"]
            encoding = parsed_args.get("encoding", "utf-8")
            create_if_missing = get_bool(parsed_args, "create_if_missing", True)
            backup = get_bool(parsed_args, "backup", False)
            ensure_can_create(path, create_if_missing)
            backup_path = backup_file(path) if backup else None
            write_text(path, content, encoding)

            message = f"Wrote {len(content)} characters to {path}"
            if backup_path:
                message += f"\nBackup saved to {backup_path}"
            return message

        if action == "append":
            error = validate_args(
                parsed_args,
                {"path", "content", "encoding", "create_if_missing"},
                {"path", "content"},
            )
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            content = parsed_args["content"]
            encoding = parsed_args.get("encoding", "utf-8")
            create_if_missing = get_bool(parsed_args, "create_if_missing", True)
            ensure_can_create(path, create_if_missing)

            with path.open("a", encoding=encoding) as file:
                file.write(content)

            return f"Appended {len(content)} characters to {path}"

        if action == "prepend":
            error = validate_args(
                parsed_args,
                {"path", "content", "encoding", "create_if_missing"},
                {"path", "content"},
            )
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            content = parsed_args["content"]
            encoding = parsed_args.get("encoding", "utf-8")
            create_if_missing = get_bool(parsed_args, "create_if_missing", True)
            existing = read_existing(path, encoding, create_if_missing)
            write_text(path, content + existing, encoding)
            return f"Prepended {len(content)} characters to {path}"

        if action == "insert_at_line":
            error = validate_args(
                parsed_args,
                {"path", "content", "line", "encoding", "backup"},
                {"path", "content", "line"},
            )
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            if not path.exists():
                raise FileNotFoundError(f"file not found: {path}")
            if not path.is_file():
                raise IsADirectoryError(f"path is not a file: {path}")

            content = parsed_args["content"]
            line = get_int(parsed_args, "line")
            encoding = parsed_args.get("encoding", "utf-8")
            backup = get_bool(parsed_args, "backup", False)
            existing = path.read_text(encoding=encoding)
            lines = existing.splitlines(keepends=True)

            if line > len(lines) + 1:
                return f"ERROR: line must be between 1 and {len(lines) + 1}"

            backup_path = backup_file(path) if backup else None
            index = line - 1
            new_text = "".join(lines[:index]) + content + "".join(lines[index:])
            write_text(path, new_text, encoding)

            message = f"Inserted {len(content)} characters at line {line} in {path}"
            if backup_path:
                message += f"\nBackup saved to {backup_path}"
            return message

        if action == "find_and_replace":
            error = validate_args(
                parsed_args,
                {"path", "find", "replace", "encoding", "use_regex", "replace_all", "backup"},
                {"path", "find", "replace"},
            )
            if error:
                return error

            path = resolve_path(parsed_args["path"])
            if not path.exists():
                raise FileNotFoundError(f"file not found: {path}")
            if not path.is_file():
                raise IsADirectoryError(f"path is not a file: {path}")

            find = parsed_args["find"]
            replace = parsed_args["replace"]
            if find == "":
                return "ERROR: find must not be empty"

            encoding = parsed_args.get("encoding", "utf-8")
            use_regex = get_bool(parsed_args, "use_regex", False)
            replace_all = get_bool(parsed_args, "replace_all", True)
            backup = get_bool(parsed_args, "backup", False)
            original = path.read_text(encoding=encoding)

            if use_regex:
                count = 0 if replace_all else 1
                new_text, replacements = re.subn(find, replace, original, count=count)
            else:
                if replace_all:
                    replacements = original.count(find)
                    new_text = original.replace(find, replace)
                else:
                    position = original.find(find)
                    replacements = 0 if position == -1 else 1
                    if replacements:
                        new_text = original[:position] + replace + original[position + len(find) :]
                    else:
                        new_text = original

            backup_path = None
            if replacements:
                backup_path = backup_file(path) if backup else None
                write_text(path, new_text, encoding)

            message = f"Replacements made: {replacements}"
            if backup_path:
                message += f"\nBackup saved to {backup_path}"
            return message

        return f"ERROR: unknown action {action}"
    except Exception as exc:
        return f"ERROR: {exc}"


if __name__ == "__main__":
    print(run(sys.argv[1:]))
