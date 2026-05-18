"""Embedding node."""

from __future__ import annotations

import json

from .common import DEFAULT_CHUNK_BREAK_MARKER, combo_input, custom_input, http_post_json, serialize_json, string_input
from .providers import EmbeddingProvider


def _embed_with_provider(provider: EmbeddingProvider, text: str, timeout: float = 30.0) -> list[float]:
    if provider.provider_kind == "ollama":
        base_url = provider.api_base_url.rstrip("/")
        payload = {"model": provider.model_name, "input": text}
        try:
            response, _ = http_post_json(f"{base_url}/api/embed", payload, timeout=timeout)
            if isinstance(response, dict) and response.get("embeddings"):
                return [float(value) for value in response["embeddings"][0]]
        except Exception:
            pass

        legacy_payload = {"model": provider.model_name, "prompt": text}
        response, _ = http_post_json(f"{base_url}/api/embeddings", legacy_payload, timeout=timeout)
        if isinstance(response, dict) and "embedding" in response:
            return [float(value) for value in response["embedding"]]
        raise RuntimeError("Ollama embedding response did not include an embedding vector.")

    headers = {"Authorization": f"Bearer {provider.api_key}"}
    payload = {"model": provider.model_name, "input": text}
    response, _ = http_post_json(f"{provider.api_base_url}/embeddings", payload, headers=headers, timeout=timeout)
    if isinstance(response, dict) and isinstance(response.get("data"), list) and response["data"]:
        vector = response["data"][0].get("embedding")
        if isinstance(vector, list):
            return [float(value) for value in vector]
    raise RuntimeError("Embedding API response did not include an embedding vector.")


class Embedding:
    """Embed chunked text using an embedding provider."""

    CATEGORY = "ComfyClaw/Embedding"
    FUNCTION = "embed_chunks"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("embedding_bundle_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "embedding_provider": custom_input("EMBEDDING_PROVIDER"),
                "chunk_input": string_input(""),
                "input_format": combo_input(["json_list", "break_string"], default="json_list"),
                "chunk_break_marker": string_input(DEFAULT_CHUNK_BREAK_MARKER, multiline=False),
                "mode": combo_input(["Overwrite", "Append"], default="Overwrite"),
                "embedding_bundle_string": string_input(""),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def embed_chunks(
        self,
        embedding_provider,
        chunk_input,
        input_format="json_list",
        chunk_break_marker=DEFAULT_CHUNK_BREAK_MARKER,
        mode="Overwrite",
        embedding_bundle_string="",
    ):
        if not isinstance(embedding_provider, EmbeddingProvider):
            return ("", "embedding_provider is missing or invalid.")
        if not isinstance(chunk_input, str):
            return ("", "chunk_input must be a string.")
        if not chunk_input.strip():
            return ("", "chunk_input cannot be empty.")
        if mode not in {"Overwrite", "Append"}:
            return ("", "mode must be Overwrite or Append.")
        if not isinstance(embedding_bundle_string, str):
            return ("", "embedding_bundle_string must be a string.")

        try:
            if input_format == "json_list":
                parsed = json.loads(chunk_input)
                if isinstance(parsed, list):
                    chunks = [chunk for chunk in parsed if isinstance(chunk, str) and chunk.strip()]
                elif isinstance(parsed, dict):
                    chunks = [serialize_json({key: value}) for key, value in parsed.items()]
                else:
                    return ("", "chunk_input must be a JSON array or JSON object when input_format is json_list.")
            else:
                if not isinstance(chunk_break_marker, str) or not chunk_break_marker:
                    return ("", "chunk_break_marker cannot be empty when input_format is break_string.")
                chunks = [chunk for chunk in chunk_input.split(chunk_break_marker) if chunk.strip()]
        except Exception as exc:
            return ("", f"Could not parse chunk_input: {exc}")

        if not chunks:
            return ("", "No valid chunks were found to embed.")

        bundle = None
        existing_chunks = None
        existing_embeddings = None
        if mode == "Append" and embedding_bundle_string.strip():
            try:
                bundle = json.loads(embedding_bundle_string)
            except Exception as exc:
                return ("", f"embedding_bundle_string is not valid JSON: {exc}")

            existing_chunks = bundle.get("chunks") if isinstance(bundle, dict) else None
            existing_embeddings = bundle.get("embeddings") if isinstance(bundle, dict) else None
            bundle_model = bundle.get("model_name") if isinstance(bundle, dict) else None
            if not isinstance(bundle, dict) or not isinstance(existing_chunks, list) or not isinstance(existing_embeddings, list):
                return ("", "embedding_bundle_string does not contain a valid chunks/embeddings bundle.")
            if len(existing_chunks) != len(existing_embeddings):
                return ("", "embedding_bundle_string does not contain a valid chunks/embeddings bundle.")
            if not isinstance(bundle_model, str) or not bundle_model:
                return ("", "embedding_bundle_string does not contain a valid model_name.")
            if bundle_model != embedding_provider.model_name:
                return ("", f"Incompatible embedding_provider detected. Expected {bundle_model}")

        try:
            embeddings = [_embed_with_provider(embedding_provider, chunk) for chunk in chunks]
        except Exception as exc:
            return ("", f"Embedding request failed: {exc}")

        if bundle is not None and existing_chunks is not None and existing_embeddings is not None:
            existing_chunks.extend(chunks)
            existing_embeddings.extend(embeddings)
            bundle.setdefault("provider_kind", embedding_provider.provider_kind)
        else:
            bundle = {
                "model_name": embedding_provider.model_name,
                "provider_kind": embedding_provider.provider_kind,
                "chunks": chunks,
                "embeddings": embeddings,
            }
        return (serialize_json(bundle), "")
