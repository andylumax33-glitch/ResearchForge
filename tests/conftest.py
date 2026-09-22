from __future__ import annotations

from pathlib import Path

import pytest

from researchforge.artifacts import FileArtifactStore
from researchforge.repositories import SQLiteStateRepository
from researchforge.service import ResearchRuntime


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    path = tmp_path / "workspace"
    path.mkdir()
    return path


@pytest.fixture
def repository(workspace: Path) -> SQLiteStateRepository:
    return SQLiteStateRepository(workspace / "researchforge.db")


@pytest.fixture
def artifact_store(workspace: Path) -> FileArtifactStore:
    return FileArtifactStore(workspace / "artifacts")


@pytest.fixture
def service(
    repository: SQLiteStateRepository, artifact_store: FileArtifactStore
) -> ResearchRuntime:
    return ResearchRuntime(repository=repository, artifact_store=artifact_store)
