"""Opt-in, bounded arithmetic reproduction; not a general experiment API."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Annotated, Literal, Protocol
from uuid import UUID, uuid4

from pydantic import Field

from researchforge.models import Artifact, FrozenModel, ResearchProject, ResearchState
from researchforge.protocols import ArtifactStore

Finite = Annotated[float, Field(allow_inf_nan=False)]
REQUEST_KIND = "baseline_execution_request"
RESULT_KIND = "baseline_execution_result"
RECEIPT_KIND = "baseline_reproduction_result"
HISTORY_KINDS = frozenset({REQUEST_KIND, RESULT_KIND, "baseline_stdout", "baseline_stderr"})


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class DatasetManifest(FrozenModel):
    schema_version: Literal[1] = 1
    name: Literal["fixed-numeric-input"] = "fixed-numeric-input"
    values: Annotated[tuple[Finite, ...], Field(min_length=1, max_length=1000)]

    def content(self) -> bytes:
        return self.model_dump_json().encode()


class BaselineProtocol(FrozenModel):
    schema_version: Literal[1] = 1
    version: Annotated[int, Field(ge=1)] = 1
    baseline: Literal["arithmetic-mean-v1"] = "arithmetic-mean-v1"
    dataset: DatasetManifest
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)] = 42
    reference_mean: Finite = 2.0
    absolute_tolerance: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 1e-12
    timeout_seconds: Annotated[int, Field(ge=1, le=30)] = 10


class ExecutionRequest(FrozenModel):
    schema_version: Literal[1] = 1
    execution_id: UUID = Field(default_factory=uuid4)
    protocol: BaselineProtocol
    image_id: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


class ExecutionResult(FrozenModel):
    schema_version: Literal[1] = 1
    execution_id: UUID
    request_artifact_id: UUID
    request_sha256: str
    dataset_sha256: str
    protocol_sha256: str
    environment_id: str
    exit_code: int | None
    timed_out: bool = False
    failure: str | None = None
    elapsed_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    stdout_artifact_id: UUID
    stderr_artifact_id: UUID


class ReproductionAssessment(FrozenModel):
    scope: Literal["V2 execution and fixed-reference metric agreement"] = (
        "V2 execution and fixed-reference metric agreement"
    )
    accepted: bool
    observed_mean: Finite | None = None
    reference_mean: Finite
    absolute_tolerance: Finite
    deviation: Finite | None = None
    reasons: tuple[str, ...]


class ReproductionReceipt(FrozenModel):
    schema_version: Literal[1] = 1
    request_artifact_id: UUID
    result_artifact_id: UUID
    assessment: ReproductionAssessment


class RunnerOutput(FrozenModel):
    exit_code: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    failure: str | None = None
    elapsed_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)] = 0.0


class BaselineRunner(Protocol):
    def execute(self, request: ExecutionRequest) -> RunnerOutput: ...


def assess(
    request: ExecutionRequest,
    *,
    exit_code: int | None,
    timed_out: bool,
    stdout: str,
    failure: str | None = None,
) -> ReproductionAssessment:
    protocol = request.protocol
    reasons: list[str] = []
    observed: float | None = None
    deviation: float | None = None
    if failure:
        reasons.append(failure)
    if timed_out:
        reasons.append("execution timed out")
    if exit_code != 0:
        reasons.append("execution did not exit successfully")
    try:
        payload = json.loads(stdout)
        if not isinstance(payload, dict) or set(payload) != {"mean"}:
            raise ValueError("expected one mean metric")
        value = payload["mean"]
        if type(value) not in (int, float):
            raise ValueError("metric must be numeric")
        observed = float(value)
        deviation = abs(observed - protocol.reference_mean)
        if not math.isfinite(observed) or not math.isfinite(deviation):
            raise ValueError("metric and deviation must be finite")
        if deviation > protocol.absolute_tolerance:
            reasons.append("reference deviation exceeds protocol tolerance")
    except (ValueError, TypeError, OverflowError):
        observed = deviation = None
        reasons.append("missing or invalid finite mean metric")
    return ReproductionAssessment(
        accepted=not reasons,
        observed_mean=observed,
        reference_mean=protocol.reference_mean,
        absolute_tolerance=protocol.absolute_tolerance,
        deviation=deviation,
        reasons=tuple(reasons),
    )


def requests(project: ResearchProject) -> tuple[Artifact, ...]:
    return tuple(item for item in project.artifacts if item.kind == REQUEST_KIND)


def validate_receipt(project: ResearchProject, store: ArtifactStore) -> tuple[str, ...]:
    """Recompute assessment; never trust the receipt's claimed acceptance flag."""
    pending = requests(project)
    if not pending:
        return ()  # Legacy simulation semantics are intentionally unchanged.
    request_artifact = pending[-1]
    request = ExecutionRequest.model_validate_json(store.get_bytes(request_artifact))
    artifacts = {item.artifact_id: item for item in project.artifacts}

    def linked(identifier: UUID, kind: str) -> Artifact:
        item = artifacts.get(identifier)
        if item is None or item.kind != kind:
            raise ValueError("missing or wrong-kind baseline provenance artifact")
        if not item.path.startswith(f"{project.project_id}/"):
            raise ValueError("baseline artifact belongs to another project")
        store.get_bytes(item)
        return item

    receipts = [item for item in project.artifacts if item.kind == RECEIPT_KIND]
    if not receipts:
        raise ValueError("latest baseline request has no receipt; interrupted or pending execution")
    receipt = ReproductionReceipt.model_validate_json(store.get_bytes(receipts[-1]))
    if receipt.request_artifact_id != request_artifact.artifact_id:
        raise ValueError("receipt does not assess the latest baseline request")
    result = ExecutionResult.model_validate_json(
        store.get_bytes(linked(receipt.result_artifact_id, RESULT_KIND))
    )
    if (
        result.execution_id != request.execution_id
        or result.request_artifact_id != request_artifact.artifact_id
        or result.request_sha256 != request_artifact.checksum
        or result.dataset_sha256 != digest(request.protocol.dataset.content())
        or result.protocol_sha256 != digest(request.protocol.model_dump_json().encode())
        or result.environment_id != request.image_id
    ):
        raise ValueError("baseline provenance linkage mismatch")
    stdout = store.get_bytes(linked(result.stdout_artifact_id, "baseline_stdout")).decode()
    linked(result.stderr_artifact_id, "baseline_stderr")
    assessment = assess(
        request,
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        stdout=stdout,
        failure=result.failure,
    )
    if assessment != receipt.assessment or not assessment.accepted:
        raise ValueError("baseline reproduction failed: " + "; ".join(assessment.reasons))
    return (assessment.scope, f"request {request.execution_id}; deviation={assessment.deviation}")


def preserve_execution_history(
    current: ResearchProject,
    snapshot: ResearchProject,
) -> tuple[Artifact, ...]:
    """Snapshot recovery must not erase enrollment, attempts, or their receipts."""
    if not requests(current):
        return snapshot.artifacts
    kinds = HISTORY_KINDS | {RECEIPT_KIND}
    historical_ids = {item.artifact_id for item in current.artifacts if item.kind in kinds}
    return tuple(
        item for item in snapshot.artifacts if item.artifact_id not in historical_ids
    ) + tuple(item for item in current.artifacts if item.kind in kinds)


def ensure_baseline_stage(project: ResearchProject) -> None:
    if project.state is not ResearchState.BASELINE_REPRODUCTION:
        raise ValueError("controlled reproduction requires baseline_reproduction state")
