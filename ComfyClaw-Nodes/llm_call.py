"""LLMCall node."""

from __future__ import annotations

import re

from .common import custom_input, extract_openai_message_text, float_input, http_post_json, int_input, serialize_json, string_input
from .providers import LLMProvider


THINK_TAG_PATTERN = re.compile(r"<think>(.*?)</think>", flags=re.DOTALL | re.IGNORECASE)


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


def _build_messages(system_prompt: str, user_prompt: str) -> list[dict[str, str]]:
    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    return messages


def _call_ollama(
    provider: LLMProvider,
    prompt: str,
    system_prompt: str,
    temperature: float,
    max_output_tokens: int,
    timeout_seconds: float,
) -> tuple[str, str]:
    payload = {
        "model": provider.model_name,
        "messages": _build_messages(system_prompt, prompt),
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
    prompt: str,
    system_prompt: str,
    temperature: float,
    max_output_tokens: int,
    timeout_seconds: float,
) -> tuple[str, str]:
    headers = {}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"
    payload = {
        "model": provider.model_name,
        "messages": _build_messages(system_prompt, prompt),
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
    """Send a prompt to an LLM provider and return the text response."""

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

        try:
            if llm_provider.provider_kind == "ollama":
                response_text, thinking_output = _call_ollama(
                    llm_provider, user_prompt, system_prompt, float(temperature), max_output_tokens, float(timeout_seconds)
                )
            else:
                response_text, thinking_output = _call_openai_compatible(
                    llm_provider, user_prompt, system_prompt, float(temperature), max_output_tokens, float(timeout_seconds)
                )
        except Exception as exc:
            return ("", f"LLM request failed: {exc}", "")
        return (response_text, "", thinking_output)
