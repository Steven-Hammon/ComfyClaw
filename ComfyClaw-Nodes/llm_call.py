"""LLMCall node."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .common import combo_input, custom_input, extract_openai_message_text, float_input, http_post_json, int_input, serialize_json, string_input
from .media_common import (
    AUDIO_FORMATS,
    IMAGE_FORMATS,
    MEDIA_CONVERSIONS,
    audio_to_bytes,
    bytes_to_base64_data,
    data_url,
    file_to_base64_data,
    image_to_bytes,
    join_errors,
)
from .providers import LLMProvider


THINK_TAG_PATTERN = re.compile(r"<think>(.*?)</think>", flags=re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class _Base64Media:
    data: str
    mime_type: str
    source: str


@dataclass(frozen=True)
class _MediaBundle:
    prompt: str
    images: tuple[_Base64Media, ...]
    audio: tuple[_Base64Media, ...]
    error: str = ""


def _thinking_to_text(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, str):
        return value
    return serialize_json(value)


def _extract_think_tags(response_text: str) -> tuple[str, str]:
    matches = THINK_TAG_PATTERN.findall(response_text)
    thinking_text = "\n\n".join(match.strip() for match in matches if match.strip())
    cleaned_response = THINK_TAG_PATTERN.sub("", response_text).strip()
    return thinking_text, cleaned_response


def _append_media_paths(prompt: str, image_file_path: str = "", sound_file_path: str = "") -> str:
    media_lines = []
    if isinstance(image_file_path, str) and image_file_path.strip():
        media_lines.append(f"image_file_path: {image_file_path.strip()}")
    if isinstance(sound_file_path, str) and sound_file_path.strip():
        media_lines.append(f"sound_file_path: {sound_file_path.strip()}")
    if not media_lines:
        return prompt
    return f"{prompt.rstrip()}\n\n[Media]\n" + "\n".join(media_lines)


def _normalize_media_inputs(
    prompt: str,
    media_conversion: str,
    image_format: str,
    audio_format: str,
    image_input=None,
    audio_input=None,
    image_file_path: str = "",
    sound_file_path: str = "",
) -> _MediaBundle:
    errors: list[str] = []
    images: list[_Base64Media] = []
    audio: list[_Base64Media] = []

    if media_conversion not in MEDIA_CONVERSIONS:
        errors.append(f"media_conversion must be one of: {', '.join(MEDIA_CONVERSIONS)}")
        media_conversion = "base64"
    if image_format not in IMAGE_FORMATS:
        errors.append(f"image_format must be one of: {', '.join(IMAGE_FORMATS)}")
        image_format = "png"
    if audio_format not in AUDIO_FORMATS:
        errors.append(f"audio_format must be one of: {', '.join(AUDIO_FORMATS)}")
        audio_format = "wav"

    image_path = image_file_path.strip() if isinstance(image_file_path, str) else ""
    sound_path = sound_file_path.strip() if isinstance(sound_file_path, str) else ""

    if image_input is not None and image_path:
        errors.append("Use either image_input or image_file_path, not both.")
    if audio_input is not None and sound_path:
        errors.append("Use either audio_input or sound_file_path, not both.")

    if media_conversion == "path_only":
        if image_input is not None:
            errors.append("path_only cannot use image_input. Save it first with Save_Media_As and pass image_file_path.")
        if audio_input is not None:
            errors.append("path_only cannot use audio_input. Save it first with Save_Media_As and pass sound_file_path.")
        return _MediaBundle(_append_media_paths(prompt, image_path, sound_path), tuple(), tuple(), join_errors(errors))

    if image_input is not None:
        try:
            data, mime_type = image_to_bytes(image_input, image_format)
            encoded, mime_type = bytes_to_base64_data(data, mime_type)
            images.append(_Base64Media(encoded, mime_type, "image_input"))
        except Exception as exc:
            errors.append(f"image_input conversion failed: {exc}")
    elif image_path:
        try:
            encoded, mime_type, source = file_to_base64_data(image_path)
            images.append(_Base64Media(encoded, mime_type, source))
        except Exception as exc:
            errors.append(f"image_file_path conversion failed: {exc}")

    if audio_input is not None:
        try:
            data, mime_type = audio_to_bytes(audio_input, audio_format)
            encoded, mime_type = bytes_to_base64_data(data, mime_type)
            audio.append(_Base64Media(encoded, mime_type, "audio_input"))
        except Exception as exc:
            errors.append(f"audio_input conversion failed: {exc}")
    elif sound_path:
        try:
            encoded, mime_type, source = file_to_base64_data(sound_path)
            audio.append(_Base64Media(encoded, mime_type, source))
        except Exception as exc:
            errors.append(f"sound_file_path conversion failed: {exc}")

    return _MediaBundle(prompt, tuple(images), tuple(audio), join_errors(errors))


def _build_ollama_messages(system_prompt: str, media_bundle: _MediaBundle) -> list[dict]:
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    user_message: dict[str, object] = {"role": "user", "content": media_bundle.prompt}
    if media_bundle.images:
        user_message["images"] = [image.data for image in media_bundle.images]
    messages.append(user_message)
    return messages


def _build_openai_messages(system_prompt: str, media_bundle: _MediaBundle, audio_format: str) -> list[dict]:
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})

    content: list[dict[str, object]] = [{"type": "text", "text": media_bundle.prompt}]
    for image in media_bundle.images:
        content.append({"type": "image_url", "image_url": {"url": data_url(image.data, image.mime_type)}})
    for audio in media_bundle.audio:
        normalized_format = "mp3" if "mpeg" in audio.mime_type else audio_format
        content.append({"type": "input_audio", "input_audio": {"data": audio.data, "format": normalized_format}})

    messages.append({"role": "user", "content": content if len(content) > 1 else media_bundle.prompt})
    return messages


def _call_ollama(
    provider: LLMProvider,
    media_bundle: _MediaBundle,
    system_prompt: str,
    temperature: float,
    max_output_tokens: int,
    timeout_seconds: float,
) -> tuple[str, str]:
    if media_bundle.audio:
        raise RuntimeError("base64 audio is not supported by the Ollama chat payload in this node. Use media_conversion=path_only for local audio-path workflows.")
    payload = {
        "model": provider.model_name,
        "messages": _build_ollama_messages(system_prompt, media_bundle),
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_output_tokens},
    }
    response, _ = http_post_json(f"{provider.api_base_url}/api/chat", payload, timeout=timeout_seconds)
    message = response.get("message") if isinstance(response, dict) else None
    if isinstance(message, dict) and "content" in message:
        response_text = extract_openai_message_text(message["content"])
        thinking_text = ""
        for source in (message, response):
            if not isinstance(source, dict):
                continue
            for key in ("thinking", "reasoning", "reasoning_content"):
                thinking_text = _thinking_to_text(source.get(key))
                if thinking_text:
                    break
            if thinking_text:
                break
        tagged_thinking, clean_response = _extract_think_tags(response_text)
        return clean_response, thinking_text or tagged_thinking
    raise RuntimeError("Ollama did not return a message content field.")


def _call_openai_compatible(
    provider: LLMProvider,
    media_bundle: _MediaBundle,
    system_prompt: str,
    temperature: float,
    max_output_tokens: int,
    timeout_seconds: float,
    audio_format: str,
) -> tuple[str, str]:
    headers = {}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"
    payload = {
        "model": provider.model_name,
        "messages": _build_openai_messages(system_prompt, media_bundle, audio_format),
        "temperature": temperature,
        "max_tokens": max_output_tokens,
    }
    response, _ = http_post_json(f"{provider.api_base_url}/chat/completions", payload, headers=headers, timeout=timeout_seconds)
    if isinstance(response, dict) and isinstance(response.get("choices"), list) and response["choices"]:
        message = response["choices"][0].get("message", {})
        if isinstance(message, dict) and "content" in message:
            response_text = extract_openai_message_text(message["content"])
            thinking_text = ""
            for key in ("reasoning_content", "reasoning", "thinking"):
                thinking_text = _thinking_to_text(message.get(key))
                if thinking_text:
                    break
            tagged_thinking, clean_response = _extract_think_tags(response_text)
            return clean_response, thinking_text or tagged_thinking
    raise RuntimeError("LLM API response did not contain a message.")


class LLMCall:
    """Send a text or explicit multimodal prompt to an LLM provider."""

    CATEGORY = "ComfyClaw/LLM"
    FUNCTION = "call_llm"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("response_text", "error_string", "thinking_output")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "llm_provider": custom_input("LLM_PROVIDER"),
                "user_prompt": string_input(""),
                "temperature": float_input(0.7, min=0.0, max=2.0, step=0.05),
                "max_output_tokens": int_input(1024, min=1, max=999999),
                "timeout_seconds": float_input(60.0, min=1.0, max=600.0, step=1.0),
                "system_prompt": string_input(""),
                "media_conversion": combo_input(MEDIA_CONVERSIONS, default="base64"),
                "image_format": combo_input(IMAGE_FORMATS, default="png"),
                "audio_format": combo_input(AUDIO_FORMATS, default="wav"),
                "image_file_path": string_input("", multiline=False),
                "sound_file_path": string_input("", multiline=False),
            },
            "optional": {
                "image_input": ("IMAGE",),
                "audio_input": ("AUDIO",),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def call_llm(
        self,
        llm_provider,
        user_prompt,
        temperature=0.7,
        max_output_tokens=1024,
        timeout_seconds=60.0,
        system_prompt="",
        media_conversion="base64",
        image_format="png",
        audio_format="wav",
        image_file_path="",
        sound_file_path="",
        image_input=None,
        audio_input=None,
        **kwargs,
    ):
        legacy_max_tokens = kwargs.get("max_tokens")
        if legacy_max_tokens is not None and max_output_tokens == 1024:
            max_output_tokens = legacy_max_tokens

        if not isinstance(llm_provider, LLMProvider):
            return ("", "llm_provider is missing or invalid.", "")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            return ("", "user_prompt cannot be empty.", "")
        if not isinstance(system_prompt, str):
            return ("", "system_prompt must be a string.", "")
        if not isinstance(temperature, (int, float)):
            return ("", "temperature must be numeric.", "")
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            return ("", "max_output_tokens must be a positive integer.", "")
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            return ("", "timeout_seconds must be positive.", "")

        media_bundle = _normalize_media_inputs(
            user_prompt,
            media_conversion,
            image_format,
            audio_format,
            image_input=image_input,
            audio_input=audio_input,
            image_file_path=image_file_path,
            sound_file_path=sound_file_path,
        )
        if media_bundle.error:
            return ("", media_bundle.error, "")

        try:
            if llm_provider.provider_kind == "ollama":
                response_text, thinking_output = _call_ollama(
                    llm_provider, media_bundle, system_prompt, float(temperature), max_output_tokens, float(timeout_seconds)
                )
            else:
                response_text, thinking_output = _call_openai_compatible(
                    llm_provider,
                    media_bundle,
                    system_prompt,
                    float(temperature),
                    max_output_tokens,
                    float(timeout_seconds),
                    audio_format,
                )
        except Exception as exc:
            return ("", f"LLM request failed: {exc}", "")
        return (response_text, "", thinking_output)
