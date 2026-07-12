from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from hardproof.domain.enums import (
    ApprovalGate,
    ArtifactKind,
    EvidenceStatus,
    RiskLevel,
    RunProfile,
    RunStage,
    TaskStatus,
)
from hardproof.domain.models import (
    Approval,
    Artifact,
    Decision,
    Evidence,
    Run,
    SessionBinding,
    Task,
    VerificationCheck,
)
from hardproof.domain.workcells import TaskState, WorkcellTask
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def test_create_and_reopen_run_with_windows_project_path(tmp_path: Path) -> None:
    db_path = tmp_path / "hardproof.db"
    repository = repository_at(db_path)
    run = Run.create(r"C:\Users\person\source\project", "Implement feature", RunProfile.STANDARD)
    repository.create_run(run)
    reopened = repository_at(db_path)
    assert reopened.get_run(run.id) == run


def test_append_only_events_are_concurrency_safe(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "hardproof.db")
    run = Run.create(str(tmp_path), "Concurrent ledger", RunProfile.QUICK)
    repository.create_run(run)

    def append(index: int) -> int:
        return repository.append_event(run.id, "worker", {"index": index})

    with ThreadPoolExecutor(max_workers=8) as pool:
        sequences = list(pool.map(append, range(40)))
    assert len(set(sequences)) == 40
    assert [event.sequence for event in repository.list_events(run.id)] == list(range(1, 42))


def test_stage_transition_and_event_are_atomic(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "hardproof.db")
    run = Run.create(str(tmp_path), "Transition", RunProfile.QUICK)
    repository.create_run(run)
    updated = repository.transition_run(run.id, RunStage.DISCOVERY, reason="intake recorded")
    assert updated.stage is RunStage.DISCOVERY
    events = repository.list_events(run.id)
    assert events[-1].event_type == "stage_transitioned"
    assert events[-1].payload["to_stage"] == "DISCOVERY"


def test_typed_ledgers_round_trip(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "hardproof.db")
    run = Run.create(str(tmp_path), "Typed ledgers", RunProfile.STANDARD)
    repository.create_run(run)
    timestamp = run.created_at

    binding = SessionBinding("session-1", run.id, "cli", timestamp)
    repository.save_session_binding(binding)
    assert repository.get_session_binding(binding.session_id) == binding

    artifact = Artifact("artifact-1", run.id, ArtifactKind.DESIGN, "design.md", "a" * 64, timestamp)
    repository.add_artifact(artifact)
    assert repository.list_artifacts(run.id) == (artifact,)

    approval = Approval("approval-1", run.id, ApprovalGate.DESIGN, "person", "slash", None, timestamp)
    repository.add_approval(approval)
    assert repository.list_approvals(run.id) == (approval,)

    decision = Decision(
        "decision-1", run.id, "storage", "Which storage?", "SQLite",
        "Project-local and durable", "accepted", timestamp,
    )
    repository.upsert_decision(decision)
    assert repository.list_decisions(run.id) == (decision,)

    task = Task(
        "task-1", run.id, "T1", "Implement", "Implement behavior",
        TaskStatus.PENDING, RiskLevel.MEDIUM, (), ("tests pass",), ("module.py",),
        timestamp, timestamp,
    )
    repository.add_task(task)
    assert repository.list_tasks(run.id) == (task,)

    check = VerificationCheck("check-1", run.id, "tests", "python -m pytest", True, 60)
    repository.add_verification_check(check)
    assert repository.list_verification_checks(run.id) == (check,)

    evidence = Evidence(
        "evidence-1", run.id, "tests", "python -m pytest", 0, EvidenceStatus.PASSED,
        "a" * 40, "b" * 64, "c" * 64, "evidence/tests.txt", "d" * 64,
        timestamp, timestamp,
    )
    repository.add_evidence(evidence)
    assert repository.list_evidence(run.id) == (evidence,)


def test_workcell_claim_is_transactional_and_has_one_winner(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "hardproof.db")
    run = Run.create(str(tmp_path), "Workcell claim", RunProfile.STANDARD)
    repository.create_run(run)
    revision_id = repository.create_workcell_graph_revision(
        run.id, 1, "a" * 64, actor="human", rationale="approved plan",
    )
    task = WorkcellTask(
        "workcell-task-1", run.id, "implement", "Implement", "implement safely",
        ("tests pass",), True, (), (), ("hardproof/module.py",), 1, 0, TaskState.READY,
    )
    repository.add_workcell_task(task, revision_id, maximum_attempts=2, model_tier="standard")

    def claim(index: int) -> str:
        attempt = repository.claim_workcell_task(
            task.task_id, claimant=f"parent-{index}", model_tier="standard", context_sha256="b" * 64,
            brief_path="runs/run/tasks/implement/brief.md", context_manifest_path="runs/run/tasks/implement/context.json",
            result_path="runs/run/tasks/implement/result.json",
        )
        return attempt.attempt_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(claim, index) for index in range(2)]
    results = [future.result() if future.exception() is None else None for future in futures]
    assert len([result for result in results if result is not None]) == 1
    assert len(repository.list_workcell_attempts(task.task_id)) == 1


def test_workcell_lifecycle_transitions_are_parent_authoritative(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "hardproof.db")
    run = Run.create(str(tmp_path), "Workcell lifecycle", RunProfile.STANDARD)
    repository.create_run(run)
    revision_id = repository.create_workcell_graph_revision(run.id, 1, "a" * 64, actor="human", rationale="approved")
    task = WorkcellTask("workcell-task-2", run.id, "lifecycle", "Lifecycle", "verify lifecycle", ("tests pass",), True, (), (), (), 1, 0, TaskState.READY)
    repository.add_workcell_task(task, revision_id, maximum_attempts=1, model_tier="standard")
    attempt = repository.claim_workcell_task(task.task_id, claimant="parent", model_tier="standard", context_sha256="b" * 64, brief_path="brief.md", context_manifest_path="context.json", result_path="result.json")
    repository.mark_workcell_attempt_running(attempt.attempt_id, child_session_id="child-1", child_handle={"handle": "h-1"})
    completed = repository.close_workcell_attempt(attempt.attempt_id, outcome="succeeded", actor="parent", reason="validated result")
    assert completed.state.value == "succeeded"
    assert repository.list_workcell_attempts(task.task_id) == (completed,)
