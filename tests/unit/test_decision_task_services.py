from pathlib import Path

import pytest

from hardproof.domain.enums import RiskLevel, RunProfile, TaskStatus
from hardproof.domain.models import Run
from hardproof.services.decisions import DecisionService
from hardproof.services.tasks import TaskService
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def setup(tmp_path: Path) -> tuple[RunRepository, Run]:
    database = Database(tmp_path / "hardproof.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "ledgers", RunProfile.STANDARD)
    repository.create_run(run)
    return repository, run


def test_decision_update_records_superseding_event(tmp_path: Path) -> None:
    repository, run = setup(tmp_path)
    service = DecisionService(repository)
    original = service.record(run.id, "storage", "Which?", "SQLite", "local", "accepted")
    replacement = service.record(run.id, "storage", "Which?", "SQLite WAL", "concurrency", "accepted")
    assert replacement.id != original.id
    assert repository.list_decisions(run.id) == (replacement,)
    superseded = [event for event in repository.list_events(run.id) if event.event_type == "decision_superseded"]
    assert superseded[-1].payload["previous_id"] == original.id


def test_task_dependencies_must_exist_and_remain_acyclic(tmp_path: Path) -> None:
    repository, run = setup(tmp_path)
    service = TaskService(repository)
    service.create(run.id, "A", "A", "first", RiskLevel.LOW)
    with pytest.raises(ValueError, match="missing task dependencies"):
        service.create(run.id, "B", "B", "second", RiskLevel.LOW, dependencies=("missing",))
    service.create(run.id, "B", "B", "second", RiskLevel.MEDIUM, dependencies=("A",))
    with pytest.raises(ValueError, match="cycle"):
        service.update(run.id, "A", dependencies=("B",))


def test_task_completion_requires_acceptance_notes(tmp_path: Path) -> None:
    repository, run = setup(tmp_path)
    service = TaskService(repository)
    service.create(
        run.id, "A", "A", "first", RiskLevel.LOW,
        acceptance=("observable behavior passes",),
    )
    with pytest.raises(ValueError, match="acceptance notes"):
        service.update(run.id, "A", status=TaskStatus.COMPLETED)
    completed = service.update(
        run.id, "A", status=TaskStatus.COMPLETED, acceptance_notes="Focused test passes"
    )
    assert completed.status is TaskStatus.COMPLETED
    assert repository.list_tasks(run.id) == (completed,)
