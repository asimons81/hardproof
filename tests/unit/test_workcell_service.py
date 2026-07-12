from __future__ import annotations

from pathlib import Path
import json

import pytest

from hardproof.domain.enums import ApprovalGate, ArtifactKind, RunProfile, RunStage
from hardproof.domain.models import Approval, Artifact, Run
from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
from hardproof.services.hermes_children import FakeHermesChildAdapter
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def test_standard_workcell_graph_requires_plan_approval_and_persists_waves(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Workcells", RunProfile.STANDARD)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    repository.add_artifact(Artifact("plan-1", run.id, ArtifactKind.PLAN, "plan.md", "a" * 64, run.created_at))
    service = WorkcellService(repository, maximum_attempts=3, default_model_tier="standard")
    with pytest.raises(PermissionError, match="plan approval"):
        service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests pass",)),))
    repository.add_approval(Approval("approval-1", run.id, ApprovalGate.PLAN, "human", "cli", "approved", run.created_at))
    result = service.create_graph(
        run.id,
        (
            WorkcellTaskSpec("build", "Build", "Build", ("tests pass",), priority=2),
            WorkcellTaskSpec("lint", "Lint", "Lint", ("lint passes",), priority=1),
            WorkcellTaskSpec("verify", "Verify", "Verify", ("all pass",), dependencies=("build", "lint")),
        ),
    )
    assert result.waves == (("lint", "build"), ("verify",))
    rows = repository.list_workcell_task_rows(run.id)
    assert [(item["task_key"], item["wave_number"]) for item in rows] == [("lint", 1), ("build", 1), ("verify", 2)]


def test_readiness_promotes_only_satisfied_dependencies(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Readiness", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(
        run.id,
        (
            WorkcellTaskSpec("build", "Build", "Build", ("tests",)),
            WorkcellTaskSpec("verify", "Verify", "Verify", ("tests",), dependencies=("build",)),
        ),
    )
    assert service.refresh_readiness(run.id) == ("build",)
    build_id = next(item["id"] for item in repository.list_workcell_task_rows(run.id) if item["task_key"] == "build")
    attempt = repository.claim_workcell_task(str(build_id), claimant="parent", model_tier="standard", context_sha256="b" * 64, brief_path="brief.md", context_manifest_path="context.json", result_path="result.json")
    repository.close_workcell_attempt(attempt.attempt_id, outcome="succeeded", actor="parent", reason="validated")
    assert service.refresh_readiness(run.id) == ("verify",)


def test_launch_next_writes_bounded_handoff_and_records_fresh_child(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Launch", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    adapter = FakeHermesChildAdapter()
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build safely", ("tests",), write_scope=("src/**",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=adapter)
    assert launched is not None and launched.child_session_id == "fake-child-1"
    assert adapter.launches[0][0].startswith("# Workcell task: build")
    assert (tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "brief.md").exists()
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    assert repository.list_workcell_attempts(task_id)[0].state.value == "running"


def test_parent_validates_child_result_before_authoritative_success(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Result", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    changed = tmp_path / "changed.py"
    changed.write_text("pass\n", encoding="utf-8")
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "result.json"
    result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": task_id, "attempt_id": attempt.attempt_id,
        "child_session_id": "fake-child-1", "reported_status": "succeeded", "summary": "completed",
        "changed_paths": ["changed.py"], "commands_executed": ["python -m pytest"],
        "tests_executed": [{"name": "tests", "outcome": "passed"}], "acceptance_completed": ["tests"],
        "artifacts_produced": [], "remaining_blockers": [], "policy_blockers": [], "approval_blockers": [],
        "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    assert service.process_result(attempt.attempt_id, project_root=tmp_path) == "succeeded"
    assert repository.list_workcell_attempts(task_id)[0].state.value == "succeeded"
