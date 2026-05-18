"""Preview_Any_As_Text node."""

from __future__ import annotations

from .common import any_type, custom_input, int_input, to_plain_text

DEFAULT_PREVIEW_TEXT = "Waiting for trigger"


def _preview_text(value) -> str:
    if value == "":
        return '""'
    return to_plain_text(value)


class PreviewAnyAsText:
    """Preview any input as selectable text, then clear it after a short delay."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "preview"
    RETURN_TYPES = ()
    RETURN_NAMES = ()
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "Source": custom_input(any_type),
                "display_time": int_input(3, min=0),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def preview(self, Source=None, display_time=3):
        if not isinstance(display_time, int) or isinstance(display_time, bool):
            display_time = 3
        display_time = max(0, display_time)
        return {
            "ui": {
                "preview_text": [_preview_text(Source)],
                "display_time": [display_time],
                "default_text": [DEFAULT_PREVIEW_TEXT],
            },
            "result": (),
        }
