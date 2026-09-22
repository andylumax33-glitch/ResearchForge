from __future__ import annotations

import pytest
from pydantic import ValidationError

from researchforge.models import ApprovalDecision, ApprovalStatus, Artifact, Budget, ResearchProject


def test_domain_models_are_immutable() -> None:
    project = ResearchProject(name="rail-study", goal="Reproduce a baseline")
    field_name = "name"

    with pytest.raises((ValidationError, TypeError)):
        setattr(project, field_name, "changed")


def test_budget_rejects_negative_limits_and_usage() -> None:
    with pytest.raises(ValidationError):
        Budget(token_limit=-1)
    with pytest.raises(ValidationError):
        Budget(cost_used_usd=-0.01)


def test_budget_rejects_usage_above_any_nonzero_limit() -> None:
    with pytest.raises(ValidationError, match="exceeds"):
        Budget(token_limit=10, tokens_used=11)
    with pytest.raises(ValidationError, match="exceeds"):
        Budget(cost_limit_usd=1, cost_used_usd=1.01)
    with pytest.raises(ValidationError, match="exceeds"):
        Budget(compute_seconds_limit=60, compute_seconds_used=61)


def test_artifact_requires_checksum_and_safe_relative_path() -> None:
    with pytest.raises(ValidationError):
        Artifact(kind="report", path="report.json", checksum="")
    with pytest.raises(ValidationError):
        Artifact(kind="report", path="../secret", checksum="a" * 64)
    with pytest.raises(ValidationError):
        Artifact(kind="report", path="/tmp/secret", checksum="a" * 64)


def test_approval_requires_actor_and_reason() -> None:
    with pytest.raises(ValidationError):
        ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            actor="",
            reason="",
        )
