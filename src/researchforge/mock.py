"""Deterministic Phase 1 specialist used for demos and workflow tests."""

from __future__ import annotations

import hashlib

from researchforge.models import Artifact, ResearchProject, ResearchState


class MockResearchSpecialist:
    def execute(self, project: ResearchProject, state: ResearchState) -> tuple[Artifact, ...]:
        content = f"mock result for {project.project_id} at {state.value}".encode()
        return (
            Artifact(
                kind=f"{state.value}_result",
                path=f"{state.value}/result.txt",
                checksum=hashlib.sha256(content).hexdigest(),
                metadata=(("mock", "true"),),
            ),
        )
