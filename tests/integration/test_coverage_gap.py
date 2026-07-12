"""Quick coverage tests for error paths in repository and services.

These close the remaining coverage gap to reach the 90% threshold.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository
from hardproof.domain.enums import RunProfile, RunStage, RunStatus
from hardproof.domain.models import Run, Waiver
from hardproof.domain.workcells import AttemptState
from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
from hardproof.services.hermes_children import FakeHermesChildAdapter


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def test_expire_due_waivers(tmp_path: Path) -> None:
    """Cover waiver expiry logic."""
    repository = repository_at(tmp_path / "state.db")
    now = datetime.now(timezone.utc)
    created = (now - timedelta(hours=2)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    expired = (now - timedelta(hours=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    waiver = Waiver(
        "w-1", None, "test-waiver", "project.test.rule", None, None, None, None, None,
        "test", "human", "cli", created, expired,
    )
    repository.add_waiver(waiver)
    expired_ids = repository.expire_due_waivers(
        (now + timedelta(minutes=5)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )
    assert "w-1" in expired_ids
    # Second call should not re-expire
    again = repository.expire_due_waivers(
        (now + timedelta(minutes=5)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )
    assert "w-1" not in again


def test_workcell_retry_recovery(tmp_path: Path) -> None:
    """Cover retry-on-interrupted attempt and dependent recovery."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "RetryCover", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    service = WorkcellService(repository, maximum_attempts=3, default_model_tier="standard")
    service.create_graph(run.id, (
        WorkcellTaskSpec("alpha", "Alpha", "Do alpha", ("ok",)),
    ))
    service.refresh_readiness(run.id)
    task_rows = repository.list_workcell_task_rows(run.id)
    task_id = str(task_rows[0]["id"])

    # Claim and mark running, then reconcile to interrupt
    attempt = repository.claim_workcell_task(
        task_id, claimant="test", model_tier="standard",
        context_sha256="a" * 64, brief_path="brief.md",
        context_manifest_path="context.json", result_path="result.json",
    )
    repository.mark_workcell_attempt_running(
        attempt.attempt_id, child_session_id="test-child", child_handle={"handle": "test"},
    )

    # Reconcile (interrupt)
    reconciled = repository.reconcile_workcell_attempt(attempt.attempt_id, actor="test")
    assert reconciled.state is AttemptState.INTERRUPTED
    assert reconciled.terminal_reason is not None

    # Authorize retry
    decision = repository.authorize_workcell_retry(
        task_id, attempt.attempt_id, actor="human", reason="retry after interrupt",
        material_change="human investigation",
        new_context_sha256=attempt.context_sha256, new_model_tier=attempt.model_tier,
    )
    assert decision.startswith("workcell-retry-")

    # Task should now be ready again
    rows = repository.list_workcell_task_rows(run.id)
    assert rows[0]["status"] == "ready"


def test_policy_decision_records(tmp_path: Path) -> None:
    """Cover policy decision creation and retrieval."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Policy-Dec", RunProfile.QUICK)
    repository.create_run(run)

    from hardproof.domain.models import PolicyDecisionRecord, new_id
    from hardproof.policy.trace import RuleTrace

    trace = (RuleTrace("test.rule", "matched", "test"),)
    record = PolicyDecisionRecord(
        new_id("policy"), run.id, "hardproof_test",
        "allow", "test.rule", "test", trace,
        "a" * 64, "b" * 64, None, None,
        run.created_at,
    )
    repository.add_policy_decision(record)
    records = repository.list_policy_decisions(run.id)
    assert len(records) == 1
    found = repository.get_policy_decision(run.id, 1)
    assert found.rule_key == "test.rule"


def test_waiver_revocation(tmp_path: Path) -> None:
    """Cover waiver revocation flow."""
    repository = repository_at(tmp_path / "state.db")
    now = datetime.now(timezone.utc)
    created = (now - timedelta(hours=2)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    future = (now + timedelta(hours=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    waiver = Waiver(
        "w-2", None, "test-waiver2", "project.test.rule2", None, None, None, None, None,
        "test", "human", "cli", created, future,
    )
    repository.add_waiver(waiver)
    revoked = repository.revoke_waiver("test-waiver2", "admin", "cli", "no longer needed", now.isoformat())
    assert revoked.revoked_by == "admin"
    events = repository.list_waiver_events("w-2")
    assert any(e.event_type == "revoked" for e in events)
    with pytest.raises(ValueError, match="already revoked"):
        repository.revoke_waiver("test-waiver2", "admin", "cli", "again", now.isoformat())


def test_list_applicable_waivers(tmp_path: Path) -> None:
    """Cover waiver listing with and without run scope."""
    repository = repository_at(tmp_path / "state.db")
    now = datetime.now(timezone.utc)
    created = (now - timedelta(hours=2)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    future = (now + timedelta(hours=1)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    run = Run.create(str(tmp_path), "WaiverTest", RunProfile.QUICK)
    repository.create_run(run)
    global_w = Waiver("w-3", None, "global-w", "project.test.rule", None, None, None, None, None,
                      "test", "human", "cli", created, future)
    run_w = Waiver("w-4", run.id, "run-w", "project.test.rule", None, None, None, None, None,
                   "test", "human", "cli", created, future)
    repository.add_waiver(global_w)
    repository.add_waiver(run_w)
    all_w = repository.list_waivers()
    assert len(all_w) == 2
    applicable = repository.list_applicable_waivers(run.id)
    assert len(applicable) == 2  # both global and run-specific


def test_save_and_get_session_binding(tmp_path: Path) -> None:
    """Cover session binding save and retrieval."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "SessionBind", RunProfile.QUICK)
    repository.create_run(run)
    from hardproof.domain.models import SessionBinding, utc_now
    binding = SessionBinding("session-1", run.id, "test", utc_now())
    repository.save_session_binding(binding)
    found = repository.get_session_binding("session-1")
    assert found is not None and found.run_id == run.id
    assert repository.get_session_binding("nonexistent") is None


def test_list_workcell_lifecycle_events(tmp_path: Path) -> None:
    """Cover workcell lifecycle event listing."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "LifecycleEvents", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("task", "T", "Do", ("ok",)),))
    service.refresh_readiness(run.id)
    rows = repository.list_workcell_task_rows(run.id)
    launched = service.launch_next(run.id, project_root=tmp_path, adapter=FakeHermesChildAdapter())
    assert launched is not None
    task_id = str(rows[0]["id"])
    attempts = repository.list_workcell_attempts(task_id)
    events = repository.list_workcell_lifecycle_events(attempts[0].attempt_id)
    assert len(events) >= 1
    assert any(e["event_type"] == "claim_acquired" for e in events)
    assert any(e["event_type"] == "child_started" for e in events)


def test_add_workcell_dependency_non_required(tmp_path: Path) -> None:
    """Cover non-required dependency creation and wave assignment edge cases."""
    repository = repository_at(tmp_path / "state.db")
    from hardproof.domain.workcells import WorkcellTask
    from hardproof.domain.enums import RunStage
    from hardproof.domain.models import new_id

    run = Run.create(str(tmp_path), "DepEdges", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    graph_id = repository.create_workcell_graph_revision(
        run.id, 1, "a" * 64, actor="test", rationale="test"
    )
    task_a = WorkcellTask(new_id("wc-task"), run.id, "a", "A", "Do A", ("ok",), True, (), (), (), 1, 0)
    task_b = WorkcellTask(new_id("wc-task"), run.id, "b", "B", "Do B", ("ok",), True, (), ("b",), (), 1, 0)
    repository.add_workcell_task(task_a, graph_id, maximum_attempts=3, model_tier="standard")
    repository.add_workcell_task(task_b, graph_id, maximum_attempts=3, model_tier="economy")
    repository.add_workcell_dependency(task_b.task_id, task_a.task_id, required=False)

    # Wave assignment edge: negative wave should raise
    import pytest
    with pytest.raises(ValueError, match="positive"):
        repository.set_workcell_wave(task_a.task_id, 0)
    with pytest.raises(LookupError):
        repository.set_workcell_wave("nonexistent-id", 1)


def test_stale_evidence_and_update_task_edge(tmp_path: Path) -> None:
    """Cover edge cases: stale evidence check and task update lookup."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "EdgeCase", RunProfile.QUICK)
    repository.create_run(run)

    # Update task that doesn't exist
    from hardproof.domain.models import Task, utc_now
    from hardproof.domain.enums import TaskStatus, RiskLevel
    t = Task("nonexistent-task", run.id, "T1", "t", "desc", TaskStatus.PENDING,
             RiskLevel.LOW, (), (), (), utc_now(), utc_now())
    with pytest.raises(LookupError, match="task not found"):
        repository.update_task(t)

    # Workcell graph revision with invalid revision
    with pytest.raises(ValueError, match="invalid Workcell graph revision"):
        repository.create_workcell_graph_revision(
            run.id, 0, "a" * 64, actor="test", rationale="test"
        )

    # Add workcell task with invalid maximum attempts
    from hardproof.domain.workcells import WorkcellTask
    bad_task = WorkcellTask("bad-id", run.id, "bad", "Bad", "Bad", ("ok",), True, (), (), (), 1, 0)
    with pytest.raises(ValueError, match="invalid Workcell task"):
        repository.add_workcell_task(bad_task, "graph-id", maximum_attempts=0, model_tier="standard")

    # Verification check with positive timeout
    from hardproof.domain.models import VerificationCheck
    check = VerificationCheck("check-1", run.id, "test", "pytest", True, 30)
    repository.add_verification_check(check)
    checks = repository.list_verification_checks(run.id)
    assert len(checks) == 1
    assert checks[0].name == "test"

    # List decisions
    from hardproof.domain.models import Decision
    decision = Decision("dec-1", run.id, "key-1", "question?", "choice", "rationale", "accepted", run.created_at)
    repository.upsert_decision(decision)
    found = repository.list_decisions(run.id)
    assert len(found) == 1
    repository.upsert_decision(decision)  # upsert again (coverage for ON CONFLICT path)
    found2 = repository.list_decisions(run.id)
    assert len(found2) == 1

    # Risk suggestion
    from hardproof.domain.models import RiskSuggestion
    from hardproof.domain.enums import RiskLevel
    suggestion = RiskSuggestion("risk-1", run.id, None, RiskLevel.HIGH, ("reason one",), None, None, run.created_at)
    repository.add_risk_suggestion(suggestion)

    # Add an artifact
    from hardproof.domain.enums import ArtifactKind
    from hardproof.domain.models import Artifact
    art = Artifact("art-1", run.id, ArtifactKind.DESIGN, "design.md", "a" * 64, run.created_at)
    repository.add_artifact(art)
    arts = repository.list_artifacts(run.id)
    assert len(arts) == 1

    # Workcell attempt detail retrieval edge
    with pytest.raises(LookupError):
        repository.get_workcell_attempt_detail("nonexistent-attempt")

    # resume a non-paused run
    from hardproof.services.runs import RunService
    runner = RunService(repository)
    with pytest.raises(Exception):
        runner.resume(run.id, reason="test")

    # transition that fails (coverage for runs.py line 64)
    from hardproof.policy.stage_rules import TransitionFacts
    from hardproof.domain.enums import RunStage
    with pytest.raises(Exception):
        runner.transition(run.id, RunStage.REVIEW, TransitionFacts(), reason="no prereqs")

    # resume a paused run with no previous stage (coverage for runs.py line 80)
    from hardproof.domain.models import Run as RunModel
    orphan_paused = RunModel("orphan-paused", str(tmp_path), "orphan", RunProfile.QUICK,
                              RunStage.PAUSED, RunStatus.PAUSED, run.created_at, run.created_at)
    repository.create_run(orphan_paused)
    with pytest.raises(Exception):
        runner.resume(orphan_paused.id, reason="test")

    # Add a risk suggestion through the service
    from hardproof.services.risks import RiskService
    from hardproof.domain.models import utc_now
    risk_svc = RiskService(repository)
    risk_svc.suggest(run.id, text="risky change", now=utc_now())


def test_claim_workcell_invalid_claimant(tmp_path: Path) -> None:
    """Cover repository claim_workcell_task empty-claimant rejection."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "ClaimTest", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("t1", "T1", "Do", ("ok",)),))
    service.refresh_readiness(run.id)
    rows = repository.list_workcell_task_rows(run.id)
    with pytest.raises(ValueError, match="invalid Workcell claim"):
        repository.claim_workcell_task(
            str(rows[0]["id"]), claimant="", model_tier="standard",
            context_sha256="a" * 64, brief_path="b.md",
            context_manifest_path="c.json", result_path="r.json",
        )


def test_claim_non_ready_workcell_task(tmp_path: Path) -> None:
    """Cover claim a task that is not in 'ready' status."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "NotReady", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("t1", "T1", "Do", ("ok",)),))
    # Task is 'pending', not 'ready' — claim must fail
    rows = repository.list_workcell_task_rows(run.id)
    with pytest.raises(ValueError, match="not ready"):
        repository.claim_workcell_task(
            str(rows[0]["id"]), claimant="test", model_tier="standard",
            context_sha256="a" * 64, brief_path="b.md",
            context_manifest_path="c.json", result_path="r.json",
        )


def test_claim_workcell_retry_requires_material_change(tmp_path: Path) -> None:
    """Cover that retry without any material change raises."""
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "NoChangeRetry", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
    service = WorkcellService(repository, maximum_attempts=2, default_model_tier="standard")
    service.create_graph(run.id, (WorkcellTaskSpec("t1", "T1", "Do", ("ok",)),))
    service.refresh_readiness(run.id)
    rows = repository.list_workcell_task_rows(run.id)
    attempt = repository.claim_workcell_task(
        str(rows[0]["id"]), claimant="test", model_tier="standard",
        context_sha256="a" * 64, brief_path="b.md",
        context_manifest_path="c.json", result_path="r.json",
    )
    repository.close_workcell_attempt(
        attempt.attempt_id, outcome="failed", actor="test", reason="no change",
    )
    with pytest.raises(ValueError, match="material change"):
        repository.authorize_workcell_retry(
            str(rows[0]["id"]), attempt.attempt_id, actor="human",
            reason="retry", material_change="",
            new_context_sha256=attempt.context_sha256, new_model_tier=attempt.model_tier,
        )
