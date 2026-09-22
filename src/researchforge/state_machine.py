"""Deterministic research workflow state machine."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import pairwise

from researchforge.models import ResearchState, StageDefinition


class InvalidTransitionError(ValueError):
    """Raised when a requested state transition is not allowed."""


ORDERED_STATES = tuple(ResearchState)
NEXT_STATE: Mapping[ResearchState, ResearchState] = {
    current: following for current, following in pairwise(ORDERED_STATES)
}

DEFAULT_STAGES: Mapping[ResearchState, StageDefinition] = {
    state: StageDefinition(
        state=state,
        required_artifact_kinds=frozenset({f"{state.value}_result"})
        if state not in {ResearchState.INTAKE, ResearchState.HUMAN_APPROVAL, ResearchState.RELEASE}
        else frozenset(),
        requires_approval=state is ResearchState.HUMAN_APPROVAL,
    )
    for state in ResearchState
}


def next_state(current: ResearchState) -> ResearchState:
    try:
        return NEXT_STATE[current]
    except KeyError as error:
        raise InvalidTransitionError(f"{current.value} is a terminal state") from error


def validate_transition(current: ResearchState, target: ResearchState) -> None:
    expected = next_state(current)
    if target is not expected:
        raise InvalidTransitionError(
            f"invalid transition from {current.value} to {target.value}; expected {expected.value}"
        )
