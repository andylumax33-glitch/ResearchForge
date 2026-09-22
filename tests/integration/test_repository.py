from __future__ import annotations

import pytest

from researchforge.models import Checkpoint, ResearchProject, ResearchState
from researchforge.repositories import ConcurrentUpdateError, SQLiteStateRepository


def test_sqlite_round_trip(repository: SQLiteStateRepository) -> None:
    created = ResearchProject(name="round-trip", goal="Verify persistence")
    repository.create(created)

    loaded = repository.get(created.project_id)

    assert loaded == created


def test_stale_version_cannot_overwrite_newer_project(
    repository: SQLiteStateRepository,
) -> None:
    created = ResearchProject(name="locking", goal="Verify optimistic locking")
    repository.create(created)
    first_reader = repository.get(created.project_id)
    stale_reader = repository.get(created.project_id)

    repository.save(
        first_reader.model_copy(update={"state": ResearchState.SCOPING, "version": 1}),
        expected_version=0,
    )

    with pytest.raises(ConcurrentUpdateError):
        repository.save(
            stale_reader.model_copy(update={"state": ResearchState.SCOPING, "version": 1}),
            expected_version=0,
        )
    assert repository.get(created.project_id).version == created.version + 1


def test_checkpoint_restores_previous_state(repository: SQLiteStateRepository) -> None:
    created = ResearchProject(name="restore", goal="Verify checkpoint recovery")
    repository.create(created)
    checkpoint = Checkpoint(
        project_id=created.project_id,
        state=created.state,
        project_version=created.version,
    )
    advanced = created.model_copy(
        update={
            "state": ResearchState.SCOPING,
            "version": 1,
            "last_checkpoint_id": checkpoint.checkpoint_id,
        }
    )
    repository.save_transition(advanced, checkpoint, expected_version=0)

    restored = repository.get_checkpoint(checkpoint.checkpoint_id)

    assert restored.state is ResearchState.INTAKE
    assert restored.project_version == created.version
