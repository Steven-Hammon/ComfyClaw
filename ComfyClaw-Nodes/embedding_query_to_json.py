"""Embedding_Query_To_JSON node."""

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


class EmbeddingQueryToJSON:
    """Convert embedding query result chunks into one root JSON object."""

    CATEGORY = "ComfyClaw/JSON"
    FUNCTION = "convert_query"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("json_output", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_input": string_input(""),
            }
        }

    def convert_query(self, json_input):
        checked_json, json_error = require_string(json_input, "json_input")
        if json_error:
            return ("{}", json_error)
        if not checked_json.strip():
            return ("{}", "json_input cannot be empty.")

        try:
            query_data = json.loads(checked_json)
        except Exception as exc:
            return ("{}", f"json_input is not valid JSON: {exc}")

        results = query_data.get("results") if isinstance(query_data, dict) else None
        if not isinstance(results, list):
            return ("{}", "json_input does not contain a valid results list.")

        output: dict[str, object] = {}
        for index, result in enumerate(results):
            if not isinstance(result, dict):
                return ("{}", f"Result {index} is not a JSON object.")
            chunk_text = result.get("chunk_text")
            if not isinstance(chunk_text, str):
                return ("{}", f"Result {index} chunk_text is not a string.")
            if not chunk_text.strip():
                continue

            try:
                parsed_chunk = json.loads(chunk_text, object_pairs_hook=_reject_duplicate_pairs)
            except Exception as exc:
                return ("{}", f"Result {index} chunk_text is not valid JSON: {exc}")
            if not isinstance(parsed_chunk, dict):
                return ("{}", f"Result {index} chunk_text must be a JSON object.")

            for key, value in parsed_chunk.items():
                if key in output:
                    return ("{}", f"Duplicate root key found in result {index}: {key}")
                output[key] = value

        return (serialize_json(output), "")
