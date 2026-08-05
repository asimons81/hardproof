"""Unit tests for repository workcell lifecycle error paths (coverage hardening)."""
from __future__ import annotations

from pathlib import Path

import pytest

from hardproof.domain.enums import RunProfile, RunStage
from hardproof.domain.models import Run
from hardproof.services.hermes_children import FakeHermesChildAdapter
from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def _ready_attempt(tmp_path: Path) -> tuple[RunRepository, str, str]:
    """Create a run with one claimed workcell attempt; return (repo, task_id, attempt_id)."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Lifecycle", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=3, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    return repository, task_id, attempt.attempt_id


def test_record_result_received_requires_actor(tmp_path: Path) -> None:
    repository, _, attempt_id = _ready_attempt(tmp_path)
    with pytest.raises(ValueError, match="requires actor"):
        repository.record_workcell_result_received(attempt_id, actor="  ", summary="ok")


def test_record_result_received_missing_attempt(tmp_path: Path) -> None:
    repository, _, _ = _ready_attempt(tmp_path)
    with pytest.raises(LookupError, match="Workcell attempt not found"):
        repository.record_workcell_result_received("no-such-attempt", actor="parent", summary="ok")


def test_record_result_received_rejects_closed_attempt(tmp_path: Path) -> None:
    repository, _, attempt_id = _ready_attempt(tmp_path)
    repository.record_workcell_result_received(attempt_id, actor="parent", summary="ok")
    repository.close_workcell_attempt(attempt_id, outcome="succeeded", actor="parent", reason="ok")
    with pytest.raises(ValueError, match="closed attempt"):
        repository.record_workcell_result_received(attempt_id, actor="parent", summary="again")


def test_mark_attempt_running_missing_attempt(tmp_path: Path) -> None:
    repository, _, _ = _ready_attempt(tmp_path)
    with pytest.raises(LookupError, match="Workcell attempt not found"):
        repository.mark_workcell_attempt_running("no-such-attempt", child_session_id=None, child_handle={})


def test_mark_attempt_running_rejects_non_starting_state(tmp_path: Path) -> None:
    repository, _, attempt_id = _ready_attempt(tmp_path)
    # Attempt is already running from launch_next; marking again must fail.
    with pytest.raises(ValueError, match="not awaiting launch"):
        repository.mark_workcell_attempt_running(
            attempt_id, child_session_id="child-9", child_handle={"id": "child-9"}
        )
