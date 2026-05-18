from __future__ import annotations

from pathlib import Path

from tool_settings import truncate_text


ACTION_ARGUMENTS = {
    "internet": {"query", "out", "results"},
    "text": {"query", "out", "results"},
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


def format_results(results) -> str:
    blocks: list[str] = []

    for item in results:
        title = item.get("title", "").strip()
        url = item.get("href", "").strip()
        body = item.get("body", "").strip()
        blocks.append("\n".join(part for part in [title, url, body] if part))

    return "\n\n".join(blocks).strip()


def run(args: list[str]) -> str:
    action, parsed_args, error = parse_command(args)
    if error:
        return error

    if action not in {"internet", "text"}:
        return f"Error: unknown action {action}"

    error = validate_args(parsed_args, {"query", "out", "results"}, {"query"})
    if error:
        return error

    try:
        try:
            result_count = int(parsed_args.get("results", "10"))
        except ValueError:
            return "Error: results must be an integer"

        if result_count < 1:
            return "Error: results must be 1 or greater"

        from ddgs import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(parsed_args["query"], max_results=result_count))

        if not results:
            text = "No results"
        else:
            text = format_results(results)

        if "out" in parsed_args:
            return save_text(text, parsed_args["out"])

        return truncate_text(text)
    except Exception as exc:
        return f"Error: {exc}"
