"""Embedding_Query node."""

from __future__ import annotations

import json

from .common import cosine_similarity, custom_input, int_input, serialize_json, string_input
from .embedding import _embed_with_provider
from .providers import EmbeddingProvider


class EmbeddingQuery:
    """Search an embedding bundle with cosine similarity."""

    CATEGORY = "ComfyClaw/Embedding"
    FUNCTION = "query_embeddings"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("results_json_string", "best_chunk_text", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "embedding_provider": custom_input("EMBEDDING_PROVIDER"),
                "embedding_bundle_string": string_input(""),
                "query_text": string_input(""),
                "top_k": int_input(3, min=1),
                "timeout": int_input(30, min=1),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def query_embeddings(self, embedding_provider, embedding_bundle_string, query_text, top_k=3, timeout=30):
        if not isinstance(embedding_provider, EmbeddingProvider):
            return ("", "", "embedding_provider is missing or invalid.")
        if not isinstance(embedding_bundle_string, str) or not embedding_bundle_string.strip():
            return ("", "", "embedding_bundle_string cannot be empty.")
        if not isinstance(query_text, str) or not query_text.strip():
            return ("", "", "query_text cannot be empty.")
        if not isinstance(top_k, int):
            return ("", "", "top_k must be an integer.")
        if not isinstance(timeout, int) or timeout <= 0:
            return ("", "", "timeout must be a positive integer.")

        try:
            bundle = json.loads(embedding_bundle_string)
        except Exception as exc:
            return ("", "", f"embedding_bundle_string is not valid JSON: {exc}")

        chunks = bundle.get("chunks")
        embeddings = bundle.get("embeddings")
        bundle_model = bundle.get("model_name")
        if not isinstance(chunks, list) or not isinstance(embeddings, list) or len(chunks) != len(embeddings):
            return ("", "", "embedding_bundle_string does not contain a valid chunks/embeddings bundle.")
        if bundle_model and bundle_model != embedding_provider.model_name:
            return ("", "", "embedding_provider model_name does not match the bundle model_name.")

        try:
            query_embedding = _embed_with_provider(embedding_provider, query_text.strip(), timeout=float(timeout))
        except Exception as exc:
            return ("", "", f"Query embedding failed: {exc}")

        scored_results = []
        for index, (chunk_text, chunk_embedding) in enumerate(zip(chunks, embeddings)):
            if not isinstance(chunk_text, str) or not isinstance(chunk_embedding, list):
                continue
            try:
                score = cosine_similarity(query_embedding, [float(value) for value in chunk_embedding])
            except Exception:
                continue
            scored_results.append((score, index, chunk_text))

        if not scored_results:
            return ("", "", "No comparable embeddings were found in the bundle.")

        scored_results.sort(key=lambda item: item[0], reverse=True)
        limit = max(1, min(top_k, len(scored_results)))
        result_items = []
        for rank, (score, index, chunk_text) in enumerate(scored_results[:limit], start=1):
            result_items.append(
                {
                    "rank": rank,
                    "chunk_index": index,
                    "score": round(score, 6),
                    "chunk_text": chunk_text,
                }
            )

        results = {"query_text": query_text, "results": result_items}
        return (serialize_json(results), result_items[0]["chunk_text"], "")
