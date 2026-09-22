"""Extension interfaces for storage, providers, specialists, and verification."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from researchforge.models import Artifact, Checkpoint, ResearchProject, ResearchState


class StateRepository(Protocol):
    def create(self, project: ResearchProject) -> None: ...
    def get(self, project_id: UUID) -> ResearchProject: ...
    def save(self, project: ResearchProject, *, expected_version: int) -> None: ...
    def save_transition(
        self, project: ResearchProject, checkpoint: Checkpoint, *, expected_version: int
    ) -> None: ...
    def get_checkpoint(self, checkpoint_id: UUID) -> Checkpoint: ...


class ArtifactStore(Protocol):
    def put_bytes(self, relative_path: str, content: bytes, *, kind: str) -> Artifact: ...
    def get_bytes(self, artifact: Artifact) -> bytes: ...
    def export_project(self, project: ResearchProject, destination: Path) -> Path: ...


class ModelProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


class LiteratureProvider(Protocol):
    def search(self, query: str) -> tuple[dict[str, Any], ...]: ...


class SandboxRunner(Protocol):
    def run(self, command: tuple[str, ...], workspace: Path) -> dict[str, Any]: ...


class ResearchSpecialist(Protocol):
    def execute(self, project: ResearchProject, state: ResearchState) -> tuple[Artifact, ...]: ...


class VerificationGate(Protocol):
    def verify(self, project: ResearchProject, state: ResearchState) -> tuple[bool, str | None]: ...
