"""Immutable domain contracts for the research runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResearchState(StrEnum):
    INTAKE = "intake"
    SCOPING = "scoping"
    LITERATURE_REVIEW = "literature_review"
    BASELINE_REPRODUCTION = "baseline_reproduction"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    EXPERIMENT_DESIGN = "experiment_design"
    IMPLEMENTATION = "implementation"
    EXPERIMENT_EXECUTION = "experiment_execution"
    ANALYSIS = "analysis"
    CRITIQUE = "critique"
    HUMAN_APPROVAL = "human_approval"
    RELEASE = "release"


class ApprovalStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class Artifact(FrozenModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    kind: str = Field(min_length=1, max_length=80)
    path: str = Field(min_length=1, max_length=500)
    checksum: str = Field(min_length=8, max_length=128)
    metadata: tuple[tuple[str, str], ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or "\\" in value:
            raise ValueError("artifact path must be a safe relative POSIX path")
        return value


class Evidence(FrozenModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    source_type: str
    source_uri: str
    locator: str | None = None
    content: str
    verified: bool = False


class Claim(FrozenModel):
    claim_id: UUID = Field(default_factory=uuid4)
    statement: str = Field(min_length=1)
    evidence_ids: tuple[UUID, ...] = ()
    status: str = "proposed"


class Budget(FrozenModel):
    token_limit: int = Field(default=0, ge=0)
    cost_limit_usd: float = Field(default=0, ge=0)
    compute_seconds_limit: int = Field(default=0, ge=0)
    tokens_used: int = Field(default=0, ge=0)
    cost_used_usd: float = Field(default=0, ge=0)
    compute_seconds_used: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_usage(self) -> Budget:
        limits_and_usage = (
            (self.token_limit, self.tokens_used),
            (self.cost_limit_usd, self.cost_used_usd),
            (self.compute_seconds_limit, self.compute_seconds_used),
        )
        if any(limit and used > limit for limit, used in limits_and_usage):
            raise ValueError("budget usage exceeds configured limit")
        return self


class ApprovalDecision(FrozenModel):
    status: ApprovalStatus
    actor: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    decided_at: datetime = Field(default_factory=utc_now)


class StageDefinition(FrozenModel):
    state: ResearchState
    required_inputs: frozenset[str] = frozenset()
    required_artifact_kinds: frozenset[str] = frozenset()
    verification_gates: tuple[str, ...] = ("artifact_integrity",)
    requires_approval: bool = False


class Checkpoint(FrozenModel):
    checkpoint_id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    state: ResearchState
    project_version: int = Field(ge=0)
    parent_checkpoint_id: UUID | None = None
    project_snapshot_json: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class TransitionRecord(FrozenModel):
    from_state: ResearchState
    to_state: ResearchState
    actor: str
    input_version: int = Field(ge=0)
    output_artifact_ids: tuple[UUID, ...] = ()
    verified: bool
    verification_details: tuple[str, ...] = ()
    budget_snapshot: Budget = Field(default_factory=Budget)
    failure_reason: str | None = None
    parent_checkpoint_id: UUID | None = None
    occurred_at: datetime = Field(default_factory=utc_now)


class ResearchProject(FrozenModel):
    project_id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1, max_length=2000)
    state: ResearchState = ResearchState.INTAKE
    version: int = Field(default=0, ge=0)
    budget: Budget = Field(default_factory=Budget)
    artifacts: tuple[Artifact, ...] = ()
    approvals: tuple[ApprovalDecision, ...] = ()
    transitions: tuple[TransitionRecord, ...] = ()
    last_checkpoint_id: UUID | None = None
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TransitionResult(FrozenModel):
    project: ResearchProject
    checkpoint: Checkpoint
    record: TransitionRecord
