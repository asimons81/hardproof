"""Integration tests proving Workcells transition gates are enforced.

P0-2 regression: required Workcells must block IMPLEMENT -> REVIEW
until all required tasks are resolved.
"""

from __future__ import annotations

import json
from pathlib import Path

from hardproof.domain.enums import RunProfile, RunStage
from hardproof.domain.models import Run
from hardproof.domain.transitions import FORWARD_STAGE
from hardproof.services.hermes_children import FakeHermesChildAdapter
from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
from hardproof.policy.stage_rules import TransitionFacts
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def advance_to(repository: RunRepository, run_id: str, target: RunStage) -> None:
    """Advance a run forward through stages to reach `target`."""
    stage = repository.get_run(run_id).stage
    for _ in range(20):  # safety bound
        if stage is target:
            return
        if stage in FORWARD_STAGE:
            repository.transition_run(run_id, FORWARD_STAGE[stage], reason="test advance")
        stage = repository.get_run(run_id).stage


def test_run_cannot_advance_from_implement_with_unfinished_required_workcells(tmp_path: Path) -> None:
    """P0-2 e2e: a run with incomplete required Workcells must not advance to REVIEW."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "P0-2 Gate e2e", RunProfile.QUICK)
    repository.create_run(run)
    advance_to(repository, run.id, RunStage.IMPLEMENT)

    # Create a Workcell graph with required tasks
    service = WorkcellService(repository, maximum_attempts=3, default_model_tier="standard")
    service.create_graph(run.id, (
        WorkcellTaskSpec("alpha", "Alpha", "First task", ("alpha done",), priority=1),
        WorkcellTaskSpec("beta", "Beta", "Second task", ("beta done",), dependencies=("alpha",)),
    ))

    # Build transition facts (includes workcell_required_unresolved)
    facts = TransitionFacts(
        artifacts=repository.list_artifacts(run.id),
        approvals=repository.list_approvals(run.id),
        tasks=repository.list_tasks(run.id),
        evidence=(),
        recorded_change=True,
        workcell_required_unresolved=repository.count_unresolved_required_workcells(run.id),
    )
    assert facts.workcell_required_unresolved == 2  # both alpha and beta unresolved

    # Attempt transition -- must be blocked
    from hardproof.services.runs import RunService
    runner = RunService(repository)
    result = runner.try_transition(
        run.id, RunStage.REVIEW, facts, reason="try to bypass"
    )
    assert not result.allowed, "transition must be blocked with unresolved Workcells"
    assert any("required Workcells" in b for b in result.blockers), (
        f"expected Workcells gate blocker, got: {result.blockers}"
    )

    # Complete alpha
    adapter = FakeHermesChildAdapter()
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=adapter)
    assert launched is not None
    rows = repository.list_workcell_task_rows(run.id)
    alpha_row = next(r for r in rows if r["task_key"] == "alpha")
    alpha_attempts = repository.list_workcell_attempts(str(alpha_row["id"]))
    attempt = alpha_attempts[0]
    (tmp_path / "alpha.out").write_text("done\n", encoding="utf-8")
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "alpha" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": str(alpha_row["id"]),
        "attempt_id": attempt.attempt_id, "child_session_id": str(attempt.child_session_id),
        "reported_status": "succeeded", "summary": "alpha done",
        "changed_paths": ["alpha.out"], "commands_executed": [],
        "tests_executed": [{"name": "alpha", "outcome": "passed"}],
        "acceptance_completed": ["alpha done"], "artifacts_produced": [],
        "remaining_blockers": [], "policy_blockers": [], "approval_blockers": [],
        "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    service.process_result(attempt.attempt_id, project_root=tmp_path)

    # beta should now be ready (unblocked by alpha)
    service.refresh_readiness(run.id)

    # Still blocked because beta is unresolved
    facts2 = TransitionFacts(
        artifacts=repository.list_artifacts(run.id),
        approvals=repository.list_approvals(run.id),
        tasks=repository.list_tasks(run.id),
        evidence=(),
        recorded_change=True,
        workcell_required_unresolved=repository.count_unresolved_required_workcells(run.id),
    )
    assert facts2.workcell_required_unresolved == 1  # only beta remains

    result2 = runner.try_transition(
        run.id, RunStage.REVIEW, facts2, reason="after alpha done"
    )
    assert not result2.allowed, "transition must still be blocked with beta unresolved"

    # Complete beta
    launched2 = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched2 is not None
    rows = repository.list_workcell_task_rows(run.id)
    beta_row = next(r for r in rows if r["task_key"] == "beta")
    beta_attempts = repository.list_workcell_attempts(str(beta_row["id"]))
    beta_attempt = beta_attempts[0]
    (tmp_path / "beta.out").write_text("done\n", encoding="utf-8")
    beta_result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "beta" / "attempts" / "1" / "result.json"
    beta_result_path.parent.mkdir(parents=True, exist_ok=True)
    beta_result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": str(beta_row["id"]),
        "attempt_id": beta_attempt.attempt_id, "child_session_id": str(beta_attempt.child_session_id),
        "reported_status": "succeeded", "summary": "beta done",
        "changed_paths": ["beta.out"], "commands_executed": [],
        "tests_executed": [{"name": "beta", "outcome": "passed"}],
        "acceptance_completed": ["beta done"], "artifacts_produced": [],
        "remaining_blockers": [], "policy_blockers": [], "approval_blockers": [],
        "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    service.process_result(beta_attempt.attempt_id, project_root=tmp_path)

    # Now all required Workcells are resolved
    facts3 = TransitionFacts(
        artifacts=repository.list_artifacts(run.id),
        approvals=repository.list_approvals(run.id),
        tasks=repository.list_tasks(run.id),
        evidence=(),
        recorded_change=True,
        workcell_required_unresolved=repository.count_unresolved_required_workcells(run.id),
    )
    assert facts3.workcell_required_unresolved == 0

    result3 = runner.try_transition(
        run.id, RunStage.REVIEW, facts3, reason="all workcells done"
    )
    assert result3.allowed, f"transition should be allowed with all Workcells resolved, got: {result3.blockers}"


def test_run_without_workcells_is_not_affected_by_gate(tmp_path: Path) -> None:
    """A run with no Workcell graph should still transition normally."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "No Workcells", RunProfile.QUICK)
    repository.create_run(run)
    advance_to(repository, run.id, RunStage.IMPLEMENT)

    facts = TransitionFacts(
        artifacts=repository.list_artifacts(run.id),
        approvals=repository.list_approvals(run.id),
        tasks=repository.list_tasks(run.id),
        evidence=(),
        recorded_change=True,
    )
    assert facts.workcell_required_unresolved == 0

    from hardproof.services.runs import RunService
    runner = RunService(repository)
    result = runner.try_transition(
        run.id, RunStage.REVIEW, facts, reason="test without workcells"
    )
    assert result.allowed, f"transition should be allowed without Workcells: {result.blockers}"
