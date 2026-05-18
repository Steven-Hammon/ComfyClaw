from __future__ import annotations

from pathlib import Path

from tool_settings import truncate_text


ACTION_ARGUMENTS = {
    "extract": {"file", "out"},
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

        parsed_args[key[2:]] = raw_args[index + 1]
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


def resolve_input_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() / path).resolve()


def resolve_output_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path.resolve()

    resolved = (Path.cwd() / path).resolve()
    cwd = Path.cwd().resolve()
    resolved.relative_to(cwd)
    return resolved

def save_text(text: str, output_value: str) -> str:
    output_path = resolve_output_path(output_value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return f"Saved to {output_path}"


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    if action != "extract":
        return f"Error: unknown action {action}"

    error = validate_args(parsed_args, {"file", "out"}, {"file"})
    if error:
        return error

    try:
        import fitz

        input_path = resolve_input_path(parsed_args["file"])
        document = fitz.open(input_path)
        parts: list[str] = []

        for page in document:
            parts.append(page.get_text("text"))

        text = "\n".join(parts)

        if "out" in parsed_args:
            return save_text(text, parsed_args["out"])

        return truncate_text(text)
    except Exception as exc:
        return f"Error: {exc}"
