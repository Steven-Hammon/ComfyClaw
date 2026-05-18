"""Custom ComfyClaw provider datatypes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMProvider:
    """Carries LLM configuration for downstream call nodes."""

    api_base_url: str
    api_key: str
    model_name: str
    provider_kind: str


@dataclass(frozen=True)
class EmbeddingProvider:
    """Carries embedding configuration for downstream embedding nodes."""

    api_base_url: str
    api_key: str
    model_name: str
    provider_kind: str


@dataclass(frozen=True)
class MCPProvider:
    """Carries MCP server configuration for downstream MCP nodes."""

    server_url: str
    api_key: str
