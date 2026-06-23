"""Save ComfyUI image, audio, or text inputs to a chosen file path."""

from __future__ import annotations

from typing import Any

from .common import combo_input, string_input
from .media_common import AUDIO_FORMATS, IMAGE_FORMATS, MEDIA_FORMATS, audio_to_bytes, image_to_bytes, join_errors, path_with_format


class SaveMediaAs:
    """Save one media input as png, jpg, wav, mp3, or txt."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "save_media_as"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("file_path", "error_string")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_path": string_input("", multiline=False),
                "media_format": combo_input(MEDIA_FORMATS, default="png"),
                "text_input": string_input(""),
            },
            "optional": {
                "image_input": ("IMAGE",),
                "audio_input": ("AUDIO",),
            },
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def save_media_as(
        self,
        output_path: str,
        media_format: str = "png",
        image_input: Any = None,
        audio_input: Any = None,
        text_input: str = "",
    ):
        errors: list[str] = []
        if not isinstance(output_path, str) or not output_path.strip():
            return ("", "output_path cannot be empty.")
        if media_format not in MEDIA_FORMATS:
            return ("", f"media_format must be one of: {', '.join(MEDIA_FORMATS)}.")

        provided_inputs = [
            name
            for name, value in (
                ("image_input", image_input),
                ("audio_input", audio_input),
                ("text_input", text_input if isinstance(text_input, str) and text_input != "" else None),
            )
            if value is not None
        ]
        if len(provided_inputs) != 1:
            return ("", "Provide exactly one of image_input, audio_input, or text_input.")

        path = path_with_format(output_path, media_format)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return ("", f"could not create output directory: {exc}")

        try:
            if media_format in IMAGE_FORMATS:
                if image_input is None:
                    return ("", f"{media_format} requires image_input.")
                data, _ = image_to_bytes(image_input, media_format)
                path.write_bytes(data)
            elif media_format in AUDIO_FORMATS:
                if audio_input is None:
                    return ("", f"{media_format} requires audio_input.")
                data, _ = audio_to_bytes(audio_input, media_format)
                path.write_bytes(data)
            else:
                if not isinstance(text_input, str):
                    return ("", "txt requires text_input to be a string.")
                path.write_text(text_input, encoding="utf-8")
        except Exception as exc:
            errors.append(f"save media failed: {exc}")

        if errors:
            return ("", join_errors(errors))
        return (str(path), "")
