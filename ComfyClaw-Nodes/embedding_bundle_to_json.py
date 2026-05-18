"""Embedding_Bundle_To_JSON node."""

from __future__ import annotations

import json

from .common import require_string, serialize_json, string_input


def _reject_duplicate_pairs(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"Duplicate key found while parsing JSON: {key}")
        output[key] = value
    return output


class EmbeddingBundleToJSON:
    """Convert JSON object chunks from an embedding bundle into one root JSON object."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "convert_bundle"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_string", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "embedding_bundle_string": string_input(""),
            }
        }

    def convert_bundle(self, embedding_bundle_string):
        checked_bundle, bundle_error = require_string(embedding_bundle_string, "embedding_bundle_string")
        if bundle_error:
            return ("{}", bundle_error)
        if not checked_bundle.strip():
            return ("{}", "embedding_bundle_string cannot be empty.")

        try:
            bundle = json.loads(checked_bundle)
        except Exception as exc:
            return ("{}", f"embedding_bundle_string is not valid JSON: {exc}")

        chunks = bundle.get("chunks") if isinstance(bundle, dict) else None
        if not isinstance(chunks, list):
            return ("{}", "embedding_bundle_string does not contain a valid chunks list.")

        output: dict[str, object] = {}
        first_chunk_error = ""
        for index, chunk in enumerate(chunks):
            if not isinstance(chunk, str):
                return ("{}", f"Chunk {index} is not a string.")
            if not chunk.strip():
                continue
            try:
                parsed_chunk = json.loads(chunk, object_pairs_hook=_reject_duplicate_pairs)
            except Exception as exc:
                first_chunk_error = f"Chunk {index} is not valid JSON: {exc}"
                break
            if not isinstance(parsed_chunk, dict):
                first_chunk_error = f"Chunk {index} must be a JSON object."
                break

            for key, value in parsed_chunk.items():
                if key in output:
                    return ("{}", f"Duplicate root key found in chunk {index}: {key}")
                output[key] = value

        if not first_chunk_error:
            return (serialize_json(output), "")

        combined_chunks = "".join(chunk for chunk in chunks if isinstance(chunk, str))
        if not combined_chunks.strip():
            return ("{}", "No JSON text was found in embedding bundle chunks.")
        try:
            combined_output = json.loads(combined_chunks, object_pairs_hook=_reject_duplicate_pairs)
        except Exception as exc:
            return ("{}", f"{first_chunk_error}; Combined chunks are not valid JSON: {exc}")
        if not isinstance(combined_output, dict):
            return ("{}", "Combined chunks must form a JSON object.")

        return (serialize_json(combined_output), "")
