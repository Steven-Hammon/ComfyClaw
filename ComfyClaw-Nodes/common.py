"""Shared helpers for ComfyClaw nodes."""

from __future__ import annotations

import copy
import json
import locale
import math
import random
import re
import urllib.error
import urllib.parse
import urllib.request
from bisect import bisect_right
from pathlib import Path
from typing import Any, Iterable, Union

MAX_DYNAMIC_SLOTS = 20
DEFAULT_CHUNK_BREAK_MARKER = "\n---CHUNK_BREAK---\n"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MCP_PROTOCOL_VERSION = "2025-03-26"


class AnyType(str):
    """A type marker that compares equal to every ComfyUI socket type."""

    def __ne__(self, __value: object) -> bool:
        return False


class FlexibleOptionalInputType(dict):
    """Dictionary-like INPUT_TYPES helper that accepts arbitrary optional keys."""

    def __init__(self, type: Any, data: dict[str, Any] | None = None):
        self.type = type
        self.data = data or {}
        super().__init__(self.data)

    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        return (self.type,)

    def __contains__(self, key):
        return True


any_type = AnyType("*")


def string_input(default: str = "", multiline: bool = True, **extra: Any) -> tuple[str, dict[str, Any]]:
    options: dict[str, Any] = {"default": default, "multiline": multiline}
    options.update(extra)
    return ("STRING", options)


def int_input(default: int = 0, **extra: Any) -> tuple[str, dict[str, Any]]:
    options: dict[str, Any] = {"default": default}
    options.update(extra)
    return ("INT", options)


def float_input(default: float = 0.0, **extra: Any) -> tuple[str, dict[str, Any]]:
    options: dict[str, Any] = {"default": default}
    options.update(extra)
    return ("FLOAT", options)


def bool_input(
    default: bool = False,
    label_on: str = "true",
    label_off: str = "false",
    **extra: Any,
) -> tuple[str, dict[str, Any]]:
    options: dict[str, Any] = {"default": default, "label_on": label_on, "label_off": label_off}
    options.update(extra)
    return ("BOOLEAN", options)


def combo_input(options: Iterable[str], default: str | None = None, **extra: Any) -> tuple[list[str], dict[str, Any]]:
    values = list(options)
    widget_options: dict[str, Any] = {"default": default or values[0]}
    widget_options.update(extra)
    return (values, widget_options)


def custom_input(type_name: str) -> tuple[str, dict[str, Any]]:
    return (type_name, {"forceInput": True})


def flexible_optional_inputs(data: dict[str, Any] | None = None) -> FlexibleOptionalInputType:
    return FlexibleOptionalInputType(type=any_type, data=data or {})


def build_text_inputs(
    prefix: str,
    *,
    start_index: int = 1,
    count: int = MAX_DYNAMIC_SLOTS,
    multiline: bool = True,
    defaults: dict[int, str] | None = None,
    advanced_from: int | None = 3,
) -> dict[str, tuple[str, dict[str, Any]]]:
    defaults = defaults or {}
    inputs: dict[str, tuple[str, dict[str, Any]]] = {}
    for index in range(start_index, count + 1):
        options: dict[str, Any] = {"default": defaults.get(index, ""), "multiline": multiline}
        if advanced_from is not None and index >= advanced_from:
            options["advanced"] = True
        inputs[f"{prefix}_{index}"] = ("STRING", options)
    return inputs


def build_rule_inputs(
    prefix: str,
    *,
    count: int = MAX_DYNAMIC_SLOTS,
    defaults: dict[int, tuple[str, str]] | None = None,
    advanced_from: int | None = 3,
    text_name: str = "text",
) -> dict[str, tuple[Any, dict[str, Any]]]:
    defaults = defaults or {}
    inputs: dict[str, tuple[Any, dict[str, Any]]] = {}
    for index in range(1, count + 1):
        default_type, default_text = defaults.get(index, ("contains", ""))
        advanced = advanced_from is not None and index >= advanced_from
        type_options: dict[str, Any] = {"default": default_type}
        text_options: dict[str, Any] = {"default": default_text, "multiline": True}
        if advanced:
            type_options["advanced"] = True
            text_options["advanced"] = True
        inputs[f"{prefix}_{index}_type"] = (["contains", "equals", "starts_with", "ends_with"], type_options)
        inputs[f"{prefix}_{index}_{text_name}"] = ("STRING", text_options)
    return inputs


def collect_ordered_inputs(kwargs: dict[str, Any], prefix: str) -> list[Any]:
    numbered: list[tuple[int, Any]] = []
    for key, value in kwargs.items():
        if not key.startswith(prefix):
            continue
        suffix = key[len(prefix) :]
        if not suffix.isdigit():
            continue
        numbered.append((int(suffix), value))
    numbered.sort(key=lambda item: item[0])
    return [value for _, value in numbered]


def require_string(value: Any, field_name: str) -> tuple[str, str]:
    if not isinstance(value, str):
        return "", f"{field_name} must be a string."
    return value, ""


def match_text(input_string: str, pattern: str, match_type: str) -> bool:
    if match_type == "equals":
        return input_string == pattern
    if match_type == "starts_with":
        return input_string.startswith(pattern)
    if match_type == "ends_with":
        return input_string.endswith(pattern)
    return pattern in input_string


def join_messages(*messages: str) -> str:
    return "; ".join(message for message in messages if message)


def resolve_text_path(file_path: str) -> Path:
    path = Path(file_path).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path


def read_text_file(path: Path) -> str:
    encodings = ("utf-8", "utf-8-sig", locale.getpreferredencoding(False) or "utf-8")
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return path.read_text()


def serialize_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def parse_json_string(json_text: str) -> Any:
    return json.loads(json_text)


def to_plain_text(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return serialize_json(value)
    return str(value)


def parse_jsonish_value(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return text


def decode_common_escapes(text: str) -> str:
    return text.replace("\\r\\n", "\r\n").replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")


def parse_key_path(key_path: str) -> list[str | int]:
    parts = [part for part in key_path.split(".") if part != ""]
    parsed: list[str | int] = []
    for part in parts:
        parsed.append(int(part) if part.isdigit() else part)
    return parsed


def traverse_path(data: Any, path_parts: list[str | int]) -> Any:
    current = data
    for part in path_parts:
        if isinstance(part, int):
            if isinstance(current, list):
                if part < 0 or part >= len(current):
                    raise KeyError(part)
                current = current[part]
            elif isinstance(current, dict):
                key = str(part)
                if key not in current:
                    raise KeyError(part)
                current = current[key]
            else:
                raise KeyError(part)
        else:
            if not isinstance(current, dict) or part not in current:
                raise KeyError(part)
            current = current[part]
    return current


def get_parent_and_key(data: Any, path_parts: list[str | int]) -> tuple[Any, str | int]:
    if not path_parts:
        raise KeyError("empty")
    parent = traverse_path(data, path_parts[:-1]) if len(path_parts) > 1 else data
    key: str | int = path_parts[-1]
    if isinstance(parent, dict) and isinstance(key, int):
        key = str(key)
    return parent, key


def coerce_object_path_parts(path_parts: list[str | int]) -> list[str]:
    return [str(part) if isinstance(part, int) else part for part in path_parts]


def is_valid_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _decode_sse_payload(body: bytes) -> list[Any]:
    events: list[Any] = []
    text = body.decode("utf-8", errors="replace")
    for event in text.split("\n\n"):
        data_lines = [line[5:].strip() for line in event.splitlines() if line.startswith("data:")]
        if not data_lines:
            continue
        payload = "\n".join(data_lines).strip()
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            events.append(payload)
    return events


def http_post_json(
    url: str,
    payload: dict[str, Any] | list[Any],
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[Any, dict[str, str]]:
    request_headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if headers:
        request_headers.update(headers)
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read()
            response_headers = {key: value for key, value in response.headers.items()}
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                events = _decode_sse_payload(raw_body)
                if not events:
                    return "", response_headers
                return events[-1], response_headers
            if not raw_body:
                return "", response_headers
            text = raw_body.decode("utf-8", errors="replace")
            try:
                return json.loads(text), response_headers
            except json.JSONDecodeError:
                return text, response_headers
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {details or exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Request failed: {exc.reason}") from exc


def count_units(text: str, unit: str) -> int:
    if isinstance(unit, list):
        return _count_units_with_markers(text, unit)
    if not text:
        return 0
    normalized = unit.strip().lower()
    if normalized == "words":
        return len(re.findall(r"\S+", text))
    if normalized == "sentences":
        matches = re.findall(r"[^.!?]+[.!?]?", text, flags=re.DOTALL)
        return len([match for match in matches if match.strip()])
    if normalized == "paragraphs":
        parts = re.split(r"\n\s*\n", text)
        return len([part for part in parts if part.strip()])
    if normalized == "characters":
        return len(text)
    if unit:
        return max(1, len(text.split(unit)))
    return len(text)


def _find_word_boundary(text: str, count: int) -> int:
    matches = list(re.finditer(r"\S+\s*", text))
    if count <= 0 or not matches:
        return 0
    if count >= len(matches):
        return len(text)
    return matches[count - 1].end()


def _find_sentence_boundary(text: str, count: int) -> int:
    matches = list(re.finditer(r"[^.!?]+[.!?]?\s*", text, flags=re.DOTALL))
    valid = [match for match in matches if match.group(0).strip()]
    if count <= 0 or not valid:
        return 0
    if count >= len(valid):
        return len(text)
    return valid[count - 1].end()


def _find_paragraph_boundary(text: str, count: int) -> int:
    matches = list(re.finditer(r"(?:.*?(?:\n\s*\n|$))", text, flags=re.DOTALL))
    valid = [match for match in matches if match.group(0).strip()]
    if count <= 0 or not valid:
        return 0
    if count >= len(valid):
        return len(text)
    return valid[count - 1].end()


def take_prefix_by_unit(text: str, unit: str, amount: int) -> str:
    if isinstance(unit, list):
        return _take_prefix_by_markers(text, unit, amount)
    if amount <= 0 or not text:
        return ""
    normalized = unit.strip().lower()
    if normalized == "words":
        return text[: _find_word_boundary(text, amount)]
    if normalized == "sentences":
        return text[: _find_sentence_boundary(text, amount)]
    if normalized == "paragraphs":
        return text[: _find_paragraph_boundary(text, amount)]
    if normalized == "characters":
        return text[:amount]
    if not unit:
        return text[:amount]
    end = 0
    start = 0
    for _ in range(amount):
        index = text.find(unit, start)
        if index == -1:
            return text
        end = index + len(unit)
        start = end
    return text[:end]


def hard_limit_boundary(text: str, unit: str, max_amount: int) -> int:
    return len(take_prefix_by_unit(text, unit, max_amount))


def normalize_marker_list(markers: Iterable[Any]) -> list[str]:
    normalized: list[str] = []
    for marker in markers:
        if not isinstance(marker, str):
            continue
        if marker == "":
            continue
        normalized.append(marker)
    return normalized


def _compile_marker_pattern(markers: list[str]) -> re.Pattern[str] | None:
    normalized = normalize_marker_list(markers)
    if not normalized:
        return None
    ordered = sorted({marker for marker in normalized}, key=len, reverse=True)
    return re.compile("|".join(re.escape(marker) for marker in ordered), flags=re.DOTALL)


def _count_units_with_markers(text: str, markers: list[str]) -> int:
    if not text:
        return 0
    pattern = _compile_marker_pattern(markers)
    if pattern is None:
        return len(text)
    matches = list(pattern.finditer(text))
    if not matches:
        return 1
    count = len(matches)
    if matches[-1].end() < len(text):
        count += 1
    return count


def _take_prefix_by_markers(text: str, markers: list[str], amount: int) -> str:
    if amount <= 0 or not text:
        return ""
    pattern = _compile_marker_pattern(markers)
    if pattern is None:
        return text[:amount]
    matches = list(pattern.finditer(text))
    if not matches:
        return text
    if amount <= len(matches):
        return text[: matches[amount - 1].end()]
    return text


def find_marker_positions(text: str, markers: list[str]) -> list[int]:
    positions: set[int] = set()
    for marker in markers:
        if not marker:
            continue
        start = 0
        while True:
            index = text.find(marker, start)
            if index == -1:
                break
            positions.add(index + len(marker))
            start = index + max(1, len(marker))
    return sorted(position for position in positions if 0 < position < len(text))


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        raise ValueError("Embedding vectors must have the same non-zero length.")
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def fallback_character_chunks(text: str, chunk_size: int = 10_000, overlap_size: int = 1_000) -> list[str]:
    chunks: list[str] = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end >= text_length:
            break
        start = max(end - overlap_size, start + 1)
    return chunks


def serialize_tool_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text" and "text" in item:
                        parts.append(str(item["text"]))
                    elif "text" in item:
                        parts.append(str(item["text"]))
                    else:
                        parts.append(serialize_json(item))
                else:
                    parts.append(str(item))
            if parts:
                return "\n".join(parts)
        if "structuredContent" in result:
            return serialize_json(result["structuredContent"])
    return to_plain_text(result)


def extract_openai_message_text(message_content: Any) -> str:
    if isinstance(message_content, str):
        return message_content
    if isinstance(message_content, list):
        parts: list[str] = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            elif isinstance(item, dict) and "text" in item:
                parts.append(str(item["text"]))
            else:
                parts.append(to_plain_text(item))
        return "".join(parts)
    return to_plain_text(message_content)


def deep_copy_prompt(prompt: Any) -> Any:
    return copy.deepcopy(prompt)


def next_marker_cursor(marker_positions: list[int], boundary: int) -> int:
    return bisect_right(marker_positions, boundary)


def random_seed() -> int:
    return random.randint(0, 2_147_483_647)
