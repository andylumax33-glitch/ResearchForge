from __future__ import annotations

from itertools import pairwise

import pytest

from researchforge.models import ResearchState
from researchforge.state_machine import (
    InvalidTransitionError,
    next_state,
    validate_transition,
)

ORDER = [
    ResearchState.INTAKE,
    ResearchState.SCOPING,
    ResearchState.LITERATURE_REVIEW,
    ResearchState.BASELINE_REPRODUCTION,
    ResearchState.HYPOTHESIS_GENERATION,
    ResearchState.EXPERIMENT_DESIGN,
    ResearchState.IMPLEMENTATION,
    ResearchState.EXPERIMENT_EXECUTION,
    ResearchState.ANALYSIS,
    ResearchState.CRITIQUE,
    ResearchState.HUMAN_APPROVAL,
    ResearchState.RELEASE,
]


@pytest.mark.parametrize("current,target", pairwise(ORDER))
def test_each_forward_transition_is_legal(current: ResearchState, target: ResearchState) -> None:
    assert next_state(current) == target
    validate_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [
        (ResearchState.INTAKE, ResearchState.LITERATURE_REVIEW),
        (ResearchState.ANALYSIS, ResearchState.SCOPING),
        (ResearchState.RELEASE, ResearchState.RELEASE),
    ],
)
def test_skip_backward_and_terminal_transitions_are_rejected(
    current: ResearchState, target: ResearchState
) -> None:
    with pytest.raises(InvalidTransitionError):
        validate_transition(current, target)
