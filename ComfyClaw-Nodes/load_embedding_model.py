"""Load_Embedding_Model node."""

from __future__ import annotations

from .common import DEFAULT_OLLAMA_URL, is_valid_url, normalize_base_url, string_input
from .providers import EmbeddingProvider


class LoadEmbeddingModel:
    """Configure a local Ollama embedding provider."""

    CATEGORY = "ComfyClaw/Embedding"
    FUNCTION = "load_model"
    RETURN_TYPES = ("EMBEDDING_PROVIDER", "STRING")
    RETURN_NAMES = ("embedding_provider", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"model_name": string_input("", multiline=False)}}

    def load_model(self, model_name):
        if not isinstance(model_name, str):
            return (None, "model_name must be a string.")
        if not model_name.strip():
            return (None, "model_name cannot be empty.")
        if not is_valid_url(DEFAULT_OLLAMA_URL):
            return (None, "The default Ollama base URL is invalid.")
        provider = EmbeddingProvider(
            api_base_url=normalize_base_url(DEFAULT_OLLAMA_URL),
            api_key="",
            model_name=model_name.strip(),
            provider_kind="ollama",
        )
        return (provider, "")
