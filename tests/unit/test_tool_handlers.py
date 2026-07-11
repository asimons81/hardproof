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
    handlers = create_handlers(dependencies(tmp_path))
    call(handlers["hardproof_run"], {"action": "start", "profile": "quick", "request": "Task test"})
    created = call(handlers["hardproof_task"], {
        "action": "create", "key": "T1", "title": "Implement", "description": "Make change",
        "risk": "low", "acceptance": ["test passes"],
    })
    assert created["task"]["key"] == "T1"
    listed = call(handlers["hardproof_task"], {"action": "list"})
    assert listed["tasks"][0]["key"] == "T1"
    fetched = call(handlers["hardproof_task"], {"action": "get", "key": "T1"})
    assert fetched["task"]["title"] == "Implement"
    updated = call(handlers["hardproof_task"], {
        "action": "update", "key": "T1", "status": "completed",
        "acceptance_notes": "focused test passes",
    })
    assert updated["task"]["status"] == "completed"


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
