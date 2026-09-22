"""Application service coordinating workflow, validation, and atomic persistence."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from researchforge.evidence import answer_claims
from researchforge.fixtures import load_graph_bytes
from researchforge.models import (
    ApprovalDecision,
    ApprovalStatus,
    Artifact,
    Budget,
    Checkpoint,
    ResearchProject,
    ResearchState,
    TransitionRecord,
    TransitionResult,
    utc_now,
)
from researchforge.protocols import ArtifactStore, StateRepository
from researchforge.state_machine import DEFAULT_STAGES, next_state, validate_transition


class StageValidationError(ValueError):
    pass


class ApprovalRequiredError(StageValidationError):
    pass


class ResearchRuntime:
    def __init__(self, repository: StateRepository, artifact_store: ArtifactStore) -> None:
        self.repository = repository
        self.artifact_store = artifact_store

    def create_project(
        self, name: str, goal: str, *, budget: Budget | None = None
    ) -> ResearchProject:
        project = ResearchProject(name=name, goal=goal, budget=budget or Budget())
        self.repository.create(project)
        return project

    def get_project(self, project_id: UUID) -> ResearchProject:
        return self.repository.get(project_id)

    def add_artifact(self, project_id: UUID, artifact: Artifact) -> ResearchProject:
        project = self.repository.get(project_id)
        self._validate_artifact(project, artifact)
        if (
            project.state is ResearchState.LITERATURE_REVIEW
            and artifact.kind == "literature_review_result"
        ):
            self._validate_literature_artifact(artifact)
        updated = project.model_copy(
            update={
                "artifacts": (*project.artifacts, artifact),
                "version": project.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated, expected_version=project.version)
        return updated

    def advance(
        self,
        project_id: UUID,
        *,
        actor: str,
        target: ResearchState | None = None,
        verified: bool = True,
    ) -> TransitionResult:
        project = self.repository.get(project_id)
        return self._advance_loaded(project, actor=actor, target=target, verified=verified)

    def submit_and_advance(
        self,
        project_id: UUID,
        *,
        actor: str,
        filename: str,
        content: bytes,
    ) -> TransitionResult:
        """Store an immutable stage result and commit it with the transition in one DB write."""
        project = self.repository.get(project_id)
        destination = next_state(project.state)
        validate_transition(project.state, destination)
        if not DEFAULT_STAGES[project.state].required_artifact_kinds:
            return self._advance_loaded(project, actor=actor, verified=True)
        if project.state is ResearchState.LITERATURE_REVIEW:
            self._validate_literature_content(content)
        artifact = self.artifact_store.put_bytes(
            f"{project.project_id}/{project.state.value}/{filename}",
            content,
            kind=f"{project.state.value}_result",
        )
        self._validate_artifact(project, artifact)
        return self._advance_loaded(
            project,
            actor=actor,
            verified=True,
            new_artifacts=(artifact,),
        )

    def _advance_loaded(
        self,
        project: ResearchProject,
        *,
        actor: str,
        verified: bool,
        target: ResearchState | None = None,
        new_artifacts: tuple[Artifact, ...] = (),
    ) -> TransitionResult:
        destination = target or next_state(project.state)
        validate_transition(project.state, destination)
        candidate = project.model_copy(update={"artifacts": (*project.artifacts, *new_artifacts)})
        verification_details = self._validate_exit(candidate, verified=verified)
        checkpoint = Checkpoint(
            project_id=project.project_id,
            state=project.state,
            project_version=project.version,
            parent_checkpoint_id=project.last_checkpoint_id,
            project_snapshot_json=project.model_dump_json(),
        )
        required_kinds = DEFAULT_STAGES[project.state].required_artifact_kinds
        output_ids = tuple(item.artifact_id for item in new_artifacts) or tuple(
            item.artifact_id for item in candidate.artifacts if item.kind in required_kinds
        )
        record = TransitionRecord(
            from_state=project.state,
            to_state=destination,
            actor=actor,
            input_version=project.version,
            output_artifact_ids=output_ids,
            verified=verified,
            verification_details=verification_details,
            budget_snapshot=project.budget,
            parent_checkpoint_id=project.last_checkpoint_id,
        )
        updated = candidate.model_copy(
            update={
                "state": destination,
                "version": project.version + 1,
                "transitions": (*project.transitions, record),
                "last_checkpoint_id": checkpoint.checkpoint_id,
                "failure_reason": None,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_transition(updated, checkpoint, expected_version=project.version)
        return TransitionResult(project=updated, checkpoint=checkpoint, record=record)

    def approve(self, project_id: UUID, *, actor: str, reason: str) -> ResearchProject:
        return self._decide(project_id, ApprovalStatus.APPROVED, actor=actor, reason=reason)

    def reject(self, project_id: UUID, *, actor: str, reason: str) -> ResearchProject:
        return self._decide(project_id, ApprovalStatus.REJECTED, actor=actor, reason=reason)

    def _decide(
        self, project_id: UUID, status: ApprovalStatus, *, actor: str, reason: str
    ) -> ResearchProject:
        project = self.repository.get(project_id)
        if project.state is not ResearchState.HUMAN_APPROVAL:
            raise StageValidationError("approval decisions are only valid at human_approval")
        if project.approvals:
            raise StageValidationError("an approval decision has already been recorded")
        decision = ApprovalDecision(status=status, actor=actor, reason=reason)
        updated = project.model_copy(
            update={
                "approvals": (*project.approvals, decision),
                "failure_reason": reason if status is ApprovalStatus.REJECTED else None,
                "version": project.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated, expected_version=project.version)
        return updated

    def fail(self, project_id: UUID, *, reason: str) -> ResearchProject:
        project = self.repository.get(project_id)
        updated = project.model_copy(
            update={
                "failure_reason": reason,
                "version": project.version + 1,
                "updated_at": utc_now(),
            }
        )
        self.repository.save(updated, expected_version=project.version)
        return updated

    def resume(self, project_id: UUID, checkpoint_id: UUID) -> ResearchProject:
        project = self.repository.get(project_id)
        checkpoint = self.repository.get_checkpoint(checkpoint_id)
        if checkpoint.project_id != project.project_id:
            raise StageValidationError("checkpoint belongs to a different project")
        if checkpoint.project_snapshot_json is None:
            raise StageValidationError("checkpoint does not contain a restorable snapshot")
        snapshot = ResearchProject.model_validate_json(checkpoint.project_snapshot_json)
        resume_checkpoint = Checkpoint(
            project_id=project.project_id,
            state=project.state,
            project_version=project.version,
            parent_checkpoint_id=project.last_checkpoint_id,
            project_snapshot_json=project.model_dump_json(),
        )
        resume_record = TransitionRecord(
            from_state=project.state,
            to_state=snapshot.state,
            actor="system:resume",
            input_version=project.version,
            verified=True,
            verification_details=(f"restored checkpoint {checkpoint.checkpoint_id}",),
            budget_snapshot=snapshot.budget,
            parent_checkpoint_id=project.last_checkpoint_id,
        )
        updated = snapshot.model_copy(
            update={
                "version": project.version + 1,
                "transitions": (*snapshot.transitions, resume_record),
                "last_checkpoint_id": resume_checkpoint.checkpoint_id,
                "failure_reason": None,
                "updated_at": utc_now(),
            }
        )
        self.repository.save_transition(
            updated, resume_checkpoint, expected_version=project.version
        )
        return updated

    def export(self, project_id: UUID, destination: Path) -> Path:
        return self.artifact_store.export_project(self.repository.get(project_id), destination)

    def _validate_exit(self, project: ResearchProject, *, verified: bool) -> tuple[str, ...]:
        if not verified:
            raise StageValidationError("verification gate did not pass")
        stage = DEFAULT_STAGES[project.state]
        actual_kinds = {artifact.kind for artifact in project.artifacts}
        missing = stage.required_artifact_kinds - actual_kinds
        if missing:
            raise StageValidationError(f"missing required artifacts: {', '.join(sorted(missing))}")
        verified_paths: list[str] = []
        for artifact in project.artifacts:
            if artifact.kind in stage.required_artifact_kinds:
                self._validate_artifact(project, artifact)
                if project.state is ResearchState.LITERATURE_REVIEW:
                    self._validate_literature_artifact(artifact)
                verified_paths.append(artifact.path)
        if project.state is ResearchState.HUMAN_APPROVAL and (
            not project.approvals or project.approvals[-1].status is not ApprovalStatus.APPROVED
        ):
            raise ApprovalRequiredError("release requires the latest human decision to be approved")
        return tuple(f"verified artifact {path}" for path in verified_paths) or (
            "stage contract verified",
        )

    def _validate_artifact(self, project: ResearchProject, artifact: Artifact) -> None:
        if not artifact.path.startswith(f"{project.project_id}/"):
            raise StageValidationError("artifact does not belong to this project")
        self.artifact_store.get_bytes(artifact)

    def _validate_literature_artifact(self, artifact: Artifact) -> None:
        self._validate_literature_content(self.artifact_store.get_bytes(artifact))

    @staticmethod
    def _validate_literature_content(content: bytes) -> None:
        try:
            graph = load_graph_bytes(content)
        except (ValueError, ValidationError) as error:
            raise StageValidationError(
                "literature artifact is not a valid evidence graph"
            ) from error
        decision = answer_claims(graph, tuple(claim.claim_id for claim in graph.claims))
        if not decision.accepted:
            raise StageValidationError(
                "literature evidence verification failed: " + "; ".join(decision.reasons)
            )
