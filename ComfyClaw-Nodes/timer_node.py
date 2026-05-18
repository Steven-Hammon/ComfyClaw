"""Timer_Node node."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from .common import bool_input, combo_input, float_input, int_input, resolve_text_path, string_input

_RESET_LATCHES: dict[str, bool] = {}


class TimerNode:
    """Emit a string when an interval or clock schedule has elapsed."""

    CATEGORY = "ComfyClaw/Utility"
    FUNCTION = "evaluate_timer"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_text_out", "error_string")

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "output_text": string_input("timer fired"),
                "mode": combo_input(["interval", "clock"], default="interval"),
                "every_mins": int_input(30, min=1),
                "target_time": string_input("09:30", multiline=False),
                "reset_ratio": float_input(0.5, step=0.05),
                "state_file_path": string_input("timer_state.json", multiline=False),
                "reset": bool_input(False, label_on="yes", label_off="no"),
            },
            "hidden": {"unique_id": "UNIQUE_ID"},
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def _fresh_state(self):
        return {"last_fired": None, "last_fired_date": None}

    def _resolve_state_path(self, state_file_path):
        if not isinstance(state_file_path, str):
            return None
        trimmed = state_file_path.strip()
        if trimmed == "":
            trimmed = "timer_state.json"
        return resolve_text_path(trimmed)

    def _read_state(self, state_path):
        if not state_path.exists():
            return self._fresh_state(), "missing"
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("State JSON must be an object.")
            return data, None
        except Exception:
            return self._fresh_state(), "invalid"

    def _write_json_state(self, state_path, state):
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _write_state(self, state_path, now):
        self._write_json_state(
            state_path,
            {
                "last_fired": now.isoformat(),
                "last_fired_date": now.date().isoformat(),
            },
        )

    def _ensure_state_file(self, state_path):
        state, status = self._read_state(state_path)
        if status == "missing":
            self._write_json_state(state_path, state)
            return state, "State file was missing and was created as a fresh timer state."
        if status == "invalid":
            self._write_json_state(state_path, state)
            return state, "State file was invalid and was fixed as a fresh timer state."
        return state, ""

    def _get_reset_key(self, unique_id, state_path):
        if unique_id is not None:
            return str(unique_id)
        return str(state_path)

    def evaluate_timer(
        self,
        output_text="timer fired",
        mode="interval",
        every_mins=30,
        target_time="09:30",
        reset_ratio=0.5,
        state_file_path="timer_state.json",
        reset=False,
        unique_id=None,
    ):
        if not isinstance(output_text, str):
            return ("", "output_text must be a string.")
        if not isinstance(state_file_path, str):
            return ("", "state_file_path must be a string.")
        if not isinstance(reset, bool):
            return ("", "reset must be a boolean.")
        if not isinstance(reset_ratio, (int, float)):
            return ("", "reset_ratio must be numeric.")

        warning = ""
        ratio = float(reset_ratio)
        if ratio <= 0.0 or ratio > 1.0:
            ratio = 0.5
            warning = "reset_ratio was invalid and was treated as 0.5."

        state_path = self._resolve_state_path(state_file_path)
        if state_path is None:
            return ("", "state_file_path must be a string.")

        try:
            state_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return ("", f"Could not create timer state directory: {exc}")

        try:
            state, state_warning = self._ensure_state_file(state_path)
        except Exception as exc:  # pragma: no cover - filesystem dependent
            return ("", f"Could not prepare timer state: {exc}")

        reset_key = self._get_reset_key(unique_id, state_path)
        previous_reset_value = _RESET_LATCHES.get(reset_key, False)
        _RESET_LATCHES[reset_key] = reset
        if reset and not previous_reset_value:
            try:
                self._write_json_state(state_path, self._fresh_state())
            except Exception as exc:  # pragma: no cover - filesystem dependent
                return ("", f"Could not reset timer state: {exc}")
            reset_message = "Timer state was reset."
            if state_warning:
                return ("", f"{state_warning}; {reset_message}")
            return ("", reset_message)

        now = datetime.now().astimezone()
        last_fired_text = state.get("last_fired")
        last_fired_date = state.get("last_fired_date")
        last_fired = None
        if isinstance(last_fired_text, str):
            try:
                last_fired = datetime.fromisoformat(last_fired_text)
            except Exception:
                last_fired = None

        if last_fired is None:
            last_fired = now - timedelta(days=3650)

        should_fire = False
        if mode == "clock":
            try:
                target_hour, target_minute = [int(part) for part in target_time.split(":", 1)]
                target_matches = now.hour == target_hour and now.minute == target_minute
            except Exception:
                return ("", "target_time must be a valid HH:MM string.")

            reset_window = timedelta(minutes=(24 * 60) * ratio)
            same_day = last_fired_date == now.date().isoformat()
            should_fire = target_matches and not same_day and (now - last_fired) >= reset_window
        else:
            if not isinstance(every_mins, int) or every_mins <= 0:
                return ("", "every_mins must be a positive integer.")
            reset_window = timedelta(minutes=every_mins * ratio)
            should_fire = (now - last_fired) >= reset_window and (now - last_fired) >= timedelta(minutes=every_mins)

        if should_fire:
            try:
                self._write_state(state_path, now)
            except Exception as exc:  # pragma: no cover - filesystem dependent
                return ("", f"Could not write timer state: {exc}")
            return (output_text, warning)

        if state_warning and warning:
            return ("", f"{state_warning}; {warning}")
        return ("", state_warning or warning)
