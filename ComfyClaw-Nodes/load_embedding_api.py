"""Load_Embedding_API node."""

from __future__ import annotations

from .common import is_valid_url, normalize_base_url, string_input
from .providers import EmbeddingProvider


class LoadEmbeddingAPI:
    """Configure a remote embedding API provider."""

    CATEGORY = "ComfyClaw/Embedding"
    FUNCTION = "load_api"
    RETURN_TYPES = ("EMBEDDING_PROVIDER", "STRING")
    RETURN_NAMES = ("embedding_provider", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_base_url": string_input("https://api.openai.com/v1", multiline=False),
                "api_key": string_input("", multiline=False),
                "model_name": string_input("", multiline=False),
            }
        }

    def load_api(self, api_base_url, api_key, model_name):
        if not isinstance(api_base_url, str) or not isinstance(api_key, str) or not isinstance(model_name, str):
            return (None, "api_base_url, api_key, and model_name must all be strings.")
        if not api_base_url.strip() or not api_key.strip() or not model_name.strip():
            return (None, "api_base_url, api_key, and model_name cannot be empty.")
        if not is_valid_url(api_base_url.strip()):
            return (None, "api_base_url must be a valid http or https URL.")
        provider = EmbeddingProvider(
            api_base_url=normalize_base_url(api_base_url.strip()),
            api_key=api_key.strip(),
            model_name=model_name.strip(),
            provider_kind="api",
        )
        return (provider, "")
