"""Timestamp node."""

from __future__ import annotations

from datetime import datetime

from .common import combo_input


class Timestamp:
    """Return the current system timestamp in a selected format."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "get_timestamp"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("timestamp_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"format": combo_input(["iso", "human", "unix"], default="iso")}}

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def get_timestamp(self, format="iso"):
        try:
            now = datetime.now().astimezone()
            if format == "human":
                value = now.strftime("%d %b %Y %H:%M:%S")
            elif format == "unix":
                value = str(int(now.timestamp()))
            else:
                value = now.replace(microsecond=0).isoformat()
            return (value, "")
        except Exception as exc:  # pragma: no cover - system clock dependent
            return ("", f"Could not access system time: {exc}")
