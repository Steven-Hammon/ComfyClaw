"""Token_Estimator node."""

from __future__ import annotations

import re

from .common import float_input, string_input


class TokenEstimator:
    """Estimate token count from word count and a multiplier."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "estimate_tokens"
    RETURN_TYPES = ("INT", "STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = (
        "token_estimate_int",
        "token_estimate_string",
        "word_count_string",
        "character_count",
        "error_string",
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": string_input(""),
                "ratio": float_input(1.3, step=0.05),
            }
        }

    def estimate_tokens(self, input_text, ratio=1.3):
        if not isinstance(input_text, str):
            return (0, "0", "0", 0, "")
        character_count = len(input_text)
        if not isinstance(ratio, (int, float)):
            return (0, "0", "0", character_count, "ratio must be numeric.")
        word_count = len(re.findall(r"\S+", input_text))
        if ratio <= 0:
            return (0, "0", str(word_count), character_count, "ratio must be greater than 0.")
        token_estimate = int(round(word_count * float(ratio)))
        return (token_estimate, str(token_estimate), str(word_count), character_count, "")
