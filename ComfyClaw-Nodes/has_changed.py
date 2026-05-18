"""Has_Changed node."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .common import require_string, resolve_text_path, serialize_json, string_input

MODIFY_DATES_KEY = "FILE_MODIFY_DATES"


def _modified_timestamp(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="microseconds")


def _load_json_store(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        return None, f"Invalid JSON file: {exc}"
    except Exception as exc:  # pragma: no cover - filesystem dependent
        return None, f"Could not read JSON file: {exc}"

    if not isinstance(data, dict):
        return None, "Invalid JSON file: root value must be an object."
    return data, ""


class HasChanged:
    """Track whether a file's Date Modified value changed since the last check."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "check_has_changed"
    RETURN_TYPES = ("BOOLEAN", "STRING", "STRING")
    RETURN_NAMES = ("has_changed", "last_modified", "error_string")
    SEARCH_ALIASES = ["file changed", "modified date", "watch file"]

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "data_file": string_input("", multiline=False),
                "file_to_check": string_input("", multiline=False),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def check_has_changed(self, data_file, file_to_check):
        checked_data_file, data_file_error = require_string(data_file, "data_file")
        checked_file_to_check, file_to_check_error = require_string(file_to_check, "file_to_check")
        if data_file_error or file_to_check_error:
            return (False, "", "; ".join(error for error in (data_file_error, file_to_check_error) if error))
        if not checked_data_file.strip():
            return (False, "", "data_file cannot be empty.")
        if not checked_file_to_check.strip():
            return (False, "", "file_to_check cannot be empty.")

        data_path = resolve_text_path(checked_data_file.strip())
        target_path = resolve_text_path(checked_file_to_check.strip())
        for path in (data_path, target_path):
            if not path.exists():
                return (False, "", f"File not found: {path}")
            if not path.is_file():
                return (False, "", f"Path is not a file: {path}")

        data, error = _load_json_store(data_path)
        if error:
            return (False, "", error)
        assert data is not None

        modify_dates = data.get(MODIFY_DATES_KEY)
        if modify_dates is None:
            modify_dates = {}
            data[MODIFY_DATES_KEY] = modify_dates
        if not isinstance(modify_dates, dict):
            return (False, "", f"Invalid JSON file: {MODIFY_DATES_KEY} must be an object.")

        try:
            last_modified = _modified_timestamp(target_path)
        except Exception as exc:  # pragma: no cover - filesystem dependent
            return (False, "", f"Could not read file metadata: {exc}")

        file_key = target_path.resolve().as_posix()
        has_changed = modify_dates.get(file_key) != last_modified
        if not has_changed:
            return (False, last_modified, "")

        modify_dates[file_key] = last_modified
        try:
            data_path.write_text(serialize_json(data), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - filesystem dependent
            return (False, last_modified, f"Could not update JSON file: {exc}")

        return (True, last_modified, "")
