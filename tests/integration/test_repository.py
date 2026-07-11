from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from crucible_agent.domain.enums import (
    ApprovalGate,
    ArtifactKind,
    EvidenceStatus,
    RiskLevel,
    RunProfile,
    RunStage,
    TaskStatus,
)
from crucible_agent.domain.models import (
    Approval,
    Artifact,
    Decision,
    Evidence,
    Run,
    SessionBinding,
    Task,
    VerificationCheck,
)
from crucible_agent.storage.database import Database
from crucible_agent.storage.migrations import migrate
from crucible_agent.storage.repository import RunRepository


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def test_create_and_reopen_run_with_windows_project_path(tmp_path: Path) -> None:
    db_path = tmp_path / "crucible.db"
    repository = repository_at(db_path)
    run = Run.create(r"C:\Users\person\source\project", "Implement feature", RunProfile.STANDARD)
    repository.create_run(run)
    reopened = repository_at(db_path)
    assert reopened.get_run(run.id) == run


def test_append_only_events_are_concurrency_safe(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "crucible.db")
    run = Run.create(str(tmp_path), "Concurrent ledger", RunProfile.QUICK)
    repository.create_run(run)

    def append(index: int) -> int:
        return repository.append_event(run.id, "worker", {"index": index})

    with ThreadPoolExecutor(max_workers=8) as pool:
        sequences = list(pool.map(append, range(40)))
    assert len(set(sequences)) == 40
    assert [event.sequence for event in repository.list_events(run.id)] == list(range(1, 42))


def test_stage_transition_and_event_are_atomic(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "crucible.db")
    run = Run.create(str(tmp_path), "Transition", RunProfile.QUICK)
    repository.create_run(run)
    updated = repository.transition_run(run.id, RunStage.DISCOVERY, reason="intake recorded")
    assert updated.stage is RunStage.DISCOVERY
    events = repository.list_events(run.id)
    assert events[-1].event_type == "stage_transitioned"
    assert events[-1].payload["to_stage"] == "DISCOVERY"


def test_typed_ledgers_round_trip(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "crucible.db")
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
