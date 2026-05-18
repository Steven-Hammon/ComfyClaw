"""ComfyUI entrypoint for the full ComfyClaw repository layout."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import sys
from types import ModuleType


_ROOT = pathlib.Path(__file__).resolve().parent
_NODES_DIR = _ROOT / "ComfyClaw-Nodes"
_NODES_INIT = _NODES_DIR / "__init__.py"
_NODES_MODULE_NAME = "_comfyclaw_nodes_" + hashlib.sha1(str(_NODES_DIR).encode("utf-8")).hexdigest()[:12]


def _load_nodes_module() -> ModuleType:
    if not _NODES_INIT.exists():
        raise ImportError(f"ComfyClaw node package not found at {_NODES_INIT}")

    existing = sys.modules.get(_NODES_MODULE_NAME)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        _NODES_MODULE_NAME,
        _NODES_INIT,
        submodule_search_locations=[str(_NODES_DIR)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load ComfyClaw node package from {_NODES_INIT}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[_NODES_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


_nodes = _load_nodes_module()

NODE_CLASS_MAPPINGS = dict(_nodes.NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS = dict(_nodes.NODE_DISPLAY_NAME_MAPPINGS)
WEB_DIRECTORY = "./ComfyClaw-Nodes/web"

for _name, _value in vars(_nodes).items():
    if _name.startswith("_") or _name in {
        "NODE_CLASS_MAPPINGS",
        "NODE_DISPLAY_NAME_MAPPINGS",
        "WEB_DIRECTORY",
    }:
        continue
    globals()[_name] = _value

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
]
