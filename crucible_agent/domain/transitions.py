"""Structural stage graph; profile gates are added by Task 6."""

from __future__ import annotations

from crucible_agent.domain.enums import RunStage


FORWARD_STAGE: dict[RunStage, RunStage] = {
    RunStage.INTAKE: RunStage.DISCOVERY,
    RunStage.DISCOVERY: RunStage.DESIGN,
    RunStage.DESIGN: RunStage.PLAN,
    RunStage.PLAN: RunStage.IMPLEMENT,
    RunStage.IMPLEMENT: RunStage.REVIEW,
    RunStage.REVIEW: RunStage.VERIFY,
    RunStage.VERIFY: RunStage.DELIVER,
    RunStage.DELIVER: RunStage.LEARN,
    RunStage.LEARN: RunStage.COMPLETE,
}

TERMINAL_STAGES = frozenset({RunStage.ABORTED, RunStage.COMPLETE})


def possible_targets(stage: RunStage) -> frozenset[RunStage]:
    """Return structurally reachable stages before profile-specific gates."""
    if stage in TERMINAL_STAGES:
        return frozenset()
    targets = {RunStage.ABORTED, RunStage.PAUSED}
    if stage is RunStage.PAUSED:
        targets.update(FORWARD_STAGE)
    elif stage in FORWARD_STAGE:
        targets.add(FORWARD_STAGE[stage])
    return frozenset(targets)
