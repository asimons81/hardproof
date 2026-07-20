from __future__ import annotations

import argparse
import asyncio
import subprocess
import json
import shutil
from pathlib import Path

import pytest

from hardproof.commands.cli import build_parser, run_cli
from hardproof.commands.shared import CommandContext, CommandService
from hardproof.commands.slash import make_slash_handler
from hardproof.domain.enums import ApprovalGate, ArtifactKind, RunStage
from hardproof.domain.models import Approval, Artifact


def context(tmp_path: Path, *, source: str = "cli") -> CommandContext:
    if not (tmp_path / ".git").exists():
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return CommandContext(tmp_path, actor="test-user", source=source, session_id="session-1")


def test_start_status_runs_and_show(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    started = service.execute(["start", "standard", "Build safe feature"])
    assert started.ok and started.run_id
    assert "INTAKE" in service.execute(["status"]).text
    assert started.run_id in service.execute(["runs"]).text
    shown = service.execute(["show", started.run_id])
    assert "Build safe feature" in shown.text
    assert ".hardproof" in str(tmp_path / ".hardproof")


def test_workcell_read_and_recovery_commands_are_available(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    service.execute(["start", "standard", "Workcell command coverage"])
    assert "No Workcell tasks" in service.execute(["tasks"]).text
    assert json.loads(service.execute(["workcells", "status"]).text) == {"task_counts": {}}


def test_workcell_plan_command_requires_existing_human_approval(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    started = service.execute(["start", "standard", "Workcell plan command"])
    assert started.run_id is not None
    run = service.repository.transition_run(started.run_id, RunStage.IMPLEMENT, reason="test")
    service.repository.add_artifact(Artifact("plan-1", run.id, ArtifactKind.PLAN, "plan.md", "a" * 64, run.created_at))
    tasks = json.dumps([{"key": "build", "title": "Build", "objective": "Build safely", "acceptance": ["tests"]}])
    with pytest.raises(PermissionError, match="plan approval"):
        service.execute(["workcells", "plan", "--tasks-json", tasks])
    service.repository.add_approval(Approval("plan-approval", run.id, ApprovalGate.PLAN, "human", "cli", "approved", run.created_at))
    result = service.execute(["workcells", "plan", "--tasks-json", tasks])
    assert json.loads(result.text)["waves"] == [["build"]]


def test_human_approval_and_waiver_sources_are_attributable(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path, source="slash"))
    service.execute(["start", "standard", "Request"])
    assert service.execute(["approve", "design", "reviewed carefully"]).ok
    assert service.execute(["waive", "review", "accepted known limitation"]).ok
    approvals = service.repository.list_approvals(service.active_run_id())
    assert {item.source for item in approvals} == {"slash"}
    assert {item.actor for item in approvals} == {"test-user"}


def test_pause_resume_abort(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    service.execute(["start", "quick", "Request"])
    assert "PAUSED" in service.execute(["pause", "waiting"]).text
    assert "INTAKE" in service.execute(["resume"]).text
    assert "ABORTED" in service.execute(["abort", "cancelled by user"]).text


def test_config_init_validate_db_migrate_and_doctor(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    initialized = service.execute(["config", "init"])
    assert initialized.ok
    assert service.paths.config.exists()
    assert service.execute(["config", "validate"]).ok
    assert service.execute(["db", "migrate"]).ok
    status = json.loads(service.execute(["db", "status"]).text)
    assert status["schema_version"] == 3
    assert status["pending_migrations"] == []
    assert status["mutation_occurred"] is False
    dry_run = json.loads(service.execute(["db", "migrate", "--dry-run"]).text)
    assert dry_run["mutation_occurred"] is False
    explained = json.loads(service.execute(["config", "explain"]).text)
    assert explained["schema_version"] == 3
    assert explained["stage_graph"]["required_stages"] == ["VERIFY", "DELIVER", "COMPLETE"]
    doctor = service.execute(["doctor"])
    assert "Git repository" in doctor.text
    assert "Database" in doctor.text


def test_legacy_state_migration_preserves_database_and_writes_recovery_report(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    old_database = tmp_path / ".crucible" / "state" / "hardproof.db"
    old_database.parent.mkdir(parents=True)
    shutil.copy2(service.paths.database, old_database)
    result = service.execute(["migrate-state"])
    assert result.ok
    assert (tmp_path / ".hardproof.backup" / "state" / "hardproof.db").exists()
    report = json.loads((tmp_path / ".hardproof" / "migration-report.json").read_text())
    assert report["database_integrity"] == "ok"
    assert "Rollback" in result.text


def test_legacy_state_conflict_fails_without_overwriting_active_state(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    old = tmp_path / ".crucible"
    old.mkdir()
    (old / "keep.txt").write_text("old", encoding="utf-8")
    (service.paths.root / "keep.txt").write_text("new", encoding="utf-8")
    result = service.execute(["migrate-state"])
    assert not result.ok
    assert "Resolve manually" in result.text
    assert (service.paths.root / "keep.txt").read_text(encoding="utf-8") == "new"


def test_evidence_and_export_are_deterministic_and_secret_safe(tmp_path: Path) -> None:
    service = CommandService(context(tmp_path))
    started = service.execute(["start", "quick", "Do not include token=secret-value"])
    assert "No verification evidence" in service.execute(["evidence"]).text
    exported = service.execute(["export"])
    assert exported.ok
    export_path = service.paths.run_directory(started.run_id or "") / "completion.json"
    first = export_path.read_bytes()
    assert b"secret-value" not in first
    service.execute(["export"])
    assert export_path.read_bytes() == first


def test_slash_and_cli_use_same_command_service_output(tmp_path: Path) -> None:
    slash = make_slash_handler(lambda: CommandService(context(tmp_path, source="slash")))
    slash_output = asyncio.run(slash('start quick "Parity request"'))
    cli_output = run_cli(
        build_parser().parse_args(["status"]),
        service_factory=lambda: CommandService(context(tmp_path, source="cli")),
    )
    assert "run-" in slash_output
    assert "INTAKE" in cli_output


@pytest.mark.parametrize(
    "argv",
    [
        ["start", "standard", "request"], ["status"], ["approve", "design"],
        ["waive", "gate", "reason"], ["pause"], ["resume"], ["abort", "reason"],
        ["evidence"], ["export"], ["doctor"], ["runs"], ["show", "run-id"],
        ["config", "init"], ["config", "validate"], ["db", "migrate"], ["complete"],
        ["config", "explain"], ["db", "status"], ["db", "migrate", "--dry-run"],
        ["policy", "waivers", "list"],
        ["policy", "explain", "--tool", "terminal", "--args-json", "{}"],
        ["policy", "suggest-risk", "--text", "change"],
        ["tasks"], ["task", "graph"], ["task", "show", "task-id"],
        ["task", "attempts", "task-id"], ["workcells", "status"],
        ["workcells", "reconcile", "attempt-id"],
        ["workcells", "plan", "--tasks-json", "[]"],
        ["workcells", "run-next"],
        ["workcells", "result", "attempt-id"],
    ],
)
def test_cli_parser_accepts_every_documented_subcommand(argv: list[str]) -> None:
    namespace = build_parser().parse_args(argv)
    assert isinstance(namespace, argparse.Namespace)


@pytest.mark.parametrize("raw", ["", "unknown", 'start standard "unterminated'])
def test_malformed_slash_arguments_return_concise_error(tmp_path: Path, raw: str) -> None:
    handler = make_slash_handler(lambda: CommandService(context(tmp_path, source="slash")))
    output = asyncio.run(handler(raw))
    assert output.startswith("Hardproof error:")
    assert len(output) < 500


def test_policy_waiver_commands_are_human_only_and_share_cli_slash_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("hardproof.commands.shared.utc_now", lambda: "2026-07-12T19:00:00Z")
    service = CommandService(context(tmp_path, source="cli"))
    service.execute(["start", "standard", "waiver command"])
    created = service.execute([
        "policy", "waivers", "create", "generated", "stage.before_implement.source_mutation",
        "--expires", "2026-07-12T20:00:00Z", "--reason", "reviewed",
        "--tool", "write_file", "--path", "generated/**", "--stage", "DESIGN",
    ])
    assert created.ok and "generated" in created.text
    assert "generated" in service.execute(["policy", "waivers", "list"]).text
    assert service.execute([
        "policy", "waivers", "revoke", "generated", "--reason", "complete"
    ]).ok

    model = CommandService(CommandContext(tmp_path, actor="model", source="tool"))
    with pytest.raises(PermissionError, match="human"):
        model.execute([
            "policy", "waivers", "create", "forbidden", "project.rule",
            "--expires", "2026-07-12T20:00:00Z", "--reason", "no",
        ])
