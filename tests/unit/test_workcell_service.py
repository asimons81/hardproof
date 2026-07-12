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


def test_create_graph_rejects_wrong_stage(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "WrongStage", RunProfile.QUICK)
    repository.create_run(run)
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    with pytest.raises(PermissionError, match="IMPLEMENT"):
        service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))


def test_create_graph_rejects_no_specs(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "NoSpecs", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    with pytest.raises(ValueError, match="at least one task"):
        service.create_graph(run.id, ())


def test_launch_next_returns_none_when_no_ready_tasks(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "NoReady", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    assert service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter()) is None


def test_launch_next_raises_when_brief_exceeds_limit(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "BriefLimit", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard", brief_size_limit=1)
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    with pytest.raises(ValueError, match="exceeds configured size limit"):
        service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())


def test_process_result_rejects_missing_child_session(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "NoChild", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    # Simulate a missing result file after launch completed
    with pytest.raises(ValueError, match="missing or unsafe"):
        service.process_result(attempt.attempt_id, project_root=tmp_path)


def test_create_graph_rejects_no_plan_artifact_for_standard_profile(tmp_path: Path) -> None:
    """Standard profile requires plan artifact even when plan approval exists."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "NoPlanArtifact", RunProfile.STANDARD)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    repository.add_approval(Approval("approval-1", run.id, ApprovalGate.PLAN, "human", "cli", "approved", run.created_at))
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    with pytest.raises(ValueError, match="plan artifact"):
        service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))


def test_launch_next_rejects_oversized_context_manifest(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "ContextLimit", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard", context_manifest_size_limit=1)
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    with pytest.raises(ValueError, match="context manifest exceeds configured size limit"):
        service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())


def test_process_result_rejects_invalid_json_result(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "BadJSON", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_bytes(b"not valid json {")
    with pytest.raises(ValueError, match="not valid UTF-8 JSON"):
        service.process_result(attempt.attempt_id, project_root=tmp_path)


def test_process_result_rejects_oversized_result(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Oversized", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard", result_size_limit=1)
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_bytes(b"x" * 100)
    with pytest.raises(ValueError, match="exceeds configured size limit"):
        service.process_result(attempt.attempt_id, project_root=tmp_path)


def test_process_result_rejects_missing_changed_path(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "MissingPath", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": task_id, "attempt_id": attempt.attempt_id,
        "child_session_id": "fake-child-1", "reported_status": "succeeded", "summary": "completed",
        "changed_paths": ["nonexistent-file.py"], "commands_executed": [],
        "tests_executed": [], "acceptance_completed": ["tests"],
        "artifacts_produced": [], "remaining_blockers": [], "policy_blockers": [],
        "approval_blockers": [], "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="missing path"):
        service.process_result(attempt.attempt_id, project_root=tmp_path)


def test_process_result_rejects_unmet_acceptance(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "UnmetAccept", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests pass",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    changed = tmp_path / "built.py"
    changed.write_text("ok\n", encoding="utf-8")
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": task_id, "attempt_id": attempt.attempt_id,
        "child_session_id": "fake-child-1", "reported_status": "succeeded", "summary": "completed",
        "changed_paths": ["built.py"], "commands_executed": [],
        "tests_executed": [], "acceptance_completed": [],
        "artifacts_produced": [], "remaining_blockers": [], "policy_blockers": [],
        "approval_blockers": [], "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="acceptance criteria"):
        service.process_result(attempt.attempt_id, project_root=tmp_path)


def test_child_can_write_result_from_received_context_only(tmp_path: Path) -> None:
    """Regression test for P0-1: the child must receive every identity it needs.

    The child receives brief + context JSON. The context includes attempt_id,
    task_id, run_id, and child_session_id (from the adapter). Using ONLY that
    information the child must be able to write a result.json that the parent
    accepts. No post-launch repository introspection is permitted.
    """
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "P0-1-Contract", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    adapter = FakeHermesChildAdapter()
    service = WorkcellService(repository, maximum_attempts=3, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build the thing", ("tests pass",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=adapter)
    assert launched is not None

    # The child receives brief + context JSON -- extract the context
    _, context_json, _ = adapter.launches[0]
    child_ctx = json.loads(context_json)

    # Validate the context contains everything needed for the result contract
    for key in ("run_id", "task_id", "attempt_id", "attempt_number", "model_tier", "result_path"):
        assert key in child_ctx, f"context missing {key}"

    # The child uses ONLY the context to write result.json
    # It knows attempt_id, task_id, and run_id from the context
    result_path = tmp_path / ".hardproof" / "runs" / child_ctx["run_id"] / "tasks" / child_ctx["task_key"] / "attempts" / str(child_ctx["attempt_number"]) / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "built.py").write_text("ok\n", encoding="utf-8")

    # The child cannot use repository introspection -- it only knows what
    # was in the context. child_session_id is from the adapter return.
    result_data = {
        "contract_version": 1,
        "run_id": child_ctx["run_id"],
        "task_id": child_ctx["task_id"],
        "attempt_id": child_ctx["attempt_id"],
        "child_session_id": launched.child_session_id,
        "reported_status": "succeeded",
        "summary": "child completed task using contract from context",
        "changed_paths": ["built.py"],
        "commands_executed": ["python -m pytest"],
        "tests_executed": [{"name": "unit", "outcome": "passed"}],
        "acceptance_completed": ["tests pass"],
        "artifacts_produced": [],
        "remaining_blockers": [],
        "policy_blockers": [],
        "approval_blockers": [],
        "evidence_references": [],
        "recommended_next_action": "review",
    }
    result_path.write_text(json.dumps(result_data), encoding="utf-8")

    # Parent validates the result -- must succeed without repository introspection
    outcome = service.process_result(child_ctx["attempt_id"], project_root=tmp_path)
    assert outcome == "succeeded"
    # Verify the attempt is now terminal
    task_rows = repository.list_workcell_task_rows(run.id)
    succeeded_tasks = [r for r in task_rows if r["status"] == "succeeded"]
    assert len(succeeded_tasks) == 1


def test_workcell_lifecycle_launch_and_result(tmp_path: Path) -> None:
    """Two-task lifecycle verifying readiness, launch, result, and dependency gating."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Life", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=3, default_model_tier="economy")
    service.create_graph(run.id, (
        WorkcellTaskSpec("first", "First", "Do first", ("ok",), priority=1),
        WorkcellTaskSpec("second", "Second", "Do second", ("ok",), dependencies=("first",)),
    ))
    ready = service.refresh_readiness(run.id)
    assert "first" in ready
    assert "second" not in ready  # blocked by first
    adapter = FakeHermesChildAdapter()
    launch = service.launch_next(run.id, project_root=tmp_path, adapter=adapter)
    assert launch is not None
    rows = repository.list_workcell_task_rows(run.id)
    first_row = next(r for r in rows if r["task_key"] == "first")
    attempt = repository.list_workcell_attempts(str(first_row["id"]))[0]
    (tmp_path / "first.out").write_text("done\n", encoding="utf-8")
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "first" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": str(first_row["id"]),
        "attempt_id": attempt.attempt_id, "child_session_id": str(attempt.child_session_id),
        "reported_status": "succeeded", "summary": "first done",
        "changed_paths": ["first.out"], "commands_executed": [],
        "tests_executed": [{"name": "first", "outcome": "passed"}],
        "acceptance_completed": ["ok"], "artifacts_produced": [],
        "remaining_blockers": [], "policy_blockers": [], "approval_blockers": [],
        "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    assert service.process_result(attempt.attempt_id, project_root=tmp_path) == "succeeded"
    ready = service.refresh_readiness(run.id)
    assert "second" in ready  # now unblocked


def test_launch_next_rejects_paused_or_aborted_run(tmp_path: Path) -> None:
    """Coverage for P1-F: launch_next must fail when run is paused or aborted."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Paused", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    # Pause the run
    repository.transition_run(run.id, RunStage.PAUSED, reason="test pause")
    with pytest.raises(PermissionError, match="active IMPLEMENT stage"):
        service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())


def test_launch_next_respects_concurrency_limit(tmp_path: Path) -> None:
    """Coverage for P1-B: maximum_active_children must be enforced."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Concurrency", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(
        repository, maximum_attempts=2, default_model_tier="standard",
        maximum_active_children=1,
    )
    service.create_graph(run.id, (
        WorkcellTaskSpec("first", "First", "Do first", ("ok",), priority=1),
        WorkcellTaskSpec("second", "Second", "Do second", ("ok",), priority=2),
    ))
    # Launch one child
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    # Second launch should be blocked by concurrency limit
    blocked = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert blocked is None


def test_process_result_rejects_wrong_stage(tmp_path: Path) -> None:
    """Coverage for P1-F: process_result must fail if run is not in IMPLEMENT."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "WrongStageProcess", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests",)),))
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    # Advance past IMPLEMENT
    repository.transition_run(run.id, RunStage.REVIEW, reason="advance past")
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    changed = tmp_path / "file.py"
    changed.write_text("ok\n", encoding="utf-8")
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": task_id,
        "attempt_id": attempt.attempt_id, "child_session_id": "fake-child-1",
        "reported_status": "succeeded", "summary": "done",
        "changed_paths": ["file.py"], "commands_executed": [],
        "tests_executed": [], "acceptance_completed": ["tests"],
        "artifacts_produced": [], "remaining_blockers": [],
        "policy_blockers": [], "approval_blockers": [],
        "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    with pytest.raises(PermissionError, match="IMPLEMENT stage"):
        service.process_result(attempt.attempt_id, project_root=tmp_path)


def test_process_result_enforces_write_scope(tmp_path: Path) -> None:
    """Coverage for P1-C: write scope must reject out-of-scope paths."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "WriteScope", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(
        run.id,
        (WorkcellTaskSpec("build", "Build", "Build", ("tests",), write_scope=("src/**",)),),
    )
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(next(item["id"] for item in repository.list_workcell_task_rows(run.id)))
    attempt = repository.list_workcell_attempts(task_id)[0]
    # Create a file in the allowed scope
    src_file = tmp_path / "src" / "built.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text("ok\n", encoding="utf-8")
    result_path = tmp_path / ".hardproof" / "runs" / run.id / "tasks" / "build" / "attempts" / "1" / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps({
        "contract_version": 1, "run_id": run.id, "task_id": task_id,
        "attempt_id": attempt.attempt_id, "child_session_id": "fake-child-1",
        "reported_status": "succeeded", "summary": "done",
        "changed_paths": ["src/built.py"], "commands_executed": [],
        "tests_executed": [], "acceptance_completed": ["tests"],
        "artifacts_produced": [], "remaining_blockers": [],
        "policy_blockers": [], "approval_blockers": [],
        "evidence_references": [], "recommended_next_action": "review",
    }), encoding="utf-8")
    # This should succeed because src/built.py matches src/**
    outcome = service.process_result(attempt.attempt_id, project_root=tmp_path)
    assert outcome == "succeeded"
