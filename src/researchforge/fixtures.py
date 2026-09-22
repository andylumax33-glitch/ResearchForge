"""Bounded loading of evidence graph documents and packaged evaluation fixture."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from researchforge.evidence import EvidenceGraph


def load_graph_bytes(data: bytes) -> EvidenceGraph:
    if len(data) > 1_000_000:
        raise ValueError("evidence graph exceeds 1 MB")
    return EvidenceGraph.model_validate_json(data)


def load_graph(path: Path) -> EvidenceGraph:
    if not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError("evidence graph missing or too large")
    return load_graph_bytes(path.read_bytes())


def load_fixture_graph() -> EvidenceGraph:
    data = files("researchforge").joinpath("data/literature_fixture.json").read_bytes()
    return load_graph_bytes(data)
