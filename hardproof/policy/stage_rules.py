"""Profile-aware transition gates over immutable run facts."""

from __future__ import annotations

from dataclasses import dataclass

from hardproof.domain.enums import ApprovalGate, ArtifactKind, RunProfile, RunStage, TaskStatus
from hardproof.domain.models import Approval, Artifact, Evidence, Run, Task, TransitionResult
from hardproof.domain.transitions import FORWARD_STAGE, TERMINAL_STAGES
from hardproof.policy.verification_rules import verification_blocker
from hardproof.policy.stage_graph import StageGraph


HUMAN_APPROVAL_SOURCES = frozenset({"slash", "cli", "gateway", "desktop", "telegram", "discord", "slack"})
NON_HUMAN_ACTORS = frozenset({"agent", "assistant", "model", "codex", "hermes"})
ORDER = tuple(FORWARD_STAGE) + (RunStage.COMPLETE,)
POSITION = {stage: index for index, stage in enumerate(ORDER)}


@dataclass(frozen=True, slots=True)
class TransitionFacts:
    artifacts: tuple[Artifact, ...] = ()
    approvals: tuple[Approval, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    approved_review: bool = False
    recorded_change: bool = False
    learning_skipped: bool = False
    workcell_required_unresolved: int = 0

    def has_artifact(self, kind: ArtifactKind) -> bool:
        return any(item.kind is kind for item in self.artifacts)

    def has_human_approval(self, gate: ApprovalGate) -> bool:
        return any(
            item.gate is gate
            and item.source.lower() in HUMAN_APPROVAL_SOURCES
            and item.actor.lower() not in NON_HUMAN_ACTORS
            and (gate is not ApprovalGate.WAIVER or bool((item.reason or "").strip()))
            for item in self.approvals
        )


def _gate_for_forward(run: Run, target: RunStage, facts: TransitionFacts) -> list[str]:
    blockers: list[str] = []
    if run.stage is RunStage.DISCOVERY and target is RunStage.DESIGN:
        if run.profile is not RunProfile.QUICK and not facts.has_artifact(ArtifactKind.DISCOVERY):
            blockers.append("discovery artifact missing")
    elif run.stage is RunStage.DESIGN and target is RunStage.PLAN:
        if run.profile is not RunProfile.QUICK:
            if not facts.has_artifact(ArtifactKind.DESIGN):
                blockers.append("design artifact missing")
            if not facts.has_human_approval(ApprovalGate.DESIGN):
                blockers.append("human design approval missing")
    elif run.stage is RunStage.PLAN and target is RunStage.IMPLEMENT:
        if run.profile is not RunProfile.QUICK:
            if not facts.has_artifact(ArtifactKind.PLAN):
                blockers.append("plan artifact missing")
            if not facts.has_human_approval(ApprovalGate.PLAN):
                blockers.append("human plan approval missing")
    elif run.stage is RunStage.IMPLEMENT and target is RunStage.REVIEW:
        if not facts.recorded_change and not any(task.status is TaskStatus.COMPLETED for task in facts.tasks):
            blockers.append("completed task or recorded change missing")
        if facts.workcell_required_unresolved > 0:
            blockers.append(f"required Workcells are unresolved: {facts.workcell_required_unresolved} task(s) not completed")
    elif run.stage is RunStage.REVIEW and target is RunStage.VERIFY:
        if run.profile is not RunProfile.QUICK and not (
            facts.approved_review or facts.has_human_approval(ApprovalGate.WAIVER)
        ):
            blockers.append("approved review or human waiver missing")
    elif run.stage is RunStage.VERIFY and target is RunStage.DELIVER:
        blocker = verification_blocker(run.profile, facts.evidence)
        if blocker:
            blockers.append(blocker)
    elif run.stage is RunStage.DELIVER and target is RunStage.LEARN:
        if not facts.has_artifact(ArtifactKind.COMPLETION):
            blockers.append("completion report draft missing")
    elif run.stage is RunStage.LEARN and target is RunStage.COMPLETE:
        if not facts.has_artifact(ArtifactKind.LEARNING) and not facts.learning_skipped:
            blockers.append("learning artifact or explicit skip reason missing")
        if run.profile is RunProfile.CRITICAL and not facts.has_human_approval(ApprovalGate.COMPLETION):
            blockers.append("human completion approval missing")
    return blockers


def _quick_jump_blockers(run: Run, target: RunStage, facts: TransitionFacts) -> list[str]:
    blockers: list[str] = []
    if POSITION[target] >= POSITION[RunStage.DELIVER]:
        blocker = verification_blocker(run.profile, facts.evidence)
        if blocker:
            blockers.append(blocker)
    if POSITION[target] >= POSITION[RunStage.LEARN] and not facts.has_artifact(ArtifactKind.COMPLETION):
        blockers.append("completion report draft missing")
    return blockers


def evaluate_transition(
    run: Run,
    target: RunStage,
    facts: TransitionFacts,
    *,
    skip_reason: str | None = None,
    stage_graph: StageGraph | None = None,
) -> TransitionResult:
    """Evaluate structural and profile requirements without mutating state."""
    target = RunStage(target)
    if run.stage in TERMINAL_STAGES:
        return TransitionResult.deny(target, f"terminal stage {run.stage.value} is immutable")
    if target is RunStage.ABORTED:
        return TransitionResult.allow(target)
    if target is RunStage.PAUSED and run.stage is not RunStage.PAUSED:
        return TransitionResult.allow(target)
    expected = (
        stage_graph.successors(run.stage)[0]
        if stage_graph is not None and stage_graph.successors(run.stage)
        else FORWARD_STAGE.get(run.stage)
    )
    if target is expected:
        blockers = _gate_for_forward(run, target, facts)
        if run.stage is RunStage.DELIVER and target is RunStage.COMPLETE:
            if not facts.has_artifact(ArtifactKind.COMPLETION):
                blockers.append("completion report draft missing")
            if run.profile is RunProfile.CRITICAL:
                blockers.append("critical profile cannot skip LEARN")
        return TransitionResult.deny(target, *blockers) if blockers else TransitionResult.allow(target)
    is_forward_jump = (
        run.profile is RunProfile.QUICK
        and run.stage in POSITION and target in POSITION
        and POSITION[target] > POSITION[run.stage]
    )
    if is_forward_jump:
        if not (skip_reason or "").strip():
            return TransitionResult.deny(target, "quick stage skip requires a recorded reason")
        blockers = _quick_jump_blockers(run, target, facts)
        return TransitionResult.deny(target, *blockers) if blockers else TransitionResult.allow(target)
    return TransitionResult.deny(target, f"transition {run.stage.value} -> {target.value} is not allowed")
