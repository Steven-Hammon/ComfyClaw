"""LLM_Model_Loader node."""

from __future__ import annotations

from .common import DEFAULT_OLLAMA_URL, is_valid_url, normalize_base_url, string_input
from .providers import LLMProvider


class LLMModelLoader:
    """Configure a local Ollama LLM provider."""

    CATEGORY = "ComfyClaw/LLM"
    FUNCTION = "load_model"
    RETURN_TYPES = ("LLM_PROVIDER", "STRING")
    RETURN_NAMES = ("llm_provider", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "ollama_base_url": string_input(DEFAULT_OLLAMA_URL, multiline=False),
                "model_name": string_input("", multiline=False),
            }
        }

    def load_model(self, ollama_base_url, model_name):
        if not isinstance(ollama_base_url, str) or not isinstance(model_name, str):
            return (None, "ollama_base_url and model_name must be strings.")
        if not ollama_base_url.strip() or not model_name.strip():
            return (None, "ollama_base_url and model_name cannot be empty.")
        if not is_valid_url(ollama_base_url.strip()):
            return (None, "ollama_base_url must be a valid http or https URL.")
        provider = LLMProvider(
            api_base_url=normalize_base_url(ollama_base_url.strip()),
            api_key="",
            model_name=model_name.strip(),
            provider_kind="ollama",
        )
        return (provider, "")
