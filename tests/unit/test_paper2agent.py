from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from researchforge.paper2agent import Paper2AgentAdapter, Paper2AgentManifest


def test_manifest_is_metadata_only(tmp_path: Path) -> None:
    path = tmp_path / "paper2agent.json"
    path.write_text(
        json.dumps(
            {
                "paper_uri": "https://doi.org/10.1/demo",
                "provenance_uri": "https://github.com/jmiao24/Paper2Agent",
                "mcp_server_uri": "https://example.org/mcp",
                "tool_names": ["analyze_data"],
            }
        )
    )
    descriptor = Paper2AgentAdapter.from_manifest(path)
    assert descriptor.tool_names == ("analyze_data",)
    assert descriptor.provider == "Paper2Agent"


def test_manifest_rejects_local_endpoint_and_oversized_file(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        Paper2AgentManifest(
            paper_uri="https://doi.org/10.1/demo",
            provenance_uri="https://github.com/jmiao24/Paper2Agent",
            mcp_server_uri="http://localhost:8000/mcp",
            tool_names=("run",),
        )
    path = tmp_path / "oversized.json"
    path.write_bytes(b"x" * 65537)
    with pytest.raises(ValueError, match="too large"):
        Paper2AgentAdapter.from_manifest(path)
