from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from researchforge.artifacts import FileArtifactStore
from researchforge.baseline import (
    BaselineProtocol,
    DatasetManifest,
    ExecutionRequest,
    ExecutionResult,
    RunnerOutput,
    assess,
    requests,
)
from researchforge.docker_runner import DockerBaselineRunner
from researchforge.fixtures import load_fixture_graph
from researchforge.models import Budget, ResearchProject, ResearchState
from researchforge.repositories import SQLiteStateRepository
from researchforge.service import ResearchRuntime, StageValidationError


def at_baseline(service: ResearchRuntime, budget: Budget | None = None) -> ResearchProject:
    project = service.create_project("baseline", "fixed reference agreement", budget=budget)
    service.advance(project.project_id, actor="fixture")
    service.submit_and_advance(
        project.project_id,
        actor="fixture",
        filename="scope.txt",
        content=b"fixed arithmetic fixture",
    )
    return service.submit_and_advance(
        project.project_id,
        actor="fixture",
        filename="literature.json",
        content=load_fixture_graph().model_dump_json().encode(),
    ).project


def request() -> ExecutionRequest:
    return ExecutionRequest(
        protocol=BaselineProtocol(dataset=DatasetManifest(values=(1.0, 2.0, 3.0))),
        image_id="sha256:" + "a" * 64,
    )


class FakeRunner:
    """Test double only; never used by production CLI."""

    def __init__(self, output: RunnerOutput | None = None) -> None:
        self.output = output or RunnerOutput(exit_code=0, stdout='{"mean":2.0}')

    def execute(self, request: ExecutionRequest) -> RunnerOutput:
        return self.output


def test_assessment_is_scoped_to_reference_and_tolerance() -> None:
    protocol = BaselineProtocol(dataset=DatasetManifest(values=(1.0, 2.0, 3.0)))
    request = ExecutionRequest(protocol=protocol, image_id="sha256:" + "a" * 64)
    assessment = assess(request, exit_code=0, timed_out=False, stdout='{"mean":2.0}')
    assert assessment.accepted
    assert assessment.deviation == 0.0
    assert not assess(request, exit_code=0, timed_out=False, stdout='{"mean":9}').accepted
    assert not assess(request, exit_code=1, timed_out=False, stdout='{"mean":2}').accepted


def test_success_persists_linked_artifacts_and_gate_advances(service: ResearchRuntime) -> None:
    project = at_baseline(service)
    receipt = service.reproduce_baseline(project.project_id, request(), FakeRunner())
    assert receipt.assessment.accepted
    recorded = service.get_project(project.project_id)
    assert recorded.state is ResearchState.BASELINE_REPRODUCTION
    assert len(recorded.artifacts) == len(project.artifacts) + 5
    result = service.advance(project.project_id, actor="operator")
    assert result.project.state is ResearchState.HYPOTHESIS_GENERATION
    assert "fixed-reference" in result.record.verification_details[0]


@pytest.mark.parametrize(
    "output",
    [
        RunnerOutput(exit_code=1, stdout='{"mean":2}'),
        RunnerOutput(exit_code=None, timed_out=True),
        RunnerOutput(exit_code=0, stdout='{"mean":8}'),
        RunnerOutput(exit_code=0, stdout='{"mean":NaN}'),
        RunnerOutput(exit_code=0, stdout='{"mean":true}'),
        RunnerOutput(exit_code=0, stdout='{"mean":"2"}'),
        RunnerOutput(exit_code=0, stdout="[]"),
        RunnerOutput(exit_code=0, stdout="{}"),
        RunnerOutput(exit_code=0, stdout="not json"),
        RunnerOutput(exit_code=0, stdout='{"mean":2}', failure="backend failed"),
    ],
)
def test_failure_is_durable_and_cannot_be_overridden(
    service: ResearchRuntime,
    output: RunnerOutput,
) -> None:
    project = at_baseline(service)
    receipt = service.reproduce_baseline(project.project_id, request(), FakeRunner(output))
    assert not receipt.assessment.accepted
    before = service.get_project(project.project_id)
    assert before.failure_reason
    with pytest.raises(StageValidationError):
        service.advance(project.project_id, actor="human", verified=True)
    with pytest.raises(StageValidationError):
        service.approve(project.project_id, actor="human", reason="ignore failure")
    assert service.get_project(project.project_id) == before


def test_latest_request_cannot_reuse_success(service: ResearchRuntime) -> None:
    project = at_baseline(service)
    service.reproduce_baseline(project.project_id, request(), FakeRunner())
    service.reproduce_baseline(project.project_id, request(), FakeRunner(RunnerOutput(exit_code=2)))
    with pytest.raises(StageValidationError):
        service.advance(project.project_id, actor="operator")
    with pytest.raises(StageValidationError):
        service.submit_and_advance(
            project.project_id, actor="mock", filename="mock.txt", content=b"looks good"
        )


def test_pending_attempt_survives_restart_and_cannot_pass(service: ResearchRuntime) -> None:
    class InterruptedRunner:
        def execute(self, request: ExecutionRequest) -> RunnerOutput:
            raise RuntimeError("simulated process interruption")

    project = at_baseline(service)
    with pytest.raises(RuntimeError):
        service.reproduce_baseline(project.project_id, request(), InterruptedRunner())
    restarted = ResearchRuntime(service.repository, service.artifact_store)
    assert requests(restarted.get_project(project.project_id))
    with pytest.raises(StageValidationError, match="no receipt"):
        restarted.advance(project.project_id, actor="operator")


def test_recovery_preserves_attempts_and_does_not_refund_budget(service: ResearchRuntime) -> None:
    project = at_baseline(service, Budget(compute_seconds_limit=10))
    assert project.last_checkpoint_id is not None
    service.reproduce_baseline(project.project_id, request(), FakeRunner())
    restored = service.resume(project.project_id, project.last_checkpoint_id)
    assert requests(restored)
    # Return via the existing forward state transition, not a scientific revision.
    service.submit_and_advance(
        project.project_id,
        actor="operator",
        filename="literature.json",
        content=load_fixture_graph().model_dump_json().encode(),
    )
    with pytest.raises(StageValidationError, match="budget"):
        service.reproduce_baseline(project.project_id, request(), FakeRunner())


def test_duplicate_execution_id_rejected(service: ResearchRuntime) -> None:
    project = at_baseline(service)
    attempt = request()
    service.reproduce_baseline(project.project_id, attempt, FakeRunner())
    with pytest.raises(StageValidationError, match="new ID"):
        service.reproduce_baseline(project.project_id, attempt, FakeRunner())


def test_linked_log_tampering_blocks_gate(service: ResearchRuntime, workspace: Path) -> None:
    project = at_baseline(service)
    service.reproduce_baseline(project.project_id, request(), FakeRunner())
    recorded = service.get_project(project.project_id)
    log = next(a for a in recorded.artifacts if a.kind == "baseline_stdout")
    (workspace / "artifacts" / log.path).write_bytes(b'{"mean":2}')
    with pytest.raises(StageValidationError, match="checksum"):
        service.advance(project.project_id, actor="operator")


def test_mismatched_provenance_and_forged_receipt_rejected(service: ResearchRuntime) -> None:
    project = at_baseline(service)
    receipt = service.reproduce_baseline(project.project_id, request(), FakeRunner())
    recorded = service.get_project(project.project_id)
    result_artifact = next(a for a in recorded.artifacts if a.kind == "baseline_execution_result")
    result = ExecutionResult.model_validate_json(service.artifact_store.get_bytes(result_artifact))
    forged = result.model_copy(update={"execution_id": uuid4()})
    wrong = service.artifact_store.put_bytes(
        f"{project.project_id}/forged.json",
        forged.model_dump_json().encode(),
        kind="baseline_execution_result",
    )
    service.add_artifact(project.project_id, wrong)
    altered = receipt.model_copy(update={"result_artifact_id": wrong.artifact_id})
    artifact = service.artifact_store.put_bytes(
        f"{project.project_id}/receipt.json",
        altered.model_dump_json().encode(),
        kind="baseline_reproduction_result",
    )
    service.add_artifact(project.project_id, artifact)
    with pytest.raises(StageValidationError, match="linkage"):
        service.advance(project.project_id, actor="operator")


def test_export_and_reopen_preserve_new_payloads(service: ResearchRuntime, workspace: Path) -> None:
    project = at_baseline(service)
    service.reproduce_baseline(project.project_id, request(), FakeRunner())
    service.export(project.project_id, workspace / "bundle.zip")
    reopened = ResearchRuntime(
        SQLiteStateRepository(workspace / "researchforge.db"),
        FileArtifactStore(workspace / "artifacts"),
    )
    assert reopened.advance(project.project_id, actor="operator").project.state == (
        ResearchState.HYPOTHESIS_GENERATION
    )


@pytest.mark.skipif(not os.environ.get("RF_DOCKER_IMAGE"), reason="requires real Docker image ID")
def test_real_docker_baseline(service: ResearchRuntime) -> None:
    project = at_baseline(service)
    attempt = request().model_copy(update={"image_id": os.environ["RF_DOCKER_IMAGE"]})
    receipt = service.reproduce_baseline(project.project_id, attempt, DockerBaselineRunner())
    assert receipt.assessment.accepted, receipt.assessment.reasons
    service.advance(project.project_id, actor="docker-integration")
