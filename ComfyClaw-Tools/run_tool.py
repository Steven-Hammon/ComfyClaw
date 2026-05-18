from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TOOLS_DIR = ROOT / "tools"
USAGE = (
    "Usage: python run_tool.py <tool> <action> [--key value ...]\n"
    "   or: python run_tool.py <TOOL-ACTION>: \"--key value ...\""
)


def normalize_key(value: str) -> str:
    return value.strip().lstrip("-").lower().replace("-", "_")


def normalize_identifier(value: str) -> str:
    cleaned = value.strip().strip('"').strip("'").strip("`").rstrip(":").lower()
    cleaned = re.sub(r"[^a-z0-9]+", "_", cleaned)
    return cleaned.strip("_")


def get_action_arguments(module, action: str) -> dict[str, str] | None:
    action_arguments = getattr(module, "ACTION_ARGUMENTS", None)
    if not isinstance(action_arguments, dict):
        return None

    keys = action_arguments.get(action)
    if keys is None:
        return None

    return {normalize_key(key): str(key) for key in keys}


def find_tool_action(key: str) -> tuple[str, str] | None:
    cleaned = normalize_identifier(key)
    compact_cleaned = cleaned.replace("_", "")

    tool_names = sorted(
        (path.stem for path in TOOLS_DIR.glob("*.py") if not path.stem.startswith("_")),
        key=len,
        reverse=True,
    )

    matches: list[tuple[int, int, str, str]] = []
    for tool_name in tool_names:
        module, error = load_tool(tool_name)
        if error:
            continue

        action_arguments = getattr(module, "ACTION_ARGUMENTS", None)
        if not isinstance(action_arguments, dict):
            continue

        for action in action_arguments:
            candidate = normalize_identifier(f"{tool_name}_{action}")
            compact_candidate = candidate.replace("_", "")

            if cleaned == candidate:
                matches.append((0, -len(compact_candidate), tool_name, action))
            elif cleaned.startswith(candidate):
                matches.append((1, -len(compact_candidate), tool_name, action))
            elif candidate in cleaned:
                matches.append((2, -len(compact_candidate), tool_name, action))
            elif compact_candidate and compact_candidate in compact_cleaned:
                matches.append((3, -len(compact_candidate), tool_name, action))

    if matches:
        _, _, tool_name, action = sorted(matches)[0]
        return tool_name, action

    return None


def split_alias_key_and_value(args: list[str]) -> tuple[str, list[str]]:
    key = args[0]
    value_parts = args[1:]

    if ":" in key:
        key, inline_value = key.split(":", 1)
        if inline_value:
            value_parts = [inline_value, *value_parts]

    return key, value_parts


def tool_file_exists(tool_name: str) -> bool:
    return (TOOLS_DIR / f"{normalize_identifier(tool_name)}.py").is_file()


def parse_raw_argument_text(action: str, raw_text: str, known_keys: dict[str, str] | None) -> list[str]:
    if not raw_text.strip():
        return [action]

    if known_keys is None:
        return [action, *raw_text.split()]

    if not known_keys:
        return [action, raw_text] if raw_text.strip() else [action]

    variants: dict[str, str] = {}
    for normalized_key, canonical_key in known_keys.items():
        variants[canonical_key.lower()] = canonical_key
        variants[canonical_key.lower().replace("_", "-")] = canonical_key
        variants[normalized_key.lower()] = canonical_key
        variants[normalized_key.lower().replace("_", "-")] = canonical_key

    escaped = sorted((re.escape(key) for key in variants), key=len, reverse=True)
    pattern = re.compile(rf"(?<!\S)--({'|'.join(escaped)})(?=\s|$)", re.IGNORECASE)
    matches = list(pattern.finditer(raw_text))

    if not matches:
        return [action, raw_text]

    normalized = [action]
    for index, match in enumerate(matches):
        raw_key = match.group(1).lower()
        canonical_key = variants[raw_key]
        value_start = match.end()
        value_end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        value = raw_text[value_start:value_end].strip()
        normalized.extend([f"--{canonical_key}", value])

    return normalized


def build_alias_tool_args(module, action: str, value_parts: list[str]) -> list[str]:
    known_keys = get_action_arguments(module, action)
    raw_text = " ".join(part for part in value_parts if part is not None)
    return parse_raw_argument_text(action, raw_text, known_keys)


def stringify_argument_value(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def build_dict_tool_args(module, action: str, args_dict: dict) -> list[str]:
    known_keys = get_action_arguments(module, action)
    tool_args = [action]

    for raw_key, raw_value in args_dict.items():
        clean_key = normalize_key(str(raw_key))
        if known_keys is not None and clean_key in known_keys:
            canonical_key = known_keys[clean_key]
        else:
            canonical_key = clean_key

        tool_args.extend([f"--{canonical_key}", stringify_argument_value(raw_value)])

    return tool_args


def normalize_tool_args(module, args: list[str]) -> list[str]:
    if not args:
        return args

    action = args[0]
    known_keys = get_action_arguments(module, action)
    normalized = [action]
    index = 1

    while index < len(args):
        token = args[index]
        if not token.startswith("--"):
            normalized.append(token)
            index += 1
            continue

        raw_key = token[2:]
        key_lookup = normalize_key(raw_key)
        canonical_key = known_keys.get(key_lookup, raw_key.lower()) if known_keys is not None else raw_key.lower()
        index += 1

        value_parts: list[str] = []
        while index < len(args):
            next_token = args[index]
            if next_token.startswith("--"):
                next_key = normalize_key(next_token)
                if known_keys is None or next_key in known_keys:
                    break

            value_parts.append(next_token)
            index += 1

        normalized.extend([f"--{canonical_key}", " ".join(value_parts)])

    return normalized


def load_tool(tool_name: str):
    tool_path = TOOLS_DIR / f"{tool_name}.py"

    if tool_name.startswith("_") or not tool_path.is_file():
        return None, f"Tool not found: {tool_name}"

    try:
        spec = importlib.util.spec_from_file_location(f"tool_{tool_name}", tool_path)
        if spec is None or spec.loader is None:
            return None, f"Tool not found: {tool_name}"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, None
    except Exception as exc:
        return None, f"Error: {exc}"


def dispatch_tool(tool_name: str, tool_args: list[str]) -> str:
    module, error = load_tool(tool_name)
    if error:
        return error

    run = getattr(module, "run", None)
    if not callable(run):
        return f"Tool '{tool_name}' does not implement run()"

    try:
        result = run(tool_args)
    except Exception as exc:
        result = f"Error: {exc}"

    if result is None:
        result = ""

    return str(result)


def is_error_result(result_text: str) -> bool:
    lowered = result_text.lower()
    return (
        lowered.startswith("error:")
        or lowered.startswith("tool not found:")
        or lowered.endswith("does not implement run()")
    )


def build_cli_dispatch(argv: list[str]) -> tuple[str, list[str]] | tuple[None, None]:
    if len(argv) < 2:
        return None, None

    first_arg = argv[1]
    alias_key, alias_value_parts = split_alias_key_and_value(argv[1:])
    first_arg_has_colon = ":" in first_arg
    alias_match = None if not first_arg_has_colon and tool_file_exists(first_arg) else find_tool_action(alias_key)

    if alias_match:
        tool_name, action = alias_match
        module, error = load_tool(tool_name)
        if error:
            return tool_name, [f"__RUN_TOOL_ERROR__{error}"]
        return tool_name, build_alias_tool_args(module, action, alias_value_parts)

    if len(argv) < 3:
        return None, None

    tool_name = normalize_identifier(first_arg)
    module, error = load_tool(tool_name)
    if error:
        return tool_name, [f"__RUN_TOOL_ERROR__{error}"]

    return tool_name, normalize_tool_args(module, argv[2:])


def build_interactive_dispatch(message: dict) -> tuple[str, list[str]]:
    if set(message.keys()) != {"tool", "args"}:
        raise ValueError("message must contain exactly two fields: tool and args")

    tool_key = message["tool"]
    args_dict = message["args"]

    if not isinstance(tool_key, str) or not tool_key.strip():
        raise ValueError("tool must be a non-empty string")
    if not isinstance(args_dict, dict):
        raise ValueError("args must be a dictionary")

    alias_match = None if tool_file_exists(tool_key) else find_tool_action(tool_key)
    if alias_match:
        tool_name, action = alias_match
        module, error = load_tool(tool_name)
        if error:
            raise ValueError(error)
        return tool_name, build_dict_tool_args(module, action, args_dict)

    direct_tool = normalize_identifier(tool_key)
    if not tool_file_exists(direct_tool):
        raise ValueError(f"Tool not found: {tool_key}")

    if "action" not in args_dict:
        raise ValueError(f"missing action for direct tool {tool_key}")

    action = stringify_argument_value(args_dict["action"])
    action_args = {key: value for key, value in args_dict.items() if key != "action"}
    module, error = load_tool(direct_tool)
    if error:
        raise ValueError(error)

    return direct_tool, build_dict_tool_args(module, action, action_args)


def handle_interactive_line(line: str) -> str:
    if not line.strip():
        return "Error: empty input"

    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        return f"Error: malformed JSON: {exc}"

    if not isinstance(message, dict):
        return "Error: message must be a JSON object"

    try:
        tool_name, tool_args = build_interactive_dispatch(message)
    except Exception as exc:
        return f"Error: {exc}"

    return dispatch_tool(tool_name, tool_args)


def interactive_main() -> int:
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    for line in sys.stdin:
        result_text = handle_interactive_line(line.rstrip("\r\n"))
        sys.stdout.write(result_text)
        sys.stdout.flush()

    return 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--interactive":
        return interactive_main()

    tool_name, tool_args = build_cli_dispatch(sys.argv)
    if tool_name is None or tool_args is None:
        print(USAGE)
        return 1

    if tool_args and tool_args[0].startswith("__RUN_TOOL_ERROR__"):
        result_text = tool_args[0][len("__RUN_TOOL_ERROR__") :]
    else:
        result_text = dispatch_tool(tool_name, tool_args)

    print(result_text)

    if is_error_result(result_text):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
