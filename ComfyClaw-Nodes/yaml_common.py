"""Shared YAML helpers for ComfyClaw nodes."""

from __future__ import annotations

from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - depends on the user's ComfyUI environment.
    yaml = None


if yaml is not None:

    class LiteralSafeDumper(yaml.SafeDumper):
        """Safe YAML dumper that keeps repeated values expanded inline."""

        def ignore_aliases(self, data):
            return True


    def _represent_string(dumper, data):
        style = "|" if "\n" in data else None
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


    LiteralSafeDumper.add_representer(str, _represent_string)
else:
    LiteralSafeDumper = None


def _require_yaml():
    if yaml is None:
        raise RuntimeError("PyYAML is required for YAML nodes.")


def parse_yaml_string(yaml_text: str) -> Any:
    _require_yaml()
    return yaml.safe_load(yaml_text)


def _strip_document_end(yaml_text: str) -> str:
    lines = yaml_text.splitlines()
    if lines and lines[-1] == "...":
        lines = lines[:-1]
        return "\n".join(lines) + ("\n" if lines else "")
    return yaml_text


def serialize_yaml(data: Any) -> str:
    _require_yaml()
    yaml_text = yaml.dump(
        data,
        Dumper=LiteralSafeDumper,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    return _strip_document_end(yaml_text)
