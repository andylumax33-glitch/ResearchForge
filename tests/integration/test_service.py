from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from researchforge.fixtures import load_fixture_graph
from researchforge.models import ResearchProject, ResearchState
from researchforge.service import ApprovalRequiredError, ResearchRuntime, StageValidationError


def run_until(
    service: ResearchRuntime, project: ResearchProject, target: ResearchState
) -> ResearchProject:
    while project.state is not target:
        if project.state not in {
            ResearchState.INTAKE,
            ResearchState.HUMAN_APPROVAL,
            ResearchState.RELEASE,
        }:
            content = (
                load_fixture_graph().model_dump_json().encode()
                if project.state is ResearchState.LITERATURE_REVIEW
                else f"result for {project.state.value}".encode()
            )
            artifact = service.artifact_store.put_bytes(
                f"{project.project_id}/{project.state.value}.txt",
                content,
                kind=f"{project.state.value}_result",
            )
            project = service.add_artifact(project.project_id, artifact)
        project = service.advance(project.project_id, actor="mock").project
    return project


def test_failed_transition_is_atomic(service: ResearchRuntime) -> None:
    project = service.create_project("atomic", "Verify atomic transitions")

    with pytest.raises(StageValidationError):
        service.advance(project.project_id, actor="mock", verified=False)

    unchanged = service.get_project(project.project_id)
    assert unchanged.state is ResearchState.INTAKE
    assert unchanged.version == project.version
    assert unchanged.last_checkpoint_id == project.last_checkpoint_id


def test_human_approval_cannot_be_bypassed(service: ResearchRuntime) -> None:
    project = service.create_project("approval", "Verify release gate")
    project = run_until(service, project, ResearchState.HUMAN_APPROVAL)

    with pytest.raises(ApprovalRequiredError):
        service.advance(project.project_id, actor="mock")
    assert service.get_project(project.project_id).state is ResearchState.HUMAN_APPROVAL


def test_rejection_records_failure_and_does_not_release(service: ResearchRuntime) -> None:
    project = service.create_project("rejected", "Verify rejection")
    project = run_until(service, project, ResearchState.HUMAN_APPROVAL)

    rejected = service.reject(project.project_id, actor="owner", reason="insufficient evidence")

    assert rejected.state is ResearchState.HUMAN_APPROVAL
    assert rejected.failure_reason == "insufficient evidence"


def test_approval_then_advance_releases_project(service: ResearchRuntime) -> None:
    project = service.create_project("approved", "Verify approval")
    project = run_until(service, project, ResearchState.HUMAN_APPROVAL)

    approved = service.approve(project.project_id, actor="owner", reason="evidence accepted")
    released = service.advance(approved.project_id, actor="mock").project

    assert released.state is ResearchState.RELEASE


def test_duplicate_approval_is_rejected(service: ResearchRuntime) -> None:
    project = service.create_project("duplicate", "Reject duplicate decisions")
    project = run_until(service, project, ResearchState.HUMAN_APPROVAL)
    service.approve(project.project_id, actor="owner", reason="accepted")

    with pytest.raises(StageValidationError, match=r"already|decision"):
        service.approve(project.project_id, actor="owner", reason="accepted twice")


def test_export_contains_manifest_and_only_project_artifacts(
    service: ResearchRuntime, tmp_path: Path
) -> None:
    project = service.create_project("exportable", "Verify reproducible export")
    project = run_until(service, project, ResearchState.HUMAN_APPROVAL)
    archive = service.export(project.project_id, tmp_path / "bundle.zip")

    with ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert "manifest.json" in names
        assert all(not name.startswith(("/", "../")) and "/../" not in name for name in names)
        manifest = json.loads(bundle.read("manifest.json"))
        assert manifest["project_id"] == str(project.project_id)


def test_corrupted_stage_artifact_cannot_advance(service: ResearchRuntime, workspace: Path) -> None:
    project = service.create_project("integrity", "Reject corrupted evidence")
    project = service.advance(project.project_id, actor="mock").project
    artifact = service.artifact_store.put_bytes(
        f"{project.project_id}/scoping/result.txt", b"verified", kind="scoping_result"
    )
    project = service.add_artifact(project.project_id, artifact)
    (workspace / "artifacts" / artifact.path).write_bytes(b"tampered")

    with pytest.raises(ValueError, match="checksum mismatch"):
        service.advance(project.project_id, actor="mock")

    assert service.get_project(project.project_id).state is ResearchState.SCOPING


def test_literature_stage_rejects_unsupported_graph_without_advancing(
    service: ResearchRuntime,
) -> None:
    project = service.create_project("evidence", "Reject unsupported claims")
    project = service.advance(project.project_id, actor="mock").project
    project = service.submit_and_advance(
        project.project_id, actor="mock", filename="scope.txt", content=b"scope"
    ).project
    bad_graph = load_fixture_graph()
    bad_card = bad_graph.cards[0].model_copy(update={"quote": "invented observation"})
    bad_graph = bad_graph.model_copy(update={"cards": (bad_card,)})

    with pytest.raises(StageValidationError, match="verification failed"):
        service.submit_and_advance(
            project.project_id,
            actor="researcher",
            filename="evidence.json",
            content=bad_graph.model_dump_json().encode(),
        )

    unchanged = service.get_project(project.project_id)
    assert unchanged.state is ResearchState.LITERATURE_REVIEW
    assert unchanged.version == project.version

    artifact = service.artifact_store.put_bytes(
        f"{project.project_id}/literature_review/unsupported.json",
        bad_graph.model_dump_json().encode(),
        kind="literature_review_result",
    )
    with pytest.raises(StageValidationError, match="verification failed"):
        service.add_artifact(project.project_id, artifact)
    assert service.get_project(project.project_id).artifacts == project.artifacts


def test_resume_restores_full_snapshot_without_future_artifacts(
    service: ResearchRuntime,
) -> None:
    project = service.create_project("restore", "Restore an immutable snapshot")
    first = service.advance(project.project_id, actor="mock")
    project = first.project
    artifact = service.artifact_store.put_bytes(
        f"{project.project_id}/scoping/result.txt", b"verified", kind="scoping_result"
    )
    project = service.add_artifact(project.project_id, artifact)
    project = service.advance(project.project_id, actor="mock").project

    restored = service.resume(project.project_id, first.checkpoint.checkpoint_id)

    assert restored.state is ResearchState.INTAKE
    assert restored.artifacts == ()
    assert restored.approvals == ()
    assert restored.transitions[-1].actor == "system:resume"
