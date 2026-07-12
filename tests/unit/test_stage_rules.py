from __future__ import annotations

from itertools import product

import pytest

from hardproof.domain.enums import (
    ApprovalGate,
    ArtifactKind,
    EvidenceStatus,
    RunProfile,
    RunStage,
    RunStatus,
    TaskStatus,
)
from hardproof.domain.models import Approval, Artifact, Evidence, Run, Task
from hardproof.policy.stage_rules import TransitionFacts, evaluate_transition


NOW = "2026-07-11T05:00:00Z"


def run_at(stage: RunStage, profile: RunProfile = RunProfile.STANDARD) -> Run:
    status = RunStatus.PAUSED if stage is RunStage.PAUSED else RunStatus.ACTIVE
    return Run("run-1", ".", "request", profile, stage, status, NOW, NOW)


def artifact(kind: ArtifactKind) -> Artifact:
    return Artifact(f"artifact-{kind.value}", "run-1", kind, f"{kind.value}.md", "a" * 64, NOW)


def approval(
    gate: ApprovalGate,
    *,
    actor: str = "person",
    source: str = "slash",
    reason: str | None = None,
) -> Approval:
    return Approval(f"approval-{gate.value}", "run-1", gate, actor, source, reason, NOW)


def completed_task() -> Task:
    return Task(
        "task-1", "run-1", "T1", "task", "description", TaskStatus.COMPLETED,
        "medium", (), ("done",), (), NOW, NOW, "accepted",
    )


def passed_evidence(name: str = "tests") -> Evidence:
    return Evidence(
        f"evidence-{name}", "run-1", name, "python -m pytest", 0,
        EvidenceStatus.PASSED, "a" * 40, "b" * 64, "c" * 64,
        f"evidence/{name}.txt", "d" * 64, NOW, NOW,
    )


@pytest.mark.parametrize(
    ("stage", "target"),
    [
        (RunStage.INTAKE, RunStage.DISCOVERY),
        (RunStage.DISCOVERY, RunStage.DESIGN),
        (RunStage.DESIGN, RunStage.PLAN),
        (RunStage.PLAN, RunStage.IMPLEMENT),
        (RunStage.IMPLEMENT, RunStage.REVIEW),
        (RunStage.REVIEW, RunStage.VERIFY),
        (RunStage.VERIFY, RunStage.DELIVER),
        (RunStage.DELIVER, RunStage.LEARN),
        (RunStage.LEARN, RunStage.COMPLETE),
    ],
)
def test_forward_transition_matrix_has_a_satisfiable_path(stage: RunStage, target: RunStage) -> None:
    facts = TransitionFacts(
        artifacts=tuple(artifact(kind) for kind in ArtifactKind),
        approvals=(approval(ApprovalGate.DESIGN), approval(ApprovalGate.PLAN)),
        tasks=(completed_task(),), evidence=(passed_evidence(),),
        approved_review=True, learning_skipped=True,
    )
    assert evaluate_transition(run_at(stage), target, facts).allowed


def test_standard_gate_messages_name_exact_missing_records() -> None:
    result = evaluate_transition(run_at(RunStage.DESIGN), RunStage.PLAN, TransitionFacts())
    assert not result.allowed
    assert "design artifact missing" in result.blockers
    assert "human design approval missing" in result.blockers


def test_plan_to_implement_rejects_self_approval() -> None:
    facts = TransitionFacts(
        artifacts=(artifact(ArtifactKind.PLAN),),
        approvals=(approval(ApprovalGate.PLAN, actor="model", source="tool"),),
    )
    result = evaluate_transition(run_at(RunStage.PLAN), RunStage.IMPLEMENT, facts)
    assert result.blockers == ("human plan approval missing",)


def test_implement_requires_completed_task_or_recorded_change() -> None:
    denied = evaluate_transition(run_at(RunStage.IMPLEMENT), RunStage.REVIEW, TransitionFacts())
    assert "completed task or recorded change missing" in denied.blockers
    allowed = evaluate_transition(
        run_at(RunStage.IMPLEMENT), RunStage.REVIEW,
        TransitionFacts(recorded_change=True),
    )
    assert allowed.allowed


def test_review_requires_approved_review_or_human_waiver() -> None:
    denied = evaluate_transition(run_at(RunStage.REVIEW), RunStage.VERIFY, TransitionFacts())
    assert not denied.allowed
    facts = TransitionFacts(approvals=(approval(ApprovalGate.WAIVER, reason="accepted risk"),))
    assert evaluate_transition(run_at(RunStage.REVIEW), RunStage.VERIFY, facts).allowed


def test_waiver_requires_a_human_source_actor_and_reason() -> None:
    for invalid in (
        approval(ApprovalGate.WAIVER, reason=None),
        approval(ApprovalGate.WAIVER, actor="agent", reason="accepted risk"),
        approval(ApprovalGate.WAIVER, source="tool", reason="accepted risk"),
    ):
        result = evaluate_transition(
            run_at(RunStage.REVIEW),
            RunStage.VERIFY,
            TransitionFacts(approvals=(invalid,)),
        )
        assert result.blockers == ("approved review or human waiver missing",)


def test_stale_or_failed_evidence_blocks_delivery() -> None:
    stale = passed_evidence()
    object.__setattr__(stale, "status", EvidenceStatus.STALE)
    result = evaluate_transition(
        run_at(RunStage.VERIFY), RunStage.DELIVER, TransitionFacts(evidence=(stale,))
    )
    assert result.blockers == ("1 fresh passing verification check required; found 0",)


def test_critical_requires_two_checks_and_completion_approval() -> None:
    verify = evaluate_transition(
        run_at(RunStage.VERIFY, RunProfile.CRITICAL), RunStage.DELIVER,
        TransitionFacts(evidence=(passed_evidence(),)),
    )
    assert "2 fresh passing verification checks required; found 1" in verify.blockers
    complete = evaluate_transition(
        run_at(RunStage.LEARN, RunProfile.CRITICAL), RunStage.COMPLETE,
        TransitionFacts(learning_skipped=True),
    )
    assert "human completion approval missing" in complete.blockers


def test_quick_skip_requires_reason_and_is_persistable() -> None:
    run = run_at(RunStage.INTAKE, RunProfile.QUICK)
    denied = evaluate_transition(run, RunStage.IMPLEMENT, TransitionFacts())
    assert denied.blockers == ("quick stage skip requires a recorded reason",)
    assert evaluate_transition(run, RunStage.IMPLEMENT, TransitionFacts(), skip_reason="localized fix").allowed


def test_forward_artifact_and_learning_gates_report_missing_records() -> None:
    discovery = evaluate_transition(
        run_at(RunStage.DISCOVERY), RunStage.DESIGN, TransitionFacts()
    )
    plan = evaluate_transition(run_at(RunStage.PLAN), RunStage.IMPLEMENT, TransitionFacts())
    deliver = evaluate_transition(run_at(RunStage.DELIVER), RunStage.LEARN, TransitionFacts())
    learn = evaluate_transition(run_at(RunStage.LEARN), RunStage.COMPLETE, TransitionFacts())
    assert discovery.blockers == ("discovery artifact missing",)
    assert "plan artifact missing" in plan.blockers
    assert deliver.blockers == ("completion report draft missing",)
    assert learn.blockers == ("learning artifact or explicit skip reason missing",)


def test_quick_jump_to_delivery_still_requires_verification_and_completion() -> None:
    run = run_at(RunStage.INTAKE, RunProfile.QUICK)
    deliver = evaluate_transition(run, RunStage.DELIVER, TransitionFacts(), skip_reason="hotfix")
    learn = evaluate_transition(
        run,
        RunStage.LEARN,
        TransitionFacts(evidence=(passed_evidence(),)),
        skip_reason="hotfix",
    )
    assert deliver.blockers == ("1 fresh passing verification check required; found 0",)
    assert learn.blockers == ("completion report draft missing",)


@pytest.mark.parametrize("terminal", [RunStage.COMPLETE, RunStage.ABORTED])
def test_terminal_runs_are_immutable(terminal: RunStage) -> None:
    status = RunStatus.COMPLETE if terminal is RunStage.COMPLETE else RunStatus.ABORTED
    run = Run("run-1", ".", "request", RunProfile.STANDARD, terminal, status, NOW, NOW)
    for target in RunStage:
        assert not evaluate_transition(run, target, TransitionFacts()).allowed


def test_abort_is_allowed_from_every_nonterminal_stage() -> None:
    for stage in set(RunStage) - {RunStage.COMPLETE, RunStage.ABORTED}:
        assert evaluate_transition(run_at(stage), RunStage.ABORTED, TransitionFacts()).allowed


def test_unlisted_transitions_are_rejected() -> None:
    forward = {
        (RunStage.INTAKE, RunStage.DISCOVERY), (RunStage.DISCOVERY, RunStage.DESIGN),
        (RunStage.DESIGN, RunStage.PLAN), (RunStage.PLAN, RunStage.IMPLEMENT),
        (RunStage.IMPLEMENT, RunStage.REVIEW), (RunStage.REVIEW, RunStage.VERIFY),
        (RunStage.VERIFY, RunStage.DELIVER), (RunStage.DELIVER, RunStage.LEARN),
        (RunStage.LEARN, RunStage.COMPLETE),
    }
    for source, target in product(RunStage, repeat=2):
        if source in {RunStage.COMPLETE, RunStage.ABORTED} or target in {RunStage.ABORTED, RunStage.PAUSED}:
            continue
        if (source, target) not in forward:
            assert not evaluate_transition(run_at(source), target, TransitionFacts()).allowed


def test_required_workcell_blocks_implement_to_review() -> None:
    """P0-2 regression: required Workcells must block IMPLEMENT -> REVIEW until resolved."""
    # Blocked when required Workcells are unresolved
    blocked = evaluate_transition(
        run_at(RunStage.IMPLEMENT), RunStage.REVIEW,
        TransitionFacts(recorded_change=True, workcell_required_unresolved=1),
    )
    assert "required Workcells are unresolved" in blocked.blockers[0]

    # Allowed when all required Workcells are completed
    allowed = evaluate_transition(
        run_at(RunStage.IMPLEMENT), RunStage.REVIEW,
        TransitionFacts(recorded_change=True, workcell_required_unresolved=0),
    )
    assert allowed.allowed

    # Allowed when there are no Workcells (default)
    default = evaluate_transition(
        run_at(RunStage.IMPLEMENT), RunStage.REVIEW,
        TransitionFacts(recorded_change=True),
    )
    assert default.allowed
