"""Shared media conversion helpers for ComfyClaw nodes."""

from __future__ import annotations

import base64
import io
import mimetypes
import os
import wave
from pathlib import Path
from typing import Any


IMAGE_FORMATS = ("png", "jpg")
AUDIO_FORMATS = ("wav", "mp3")
MEDIA_FORMATS = ("png", "jpg", "wav", "mp3", "txt")
MEDIA_CONVERSIONS = ("base64", "path_only")


def join_errors(errors: list[str]) -> str:
    return "; ".join(error for error in errors if error)


def resolve_media_path(path_text: str) -> Path:
    expanded = os.path.expandvars(path_text.strip())
    path = Path(expanded).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path


def path_with_format(path_text: str, media_format: str) -> Path:
    path = resolve_media_path(path_text)
    if path.exists() and path.is_dir():
        return path / f"media.{media_format}"
    if not path.suffix:
        return path.with_suffix(f".{media_format}")
    return path


def media_mime_type(path: str | Path, fallback_format: str = "") -> str:
    mime_type, _ = mimetypes.guess_type(str(path))
    if mime_type:
        return mime_type
    normalized = fallback_format.lower().lstrip(".")
    if normalized == "png":
        return "image/png"
    if normalized in {"jpg", "jpeg"}:
        return "image/jpeg"
    if normalized == "wav":
        return "audio/wav"
    if normalized == "mp3":
        return "audio/mpeg"
    if normalized == "txt":
        return "text/plain"
    return "application/octet-stream"


def _to_numpy(value: Any):
    import numpy as np

    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        return value.numpy()
    return np.asarray(value)


def image_to_pil(image_input: Any):
    import numpy as np
    from PIL import Image

    if isinstance(image_input, Image.Image):
        return image_input.convert("RGB")

    array = _to_numpy(image_input)
    if array.ndim == 4:
        array = array[0]
    if array.ndim == 3 and array.shape[0] in {1, 3, 4} and array.shape[-1] not in {1, 3, 4}:
        array = np.transpose(array, (1, 2, 0))
    if array.ndim == 2:
        array = array[:, :, None]

    if array.ndim != 3:
        raise ValueError("image_input must be a PIL image or a tensor/array shaped HWC, BHWC, CHW, or BCHW.")

    if array.shape[-1] == 1:
        array = np.repeat(array, 3, axis=-1)
    elif array.shape[-1] > 4:
        array = array[:, :, :3]

    if np.issubdtype(array.dtype, np.floating):
        array = np.clip(array, 0.0, 1.0) * 255.0
    else:
        array = np.clip(array, 0, 255)
    array = array.astype("uint8")

    if array.shape[-1] == 4:
        return Image.fromarray(array, mode="RGBA").convert("RGB")
    return Image.fromarray(array[:, :, :3], mode="RGB")


def image_to_bytes(image_input: Any, image_format: str) -> tuple[bytes, str]:
    normalized_format = image_format.lower()
    if normalized_format not in IMAGE_FORMATS:
        raise ValueError("image_format must be png or jpg.")

    image = image_to_pil(image_input)
    output = io.BytesIO()
    if normalized_format == "jpg":
        image.save(output, format="JPEG", quality=95)
        return output.getvalue(), "image/jpeg"
    image.save(output, format="PNG")
    return output.getvalue(), "image/png"


def _audio_waveform_and_rate(audio_input: Any):
    if not isinstance(audio_input, dict):
        raise ValueError("audio_input must be a ComfyUI AUDIO dictionary with waveform and sample_rate.")
    if "waveform" not in audio_input or "sample_rate" not in audio_input:
        raise ValueError("audio_input must contain waveform and sample_rate.")
    sample_rate = int(audio_input["sample_rate"])
    if sample_rate <= 0:
        raise ValueError("audio_input sample_rate must be positive.")
    return _to_numpy(audio_input["waveform"]), sample_rate


def audio_to_wav_bytes(audio_input: Any) -> bytes:
    import numpy as np

    waveform, sample_rate = _audio_waveform_and_rate(audio_input)
    if waveform.ndim == 3:
        waveform = waveform[0]
    if waveform.ndim == 1:
        samples_by_channel = waveform[:, None]
    elif waveform.ndim == 2:
        if waveform.shape[0] <= 8 and waveform.shape[1] > waveform.shape[0]:
            samples_by_channel = waveform.T
        else:
            samples_by_channel = waveform
    else:
        raise ValueError("audio waveform must be shaped samples, channels-by-samples, samples-by-channels, or batch-by-channels-by-samples.")

    samples_by_channel = np.asarray(samples_by_channel, dtype="float32")
    samples_by_channel = np.clip(samples_by_channel, -1.0, 1.0)
    pcm = (samples_by_channel * 32767.0).astype("<i2")

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(int(pcm.shape[1]))
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm.tobytes())
    return output.getvalue()


def audio_to_bytes(audio_input: Any, audio_format: str) -> tuple[bytes, str]:
    normalized_format = audio_format.lower()
    if normalized_format == "wav":
        return audio_to_wav_bytes(audio_input), "audio/wav"
    if normalized_format == "mp3":
        wav_bytes = audio_to_wav_bytes(audio_input)
        try:
            from pydub import AudioSegment
        except Exception as exc:
            raise RuntimeError("mp3 encoding requires pydub and ffmpeg. Use wav for built-in audio saving.") from exc
        output = io.BytesIO()
        AudioSegment.from_wav(io.BytesIO(wav_bytes)).export(output, format="mp3")
        return output.getvalue(), "audio/mpeg"
    raise ValueError("audio_format must be wav or mp3.")


def file_to_base64_data(path_text: str) -> tuple[str, str, str]:
    path = resolve_media_path(path_text)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"media file not found: {path}")
    data = path.read_bytes()
    mime_type = media_mime_type(path)
    return base64.b64encode(data).decode("ascii"), mime_type, str(path)


def bytes_to_base64_data(data: bytes, mime_type: str) -> tuple[str, str]:
    return base64.b64encode(data).decode("ascii"), mime_type


def data_url(data_b64: str, mime_type: str) -> str:
    return f"data:{mime_type};base64,{data_b64}"
