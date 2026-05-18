from __future__ import annotations

import json
from pathlib import Path


SETTINGS_FILE = Path(__file__).resolve().parent / "settings.json"
DEFAULT_TRUNCATED_CHARACTERS = 3000
TRUNCATED_SUFFIX = "\n...[truncated]"


def get_truncated_characters() -> int:
    if not SETTINGS_FILE.is_file():
        return DEFAULT_TRUNCATED_CHARACTERS

    data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    value = data.get("TruncatedCharacters", DEFAULT_TRUNCATED_CHARACTERS)

    if not isinstance(value, int):
        raise ValueError("settings.json TruncatedCharacters must be an integer")

    if value < 0:
        raise ValueError("settings.json TruncatedCharacters must be 0 or greater")

    return value


def truncate_text(text: str) -> str:
    limit = get_truncated_characters()

    if len(text) <= limit:
        return text

    if limit == 0:
        return TRUNCATED_SUFFIX.lstrip()

    return text[:limit] + TRUNCATED_SUFFIX
