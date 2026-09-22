"""Metadata-only boundary for independently generated Paper2Agent tools."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator

from researchforge.literature import validate_public_https
from researchforge.models import FrozenModel


class Paper2AgentManifest(FrozenModel):
    paper_uri: str
    provenance_uri: str
    mcp_server_uri: str
    tool_names: tuple[str, ...] = Field(min_length=1)

    @field_validator("paper_uri", "provenance_uri", "mcp_server_uri")
    @classmethod
    def validate_uri(cls, value: str) -> str:
        return validate_public_https(value)

    @field_validator("tool_names")
    @classmethod
    def validate_tools(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(
            not name or len(name) > 100 or not name.replace("_", "").isalnum() for name in value
        ):
            raise ValueError("tool names must be nonempty identifiers")
        if len(value) != len(set(value)):
            raise ValueError("tool names must be unique")
        return value


class ExternalPaperTool(FrozenModel):
    provider: str = "Paper2Agent"
    paper_uri: str
    provenance_uri: str
    mcp_server_uri: str
    tool_names: tuple[str, ...]


class Paper2AgentAdapter:
    @staticmethod
    def from_manifest(path: Path) -> ExternalPaperTool:
        if not path.is_file() or path.stat().st_size > 65_536:
            raise ValueError("Paper2Agent manifest missing or too large")
        manifest = Paper2AgentManifest.model_validate_json(path.read_bytes())
        return ExternalPaperTool(**manifest.model_dump())
