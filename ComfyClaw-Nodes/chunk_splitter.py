"""ChunkSplitter node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .common import DEFAULT_CHUNK_BREAK_MARKER, combo_input, count_units, int_input, require_string, serialize_json, string_input, take_prefix_by_unit

_SPLIT_TYPES = ["characters", "words", "paragraphs", "custom"]


@dataclass(frozen=True)
class _SplitConfig:
    amount: int
    split_type: str
    markers: tuple[str, ...]


@dataclass(frozen=True)
class _LimitConfig:
    minimum: int
    maximum: int
    split_type: str
    markers: tuple[str, ...]


class ChunkSplitter:
    """Split long text into bounded chunks with overlap taken from the next main chunk."""

    CATEGORY = "ComfyClaw/Embedding"
    FUNCTION = "split_text"
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("chunks_text", "chunks_json", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_text": string_input(""),
                "main_chunk_min": int_input(5, min=1, max=999999),
                "main_chunk_split_type": combo_input(_SPLIT_TYPES, default="paragraphs"),
                "main_chunk_marker_1": string_input("", multiline=False),
                "main_chunk_marker_2": string_input("", multiline=False),
                "main_chunk_marker_3": string_input("", multiline=False),
                "main_chunk_marker_4": string_input("", multiline=False),
                "main_chunk_marker_5": string_input("", multiline=False),
                "chunk_limit_min": int_input(1, min=1, max=999999),
                "chunk_limit_max": int_input(30, min=1, max=999999),
                "chunk_limit_split_type": combo_input(_SPLIT_TYPES, default="paragraphs"),
                "chunk_limit_marker_1": string_input("", multiline=False),
                "chunk_limit_marker_2": string_input("", multiline=False),
                "chunk_limit_marker_3": string_input("", multiline=False),
                "chunk_limit_marker_4": string_input("", multiline=False),
                "chunk_limit_marker_5": string_input("", multiline=False),
                "chunk_overlap_min": int_input(0, min=0, max=999999),
                "chunk_overlap_split_type": combo_input(_SPLIT_TYPES, default="paragraphs"),
                "chunk_overlap_marker_1": string_input("", multiline=False),
                "chunk_overlap_marker_2": string_input("", multiline=False),
                "chunk_overlap_marker_3": string_input("", multiline=False),
                "chunk_overlap_marker_4": string_input("", multiline=False),
                "chunk_overlap_marker_5": string_input("", multiline=False),
            }
        }

    def split_text(
        self,
        input_text,
        main_chunk_min=5,
        main_chunk_split_type="paragraphs",
        main_chunk_marker_1="",
        main_chunk_marker_2="",
        main_chunk_marker_3="",
        main_chunk_marker_4="",
        main_chunk_marker_5="",
        chunk_limit_min=1,
        chunk_limit_max=30,
        chunk_limit_split_type="paragraphs",
        chunk_limit_marker_1="",
        chunk_limit_marker_2="",
        chunk_limit_marker_3="",
        chunk_limit_marker_4="",
        chunk_limit_marker_5="",
        chunk_overlap_min=0,
        chunk_overlap_split_type="paragraphs",
        chunk_overlap_marker_1="",
        chunk_overlap_marker_2="",
        chunk_overlap_marker_3="",
        chunk_overlap_marker_4="",
        chunk_overlap_marker_5="",
    ):
        checked_text, text_error = require_string(input_text, "input_text")
        main_type, main_type_error = self._normalize_split_type(main_chunk_split_type, "main_chunk_split_type")
        limit_type, limit_type_error = self._normalize_split_type(chunk_limit_split_type, "chunk_limit_split_type")
        overlap_type, overlap_type_error = self._normalize_split_type(chunk_overlap_split_type, "chunk_overlap_split_type")
        if text_error or main_type_error or limit_type_error or overlap_type_error:
            return ("", "", "; ".join(error for error in (text_error, main_type_error, limit_type_error, overlap_type_error) if error))
        if checked_text == "":
            return ("", "", "input_text was empty.")
        if not isinstance(main_chunk_min, int) or main_chunk_min < 1:
            return ("", "", "main_chunk_min must be an integer greater than 0.")
        if not isinstance(chunk_limit_min, int) or chunk_limit_min < 1:
            return ("", "", "chunk_limit_min must be an integer greater than 0.")
        if not isinstance(chunk_limit_max, int) or chunk_limit_max < 1:
            return ("", "", "chunk_limit_max must be an integer greater than 0.")
        if chunk_limit_min > chunk_limit_max:
            return ("", "", "chunk_limit_min cannot be greater than chunk_limit_max.")
        if not isinstance(chunk_overlap_min, int) or chunk_overlap_min < 0:
            return ("", "", "chunk_overlap_min must be an integer greater than or equal to 0.")

        main_markers, main_marker_error = self._normalize_markers(
            [main_chunk_marker_1, main_chunk_marker_2, main_chunk_marker_3, main_chunk_marker_4, main_chunk_marker_5],
            "main_chunk_marker",
        )
        limit_markers, limit_marker_error = self._normalize_markers(
            [chunk_limit_marker_1, chunk_limit_marker_2, chunk_limit_marker_3, chunk_limit_marker_4, chunk_limit_marker_5],
            "chunk_limit_marker",
        )
        overlap_markers, overlap_marker_error = self._normalize_markers(
            [chunk_overlap_marker_1, chunk_overlap_marker_2, chunk_overlap_marker_3, chunk_overlap_marker_4, chunk_overlap_marker_5],
            "chunk_overlap_marker",
        )
        if main_marker_error or limit_marker_error or overlap_marker_error:
            return ("", "", "; ".join(error for error in (main_marker_error, limit_marker_error, overlap_marker_error) if error))

        if main_type == "custom" and not main_markers:
            return ("", "", "At least one main_chunk_marker is required when main_chunk_split_type is custom.")
        if limit_type == "custom" and not limit_markers:
            return ("", "", "At least one chunk_limit_marker is required when chunk_limit_split_type is custom.")
        if overlap_type == "custom" and chunk_overlap_min > 0 and not overlap_markers:
            return ("", "", "At least one chunk_overlap_marker is required when chunk_overlap_split_type is custom.")

        main_config = _SplitConfig(main_chunk_min, main_type, tuple(main_markers))
        limit_config = _LimitConfig(chunk_limit_min, chunk_limit_max, limit_type, tuple(limit_markers))
        overlap_config = _SplitConfig(chunk_overlap_min, overlap_type, tuple(overlap_markers))

        chunks: list[str] = []
        remaining_text = checked_text
        while remaining_text:
            main_chunk_text = self._build_main_chunk(remaining_text, main_config, limit_config)
            if not main_chunk_text:
                main_chunk_text = remaining_text

            remaining_after_main = remaining_text[len(main_chunk_text) :]
            overlap_text = self._take_prefix_for_config(remaining_after_main, overlap_config)
            chunks.append(main_chunk_text + overlap_text)

            if not remaining_after_main:
                break
            remaining_text = remaining_after_main

        return (DEFAULT_CHUNK_BREAK_MARKER.join(chunks), serialize_json(chunks), "")

    def _build_main_chunk(self, text: str, main_config: _SplitConfig, limit_config: _LimitConfig) -> str:
        total_main_units = self._count_units_for_config(text, main_config)
        if total_main_units <= 0:
            return text

        current_main_units = min(main_config.amount, total_main_units)
        candidate = self._take_prefix(text, main_config.split_type, current_main_units, main_config.markers)
        if not candidate:
            candidate = text
        candidate_limit_units = self._count_units(text=candidate, split_type=limit_config.split_type, markers=limit_config.markers)

        while candidate != text and candidate_limit_units < limit_config.minimum:
            next_main_units = current_main_units + 1
            next_candidate = self._take_prefix(text, main_config.split_type, next_main_units, main_config.markers)
            if next_candidate == candidate:
                break
            candidate = next_candidate
            current_main_units = next_main_units
            candidate_limit_units = self._count_units(text=candidate, split_type=limit_config.split_type, markers=limit_config.markers)

        while current_main_units > 1 and candidate_limit_units > limit_config.maximum:
            next_main_units = current_main_units - 1
            next_candidate = self._take_prefix(text, main_config.split_type, next_main_units, main_config.markers)
            if not next_candidate or next_candidate == candidate:
                break
            candidate = next_candidate
            current_main_units = next_main_units
            candidate_limit_units = self._count_units(text=candidate, split_type=limit_config.split_type, markers=limit_config.markers)

        if candidate_limit_units > limit_config.maximum:
            limited_candidate = self._take_prefix(text, limit_config.split_type, limit_config.maximum, limit_config.markers)
            if limited_candidate:
                candidate = limited_candidate

        return candidate or text

    def _count_units_for_config(self, text: str, config: _SplitConfig) -> int:
        return self._count_units(text, config.split_type, config.markers)

    def _take_prefix_for_config(self, text: str, config: _SplitConfig) -> str:
        return self._take_prefix(text, config.split_type, config.amount, config.markers)

    def _count_units(self, text: str, split_type: str, markers: Sequence[str]) -> int:
        if split_type == "custom":
            return len(self._split_custom_units(text, markers))
        return count_units(text, split_type)

    def _take_prefix(self, text: str, split_type: str, amount: int, markers: Sequence[str]) -> str:
        if amount <= 0 or not text:
            return ""
        if split_type == "custom":
            units = self._split_custom_units(text, markers)
            if not units:
                return ""
            if amount >= len(units):
                return text
            return "".join(units[:amount])
        return take_prefix_by_unit(text, split_type, amount)

    def _split_custom_units(self, text: str, markers: Sequence[str]) -> list[str]:
        if not text:
            return []
        starts = self._find_custom_starts(text, markers)
        if not starts:
            return [text]

        units: list[str] = []
        preamble = text[: starts[0]]
        for index, start in enumerate(starts):
            end = starts[index + 1] if index + 1 < len(starts) else len(text)
            unit = text[start:end]
            if index == 0 and preamble:
                unit = preamble + unit
            if unit:
                units.append(unit)
        return units or [text]

    def _find_custom_starts(self, text: str, markers: Sequence[str]) -> list[int]:
        starts: set[int] = set()
        for marker in markers:
            if not marker:
                continue
            cursor = 0
            while True:
                index = text.find(marker, cursor)
                if index == -1:
                    break
                starts.add(index)
                cursor = index + max(1, len(marker))
        return sorted(starts)

    def _normalize_split_type(self, value, field_name: str) -> tuple[str, str]:
        checked_value, value_error = require_string(value, field_name)
        if value_error:
            return ("", value_error)
        normalized = checked_value.strip().lower()
        if normalized not in _SPLIT_TYPES:
            return ("", f"{field_name} must be one of: {', '.join(_SPLIT_TYPES)}.")
        return (normalized, "")

    def _normalize_markers(self, values: Sequence[object], field_prefix: str) -> tuple[list[str], str]:
        markers: list[str] = []
        for index, value in enumerate(values, start=1):
            checked_value, value_error = require_string(value, f"{field_prefix}_{index}")
            if value_error:
                return ([], value_error)
            if checked_value == "":
                continue
            markers.append(checked_value)
        return (markers, "")
