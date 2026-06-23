"""PyAutoGUI desktop-control node with lightweight OCR grounding."""

from __future__ import annotations

import ast
import json
import os
import queue
import shutil
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import combo_input, float_input, int_input, string_input


OCR_ENGINES = ("PaddleOCR", "EasyOCR", "Tesseract")

_ALLOWED_PYAUTOGUI_COMMANDS = frozenset(
    {
        "click",
        "doubleClick",
        "tripleClick",
        "rightClick",
        "middleClick",
        "moveTo",
        "moveRel",
        "move",
        "dragTo",
        "dragRel",
        "scroll",
        "hscroll",
        "vscroll",
        "press",
        "keyDown",
        "keyUp",
        "hotkey",
        "write",
        "typewrite",
        "mouseDown",
        "mouseUp",
        "screenshot",
    }
)
_SCREENSHOT_COMMANDS = frozenset({"screenshot"})
_OCR_CACHE: dict[str, Any] = {}
_OCR_CACHE_LOCK = threading.Lock()
_TESSERACT_EXE_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)
_PADDLE_SAFE_CPU_ENV = {
    "PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT": "0",
}


@dataclass(frozen=True)
class _ParsedCommand:
    name: str
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


def _join_errors(errors: list[str]) -> str:
    return "; ".join(error for error in errors if error)


def _extract_command_name(func_node: ast.AST) -> str | None:
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute) and isinstance(func_node.value, ast.Name):
        if func_node.value.id == "pyautogui":
            return func_node.attr
    return None


def _literal_eval_arg(node: ast.AST, label: str) -> tuple[Any, str]:
    try:
        return ast.literal_eval(node), ""
    except Exception as exc:
        return None, f"{label} must be a Python literal value: {exc}"


def _parse_wait_command(command_string: str) -> tuple[bool, float, str]:
    stripped = command_string.strip()
    if not stripped:
        return False, 0.0, ""
    if stripped.lower() == "wait":
        return True, 0.0, ""

    try:
        expression = ast.parse(stripped, mode="eval").body
    except SyntaxError:
        return False, 0.0, ""

    if not isinstance(expression, ast.Call) or _extract_command_name(expression.func) != "wait":
        return False, 0.0, ""
    if expression.keywords:
        return True, 0.0, "wait only accepts one optional positional seconds value."
    if len(expression.args) > 1:
        return True, 0.0, "wait only accepts one optional seconds value."
    if not expression.args:
        return True, 0.0, ""

    seconds_value, error = _literal_eval_arg(expression.args[0], "wait seconds")
    if error:
        return True, 0.0, error
    if not isinstance(seconds_value, (int, float)) or isinstance(seconds_value, bool):
        return True, 0.0, "wait seconds must be a number."
    if seconds_value < 0:
        return True, 0.0, "wait seconds cannot be negative."
    return True, float(seconds_value), ""


def _parse_pyautogui_command(command_string: str) -> tuple[_ParsedCommand | None, str]:
    stripped = command_string.strip()
    if not stripped:
        return None, ""

    try:
        expression = ast.parse(stripped, mode="eval").body
    except SyntaxError as exc:
        return None, f"invalid PyAutoGUI command: {exc.msg}."

    if not isinstance(expression, ast.Call):
        return None, "invalid PyAutoGUI command: expected a function call like click(742,381)."

    command_name = _extract_command_name(expression.func)
    if command_name not in _ALLOWED_PYAUTOGUI_COMMANDS:
        allowed = ", ".join(sorted(_ALLOWED_PYAUTOGUI_COMMANDS))
        return None, f"unsupported PyAutoGUI command. Allowed commands: {allowed}."

    args: list[Any] = []
    for index, arg_node in enumerate(expression.args, start=1):
        if isinstance(arg_node, ast.Starred):
            return None, "starred arguments are not supported."
        value, error = _literal_eval_arg(arg_node, f"argument {index}")
        if error:
            return None, error
        args.append(value)

    kwargs: dict[str, Any] = {}
    for keyword_node in expression.keywords:
        if keyword_node.arg is None:
            return None, "expanded keyword arguments are not supported."
        value, error = _literal_eval_arg(keyword_node.value, f"keyword {keyword_node.arg}")
        if error:
            return None, error
        kwargs[keyword_node.arg] = value

    return _ParsedCommand(name=command_name, args=tuple(args), kwargs=kwargs), ""


def _import_pyautogui():
    import pyautogui

    return pyautogui


def _import_pil_image():
    from PIL import Image

    return Image


def _to_int_pair(value: Any) -> tuple[int, int] | None:
    if hasattr(value, "x") and hasattr(value, "y"):
        return int(value.x), int(value.y)
    try:
        return int(value[0]), int(value[1])
    except Exception:
        return None


def _get_desktop_state(pyautogui_module: Any | None, screenshot_image: Any) -> tuple[list[int], list[int], list[str]]:
    errors: list[str] = []
    fallback_width, fallback_height = screenshot_image.size
    resolution = [int(fallback_width), int(fallback_height)]
    cursor = [0, 0]

    if pyautogui_module is None:
        return resolution, cursor, errors

    try:
        screen_size = _to_int_pair(pyautogui_module.size())
        if screen_size is not None:
            resolution = [screen_size[0], screen_size[1]]
    except Exception as exc:
        errors.append(f"could not read desktop resolution: {exc}")

    try:
        position = _to_int_pair(pyautogui_module.position())
        if position is not None:
            cursor = [position[0], position[1]]
    except Exception as exc:
        errors.append(f"could not read cursor position: {exc}")

    if resolution[0] > 0 and resolution[1] > 0:
        if cursor[0] < 0 or cursor[1] < 0 or cursor[0] >= resolution[0] or cursor[1] >= resolution[1]:
            errors.append(f"cursor out of bounds: cursor={cursor}, resolution={resolution}")

    return resolution, cursor, errors


def _resolve_image_path(path_text: str) -> Path:
    expanded = os.path.expandvars(path_text.strip())
    path = Path(expanded).expanduser()
    if path.is_absolute():
        return path
    return Path.cwd() / path


def _load_optional_image(path_text: str, role: str, errors: list[str]) -> Any | None:
    if not isinstance(path_text, str) or not path_text.strip():
        return None

    Image = _import_pil_image()
    path = _resolve_image_path(path_text)
    if not path.exists():
        errors.append(f"{role} image load failure: file not found at {path}")
        return None

    try:
        with Image.open(path) as image:
            return image.convert("RGBA").copy()
    except Exception as exc:
        errors.append(f"{role} image load failure: {exc}")
        return None


def _coerce_screenshot_image(result: Any, parsed_command: _ParsedCommand | None = None) -> Any | None:
    Image = _import_pil_image()
    if isinstance(result, Image.Image):
        return result.copy()
    if isinstance(result, (str, os.PathLike)):
        path = _resolve_image_path(str(result))
        if path.exists():
            with Image.open(path) as image:
                return image.copy()
    if parsed_command and parsed_command.args and isinstance(parsed_command.args[0], (str, os.PathLike)):
        path = _resolve_image_path(str(parsed_command.args[0]))
        if path.exists():
            with Image.open(path) as image:
                return image.copy()
    return None


def _capture_screenshot(pyautogui_module: Any) -> Any:
    image = _coerce_screenshot_image(pyautogui_module.screenshot())
    if image is None:
        raise RuntimeError("PyAutoGUI did not return a screenshot image.")
    return image


def _execute_pyautogui_command(
    pyautogui_module: Any | None,
    command_string: str,
) -> tuple[bool, Any | None, str]:
    parsed_command, parse_error = _parse_pyautogui_command(command_string)
    if parse_error:
        return False, None, parse_error
    if parsed_command is None:
        return False, None, ""

    is_screenshot_command = parsed_command.name in _SCREENSHOT_COMMANDS
    if pyautogui_module is None:
        return is_screenshot_command, None, "PyAutoGUI is not available."

    try:
        pyautogui_function = getattr(pyautogui_module, parsed_command.name)
        result = pyautogui_function(*parsed_command.args, **parsed_command.kwargs)
        if is_screenshot_command:
            image = _coerce_screenshot_image(result, parsed_command)
            if image is None:
                return True, None, "screenshot command did not return or save an image."
            return True, image, ""
        return False, None, ""
    except Exception as exc:
        return is_screenshot_command, None, f"PyAutoGUI command failed: {exc}"


def _blank_image(width: int = 1, height: int = 1) -> Any:
    Image = _import_pil_image()
    return Image.new("RGB", (max(1, int(width)), max(1, int(height))), (0, 0, 0))


def _paste_layer(canvas: Any, layer: Any, x: int, y: int) -> None:
    rgba_layer = layer.convert("RGBA")
    canvas.paste(rgba_layer, (int(x), int(y)), rgba_layer)


def _layer_extent(width: int, height: int, x: int = 0, y: int = 0) -> tuple[int, int]:
    return max(width, width + int(x)), max(height, height + int(y))


def _composite_image(
    screenshot_image: Any,
    background_image: Any | None,
    overlay_image: Any | None,
    cursor_image: Any | None,
    cursor: list[int],
    screenshot_offset_x: int,
    screenshot_offset_y: int,
    cursor_offset_x: int,
    cursor_offset_y: int,
) -> Any:
    Image = _import_pil_image()
    screenshot_rgba = screenshot_image.convert("RGBA")
    extents = [
        _layer_extent(screenshot_rgba.width, screenshot_rgba.height, screenshot_offset_x, screenshot_offset_y),
    ]
    if background_image is not None:
        extents.append((background_image.width, background_image.height))
    if overlay_image is not None:
        extents.append((overlay_image.width, overlay_image.height))

    final_width = max(1, *(width for width, _ in extents))
    final_height = max(1, *(height for _, height in extents))
    canvas = Image.new("RGBA", (final_width, final_height), (0, 0, 0, 0))

    if background_image is not None:
        _paste_layer(canvas, background_image, 0, 0)
    _paste_layer(canvas, screenshot_rgba, screenshot_offset_x, screenshot_offset_y)
    if overlay_image is not None:
        _paste_layer(canvas, overlay_image, 0, 0)
    if cursor_image is not None:
        cursor_x = screenshot_offset_x + cursor[0] + int(cursor_offset_x)
        cursor_y = screenshot_offset_y + cursor[1] + int(cursor_offset_y)
        _paste_layer(canvas, cursor_image, cursor_x, cursor_y)

    return canvas


def _pil_to_comfy_image(image: Any) -> Any:
    import numpy as np
    import torch

    rgb_image = image.convert("RGB")
    array = np.asarray(rgb_image).astype(np.float32) / 255.0
    return torch.from_numpy(array)[None,]


def _to_builtin(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "to_dict"):
        try:
            return value.to_dict()
        except Exception:
            pass
    if hasattr(value, "res"):
        try:
            return value.res
        except Exception:
            pass
    return value


def _first_mapping_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _bbox_from_points(value: Any) -> list[int] | None:
    value = _to_builtin(value)
    if not isinstance(value, (list, tuple)):
        return None

    if len(value) == 4 and all(_is_number(item) for item in value):
        x1, y1, x2, y2 = value
        return [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))]

    points: list[tuple[float, float]] = []
    for point in value:
        point = _to_builtin(point)
        if isinstance(point, (list, tuple)) and len(point) >= 2 and _is_number(point[0]) and _is_number(point[1]):
            points.append((float(point[0]), float(point[1])))

    if not points:
        return None

    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [
        int(round(min(xs))),
        int(round(min(ys))),
        int(round(max(xs))),
        int(round(max(ys))),
    ]


def _confidence_to_float(confidence: Any) -> float:
    try:
        value = float(confidence)
    except Exception:
        return 0.0
    if value < 0:
        return 0.0
    if value > 1.0:
        value = value / 100.0
    return max(0.0, min(1.0, value))


def _make_ocr_entry(text: Any, bbox: Any, confidence: Any) -> dict[str, Any] | None:
    bbox_values = _bbox_from_points(bbox)
    if bbox_values is None:
        return None

    normalized_text = " ".join(str(text).split())
    if not normalized_text:
        return None

    x1, y1, x2, y2 = bbox_values
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1

    return {
        "text": normalized_text,
        "bbox": [x1, y1, x2, y2],
        "confidence": round(_confidence_to_float(confidence), 4),
    }


def _normalize_generic_ocr_result(raw_result: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    def walk(value: Any) -> None:
        value = _to_builtin(value)
        if isinstance(value, Mapping):
            texts = _to_builtin(_first_mapping_value(value, "rec_texts", "texts"))
            scores = _to_builtin(_first_mapping_value(value, "rec_scores", "scores", "confidences"))
            boxes = _to_builtin(_first_mapping_value(value, "rec_polys", "dt_polys", "rec_boxes", "boxes"))
            if isinstance(texts, (list, tuple)) and isinstance(scores, (list, tuple)) and isinstance(boxes, (list, tuple)):
                for index, text in enumerate(texts):
                    if index >= len(scores) or index >= len(boxes):
                        break
                    entry = _make_ocr_entry(text, boxes[index], scores[index])
                    if entry is not None:
                        entries.append(entry)
                return
            for nested_value in value.values():
                walk(nested_value)
            return

        if not isinstance(value, (list, tuple)):
            return

        if len(value) >= 2:
            bbox = _bbox_from_points(value[0])
            if bbox is not None:
                if isinstance(value[1], (list, tuple)) and len(value[1]) >= 2:
                    entry = _make_ocr_entry(value[1][0], bbox, value[1][1])
                    if entry is not None:
                        entries.append(entry)
                    return
                if len(value) >= 3:
                    entry = _make_ocr_entry(value[1], bbox, value[2])
                    if entry is not None:
                        entries.append(entry)
                    return

        for nested_value in value:
            walk(nested_value)

    walk(raw_result)
    return entries


def _configure_paddle_safe_cpu_env() -> None:
    for name, value in _PADDLE_SAFE_CPU_ENV.items():
        os.environ.setdefault(name, value)


def _paddle_ocr_init_kwargs() -> tuple[dict[str, Any], ...]:
    v3_safe_cpu = {
        "lang": "en",
        "device": "cpu",
        "engine": "paddle_static",
        "enable_mkldnn": False,
        "enable_cinn": False,
        "engine_config": {
            "run_mode": "paddle",
            "enable_new_ir": False,
            "enable_cinn": False,
            "cpu_threads": 4,
        },
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
    }
    return (
        v3_safe_cpu,
        {
            "lang": "en",
            "device": "cpu",
            "engine": "paddle_static",
            "enable_mkldnn": False,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {
            "lang": "en",
            "device": "cpu",
            "enable_mkldnn": False,
            "use_doc_orientation_classify": False,
            "use_doc_unwarping": False,
            "use_textline_orientation": False,
        },
        {"use_angle_cls": False, "lang": "en", "show_log": False},
        {"use_angle_cls": False, "lang": "en"},
        {"lang": "en"},
        {},
    )


def _get_cached_ocr_engine(engine_name: str) -> Any:
    with _OCR_CACHE_LOCK:
        cached_engine = _OCR_CACHE.get(engine_name)
        if cached_engine is not None:
            return cached_engine

        if engine_name == "PaddleOCR":
            _configure_paddle_safe_cpu_env()
            from paddleocr import PaddleOCR

            last_init_error: Exception | None = None
            for kwargs in _paddle_ocr_init_kwargs():
                try:
                    cached_engine = PaddleOCR(**kwargs)
                    break
                except (TypeError, ValueError) as exc:
                    last_init_error = exc
            if cached_engine is None:
                raise last_init_error or RuntimeError("Could not initialize PaddleOCR.")
        elif engine_name == "EasyOCR":
            import easyocr

            cached_engine = easyocr.Reader(["en"], gpu=False)
        else:
            raise ValueError(f"unsupported OCR engine: {engine_name}")

        _OCR_CACHE[engine_name] = cached_engine
        return cached_engine


def _image_to_numpy(image: Any) -> Any:
    import numpy as np

    return np.asarray(image.convert("RGB"))


def _run_paddle_ocr(image: Any) -> list[dict[str, Any]]:
    ocr = _get_cached_ocr_engine("PaddleOCR")
    image_array = _image_to_numpy(image)
    if hasattr(ocr, "predict"):
        try:
            raw_result = list(ocr.predict(input=image_array))
        except TypeError:
            raw_result = list(ocr.predict(image_array))
        return _normalize_generic_ocr_result(raw_result)
    try:
        raw_result = ocr.ocr(image_array, cls=False)
    except TypeError:
        raw_result = ocr.ocr(image_array)
    return _normalize_generic_ocr_result(raw_result)


def _run_easyocr(image: Any) -> list[dict[str, Any]]:
    reader = _get_cached_ocr_engine("EasyOCR")
    raw_result = reader.readtext(_image_to_numpy(image))
    return _normalize_generic_ocr_result(raw_result)


def _resolve_tesseract_exe_path(tesseract_exe_path: str = "") -> str | None:
    configured_path = str(tesseract_exe_path or "").strip().strip("\"'")
    if configured_path:
        resolved = Path(os.path.expandvars(configured_path)).expanduser()
        if resolved.is_dir():
            resolved = resolved / "tesseract.exe"
        if not resolved.exists():
            raise FileNotFoundError(f"tesseract_exe_path does not exist: {resolved}")
        return str(resolved)

    path_match = shutil.which("tesseract")
    if path_match:
        return path_match

    for candidate in _TESSERACT_EXE_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


def _configure_tesseract_exe_path(pytesseract_module: Any, tesseract_exe_path: str = "") -> None:
    resolved_path = _resolve_tesseract_exe_path(tesseract_exe_path)
    if resolved_path:
        pytesseract_module.pytesseract.tesseract_cmd = resolved_path


def _run_tesseract(image: Any, tesseract_exe_path: str = "") -> list[dict[str, Any]]:
    import pytesseract

    _configure_tesseract_exe_path(pytesseract, tesseract_exe_path)
    rgb_image = image.convert("RGB")
    raw_data = pytesseract.image_to_data(rgb_image, output_type=pytesseract.Output.DICT)
    entries: list[dict[str, Any]] = []
    total = len(raw_data.get("text", []))
    for index in range(total):
        text = raw_data["text"][index]
        confidence = raw_data["conf"][index]
        try:
            left = int(float(raw_data["left"][index]))
            top = int(float(raw_data["top"][index]))
            width = int(float(raw_data["width"][index]))
            height = int(float(raw_data["height"][index]))
        except Exception:
            continue
        entry = _make_ocr_entry(text, [left, top, left + width, top + height], confidence)
        if entry is not None:
            entries.append(entry)
    return entries


def _run_ocr(engine_name: str, image: Any, tesseract_exe_path: str = "") -> list[dict[str, Any]]:
    if engine_name == "PaddleOCR":
        return _run_paddle_ocr(image)
    if engine_name == "EasyOCR":
        return _run_easyocr(image)
    if engine_name == "Tesseract":
        return _run_tesseract(image, tesseract_exe_path)
    raise ValueError(f"unsupported OCR engine: {engine_name}")


def _run_ocr_with_timeout(
    engine_name: str,
    image: Any,
    timeout_seconds: int,
    tesseract_exe_path: str = "",
) -> tuple[list[dict[str, Any]], str]:
    result_queue: queue.Queue[tuple[list[dict[str, Any]], str]] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            result_queue.put((_run_ocr(engine_name, image, tesseract_exe_path), ""))
        except Exception as exc:
            result_queue.put(([], f"OCR engine failure: {exc}"))

    thread = threading.Thread(target=worker, name=f"ComfyClawOCR-{engine_name}", daemon=True)
    thread.start()

    try:
        return result_queue.get(timeout=max(1, int(timeout_seconds)))
    except queue.Empty:
        return [], f"OCR timeout after {timeout_seconds} seconds."


def _filter_ocr_entries(
    entries: list[dict[str, Any]],
    max_text_chars: int,
    max_box_width: int,
    max_box_height: int,
    min_confidence: float,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for entry in entries:
        text = str(entry.get("text", "")).strip()
        bbox = entry.get("bbox")
        confidence = _confidence_to_float(entry.get("confidence", 0.0))
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        x1, y1, x2, y2 = [int(value) for value in bbox]
        width = max(0, x2 - x1)
        height = max(0, y2 - y1)
        if not text:
            continue
        if len(text) > int(max_text_chars):
            continue
        if width > int(max_box_width):
            continue
        if height > int(max_box_height):
            continue
        if confidence < float(min_confidence):
            continue
        filtered.append(
            {
                "text": text,
                "bbox": [x1, y1, x2, y2],
                "confidence": round(confidence, 4),
            }
        )
    return filtered


def _build_ocr_json(resolution: list[int], cursor: list[int], ocr_entries: list[dict[str, Any]]) -> str:
    payload = {
        "resolution": [int(resolution[0]), int(resolution[1])],
        "cursor": [int(cursor[0]), int(cursor[1])],
        "ocr": ocr_entries,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class PyAutoGUISimpleOCR:
    """Run one PyAutoGUI action and return a composited screenshot plus normalized OCR JSON."""

    CATEGORY = "ComfyClaw/System"
    FUNCTION = "run_desktop_step"
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "OCR_JSON", "error_string")
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "command_string": string_input("", multiline=False),
                "ocr_engine": combo_input(OCR_ENGINES, default="Tesseract"),
                "max_text_chars": int_input(15, min=1),
                "max_box_width": int_input(320, min=1),
                "max_box_height": int_input(80, min=1),
                "min_confidence": float_input(0.5, min=0.0, max=1.0, step=0.01),
                "OCR_timeout": int_input(10, min=1),
                "tesseract_exe_path": string_input("", multiline=False),
                "bg_img_path": string_input("", multiline=False),
                "overlay_img_path": string_input("", multiline=False),
                "cursor_img_path": string_input("", multiline=False),
                "screenshot_offset_x": int_input(0),
                "screenshot_offset_y": int_input(0),
                "cursor_offset_x": int_input(0, min=-10000, max=10000),
                "cursor_offset_y": int_input(0, min=-10000, max=10000),
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

    def run_desktop_step(
        self,
        command_string: str = "",
        ocr_engine: str = "Tesseract",
        max_text_chars: int = 15,
        max_box_width: int = 320,
        max_box_height: int = 80,
        min_confidence: float = 0.5,
        OCR_timeout: int = 10,
        tesseract_exe_path: str = "",
        bg_img_path: str = "",
        overlay_img_path: str = "",
        cursor_img_path: str = "",
        screenshot_offset_x: int = 0,
        screenshot_offset_y: int = 0,
        cursor_offset_x: int = 0,
        cursor_offset_y: int = 0,
    ):
        errors: list[str] = []
        if ocr_engine not in OCR_ENGINES:
            errors.append(f"ocr_engine must be one of: {', '.join(OCR_ENGINES)}")
            ocr_engine = "Tesseract"

        try:
            pyautogui_module = _import_pyautogui()
        except Exception as exc:
            pyautogui_module = None
            errors.append(f"PyAutoGUI import failure: {exc}")

        command_text = command_string if isinstance(command_string, str) else ""
        is_wait_command, wait_seconds, wait_error = _parse_wait_command(command_text)
        screenshot_command_image = None
        skip_automatic_screenshot = False

        if is_wait_command:
            if wait_error:
                errors.append(wait_error)
            elif wait_seconds > 0:
                time.sleep(wait_seconds)
        else:
            skip_automatic_screenshot, screenshot_command_image, command_error = _execute_pyautogui_command(
                pyautogui_module,
                command_text,
            )
            if command_error:
                errors.append(command_error)

        screenshot_image = screenshot_command_image
        if screenshot_image is None and not skip_automatic_screenshot:
            if pyautogui_module is None:
                errors.append("screenshot failure: PyAutoGUI is not available.")
            else:
                try:
                    screenshot_image = _capture_screenshot(pyautogui_module)
                except Exception as exc:
                    errors.append(f"screenshot failure: {exc}")

        if screenshot_image is None:
            screenshot_image = _blank_image()

        resolution, cursor, state_errors = _get_desktop_state(pyautogui_module, screenshot_image)
        errors.extend(state_errors)

        ocr_entries: list[dict[str, Any]] = []
        ocr_error = ""
        if ocr_engine in OCR_ENGINES:
            ocr_entries, ocr_error = _run_ocr_with_timeout(
                ocr_engine,
                screenshot_image,
                OCR_timeout,
                tesseract_exe_path=tesseract_exe_path,
            )
        if ocr_error:
            errors.append(ocr_error)

        filtered_ocr_entries = _filter_ocr_entries(
            ocr_entries,
            max_text_chars=max_text_chars,
            max_box_width=max_box_width,
            max_box_height=max_box_height,
            min_confidence=min_confidence,
        )
        ocr_json = _build_ocr_json(resolution, cursor, filtered_ocr_entries)

        if skip_automatic_screenshot:
            output_image = screenshot_image
        else:
            background_image = _load_optional_image(bg_img_path, "background", errors)
            overlay_image = _load_optional_image(overlay_img_path, "overlay", errors)
            cursor_image = _load_optional_image(cursor_img_path, "cursor", errors)
            try:
                output_image = _composite_image(
                    screenshot_image=screenshot_image,
                    background_image=background_image,
                    overlay_image=overlay_image,
                    cursor_image=cursor_image,
                    cursor=cursor,
                    screenshot_offset_x=screenshot_offset_x,
                    screenshot_offset_y=screenshot_offset_y,
                    cursor_offset_x=cursor_offset_x,
                    cursor_offset_y=cursor_offset_y,
                )
            except Exception as exc:
                errors.append(f"image composite failure: {exc}")
                output_image = screenshot_image

        try:
            comfy_image = _pil_to_comfy_image(output_image)
        except Exception as exc:
            errors.append(f"image output conversion failure: {exc}")
            comfy_image = _pil_to_comfy_image(_blank_image())

        return (comfy_image, ocr_json, _join_errors(errors))
