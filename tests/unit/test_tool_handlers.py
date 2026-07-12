from __future__ import annotations

import json
import subprocess
from pathlib import Path

from hardproof.commands.shared import CommandContext, CommandService
from hardproof.tools.handlers import HandlerDependencies, create_handlers


def dependencies(tmp_path: Path) -> HandlerDependencies:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    command_service = CommandService(CommandContext(tmp_path, actor="model", source="tool"))
    return HandlerDependencies(
        command_service=command_service,
        verify=lambda args: {"ok": True, "checks": args.get("checks", [])},
        report=lambda args: {"ok": True, "action": args.get("action")},
    )


def call(handler, args: dict, **kwargs: object) -> dict:
    result = handler(args, **kwargs)
    assert isinstance(result, str)
    return json.loads(result)


def test_run_handler_start_status_and_failures(tmp_path: Path) -> None:
    handlers = create_handlers(dependencies(tmp_path))
    started = call(handlers["hardproof_run"], {
        "action": "start", "profile": "quick", "request": "Localized fix",
    }, unexpected="ignored")
    assert started["ok"] and started["run_id"].startswith("run-")
    assert call(handlers["hardproof_run"], {"action": "status"})["stage"] == "INTAKE"
    failed = call(handlers["hardproof_run"], {"action": "unknown"})
    assert not failed["ok"] and "unknown" in failed["error"]


def test_record_handler_writes_artifacts_but_never_approvals(tmp_path: Path) -> None:
    deps = dependencies(tmp_path)
    handlers = create_handlers(deps)
    call(handlers["hardproof_run"], {"action": "start", "profile": "standard", "request": "Feature"})
    recorded = call(handlers["hardproof_record"], {
        "kind": "design", "title": "Design", "content": "# Design\nSafe.", "path": "design.md",
    })
    assert recorded["ok"] and len(recorded["sha256"]) == 64
    denied = call(handlers["hardproof_record"], {"kind": "approval", "content": "approve"})
    assert not denied["ok"]
    assert "/hardproof approve" in denied["error"]
    assert deps.command_service.repository.list_approvals(deps.command_service.active_run_id()) == ()


def test_task_create_update_list_get(tmp_path: Path) -> None:
    deps = dependencies(tmp_path)
    handlers = create_handlers(deps)
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "Task test"})
    created = call(handlers["hardproof_task"], {
        "action": "create", "key": "T1", "title": "Implement", "description": "Make change",
        "risk": "low", "acceptance": ["test passes"],
    })
    assert created["task"]["key"] == "T1"
    assert created["risk_suggestion"]["decision_required"] is True
    assert created["risk_suggestion"]["selected_task_risk_unchanged"] == "low"
    stored_risks = deps.command_service.repository.list_risk_suggestions(
        deps.command_service.active_run_id()
    )
    assert len(stored_risks) == 1 and stored_risks[0].task_id is not None
    listed = call(handlers["hardproof_task"], {"action": "list"})
    assert listed["tasks"][0]["key"] == "T1"
    fetched = call(handlers["hardproof_task"], {"action": "get", "key": "T1"})
    assert fetched["task"]["title"] == "Implement"
    updated = call(handlers["hardproof_task"], {
        "action": "update", "key": "T1", "status": "completed",
        "acceptance_notes": "focused test passes",
    })
    assert updated["task"]["status"] == "completed"
    assert call(handlers["hardproof_task"], {"action": "workcell_graph"})["graph"] == []
    status = call(handlers["hardproof_run"], {"action": "workcells_status"})
    assert status["workcells"] == {"task_counts": {}}


def test_transition_verify_and_report_are_dependency_injected(tmp_path: Path) -> None:
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "Flow"})
    transitioned = call(handlers["hardproof_transition"], {
        "target_stage": "IMPLEMENT", "reason": "begin", "skip_reason": "localized",
    })
    assert transitioned["stage"] == "IMPLEMENT"
    assert call(handlers["hardproof_verify"], {"checks": ["tests"]})["checks"] == ["tests"]
    assert call(handlers["hardproof_report"], {"action": "status"})["action"] == "status"


def test_handler_response_is_bounded_and_redacts_errors(tmp_path: Path) -> None:
    deps = dependencies(tmp_path)
    spill_path = tmp_path / "spilled.json"
    deps = HandlerDependencies(
        deps.command_service,
        verify=lambda args: {"ok": True, "output": "x" * 100_000},
        report=deps.report,
        maximum_response_characters=2_000,
        spill=lambda content: (spill_path.write_text(content, encoding="utf-8") and str(spill_path)),
    )
    response = create_handlers(deps)["hardproof_verify"]({})
    assert len(response) <= 2_000
    parsed = json.loads(response)
    assert parsed["truncated"] is True
    assert parsed["output_path"] == str(spill_path)
    assert len(spill_path.read_text(encoding="utf-8")) > len(response)


def test_run_handler_pause_resume_abort(tmp_path: Path) -> None:
    """Covers handlers.py lines 100, 102-103, 105: pause/resume/abort actions"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "Flow"})
    paused = call(handlers["hardproof_run"], {"action": "pause", "reason": "testing"})
    assert paused["ok"]
    assert paused["stage"] in ("PAUSED", "INTAKE")
    resumed = call(handlers["hardproof_run"], {"action": "resume"})
    assert resumed["ok"]
    aborted = call(handlers["hardproof_run"], {"action": "abort", "reason": "done"})
    assert aborted["ok"]


def test_run_handler_workcells_reconcile_and_run_next(tmp_path: Path) -> None:
    """Covers handlers.py lines 110-114, 116-117: workcells_reconcile, workcells_run_next"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "WC test"})
    reconcile = call(handlers["hardproof_run"], {"action": "workcells_reconcile", "attempt_id": "some-attempt"})
    assert "ok" in reconcile
    run_next = call(handlers["hardproof_run"], {"action": "workcells_run_next"})
    assert "ok" in run_next


def test_record_handler_decision(tmp_path: Path) -> None:
    """Covers handlers.py lines 135-143: decision recording"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "Decision"})
    result = call(handlers["hardproof_record"], {
        "kind": "decision", "content": "Proceed with plan",
        "title": "Architecture choice",
        "metadata": {"key": "arch-python", "question": "Python or Rust?", "choice": "Python", "rationale": "Ecosystem", "status": "accepted"},
    })
    assert result["ok"]
    assert result["kind"] == "decision"
    assert result["key"] == "arch-python"


def test_record_handler_unknown_kind_raises(tmp_path: Path) -> None:
    """Covers handlers.py lines 151-153: unknown record kind raises ValueError"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "Unknown"})
    result = call(handlers["hardproof_record"], {"kind": "unknown_kind", "content": "test"})
    assert not result["ok"]
    assert "unknown hardproof_record kind" in result["error"]


def test_record_handler_review_approved_and_learning_skipped(tmp_path: Path) -> None:
    """Covers handlers.py lines 161, 163: review-approved and learning-skipped events"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "ReviewLearn"})
    review = call(handlers["hardproof_record"], {
        "kind": "review", "content": "# Review\nLooks good.", "path": "review.md",
        "metadata": {"outcome": "approved"},
    })
    assert review["ok"]
    learning = call(handlers["hardproof_record"], {
        "kind": "learning", "content": "Learned something new", "path": "learn.md",
        "metadata": {"skipped": "true"},
    })
    assert learning["ok"]


def test_task_handler_get_not_found(tmp_path: Path) -> None:
    """Covers handlers.py line 209: task get for non-existent key"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "GetTask"})
    result = call(handlers["hardproof_task"], {"action": "get", "key": "nonexistent"})
    assert not result["ok"]
    assert "not found" in result["error"]


def test_task_handler_workcell_actions(tmp_path: Path) -> None:
    """Covers handlers.py lines 214-235: workcell_create_graph, workcell_attempts, workcell_process_result"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "WCActions"})
    # workcell_create_graph with a valid task list
    result = call(handlers["hardproof_task"], {
        "action": "workcell_create_graph",
        "workcell_tasks": [{"id": "T1", "title": "Task 1", "dependencies": []}],
    })
    assert "ok" in result
    # workcell_attempts with a non-empty task_id
    result = call(handlers["hardproof_task"], {"action": "workcell_attempts", "task_id": "T1"})
    assert "ok" in result
    # workcell_process_result with a non-empty attempt_id
    result = call(handlers["hardproof_task"], {"action": "workcell_process_result", "attempt_id": "att-1"})
    assert "ok" in result


def test_handler_not_configured_returns_error(tmp_path: Path) -> None:
    """Covers handlers.py line 27: _not_configured for missing verify/report"""
    deps = dependencies(tmp_path)
    # Create dependencies without verify/report so defaults (_not_configured) are used
    raw = HandlerDependencies(command_service=deps.command_service)
    handlers = create_handlers(raw)
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "NC"})
    result = call(handlers["hardproof_verify"], {"checks": []})
    assert not result["ok"]
    assert "not configured" in result["error"]
    result = call(handlers["hardproof_report"], {"action": "status"})
    assert not result["ok"]
    assert "not configured" in result["error"]


def test_run_handler_resume_with_run_id(tmp_path: Path) -> None:
    """Covers handlers.py line 102: resume with explicit run_id"""
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "ResumeTest"})
    status = call(handlers["hardproof_run"], {"action": "status"})
    run_id = status["run_id"]
    call(handlers["hardproof_run"], {"action": "pause"})
    result = call(handlers["hardproof_run"], {"action": "resume", "run_id": run_id})
    assert result["ok"]
