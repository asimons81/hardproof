from __future__ import annotations

import argparse
import asyncio
import subprocess
from pathlib import Path

import pytest

from hardproof.commands.cli import build_parser, run_cli
from hardproof.commands.shared import CommandContext, CommandService
from hardproof.commands.slash import make_slash_handler


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
    doctor = service.execute(["doctor"])
    assert "Git repository" in doctor.text
    assert "Database" in doctor.text


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
        ["policy", "waivers", "list"],
        ["policy", "explain", "--tool", "terminal", "--args-json", "{}"],
        ["policy", "suggest-risk", "--text", "change"],
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


def test_policy_waiver_commands_are_human_only_and_share_cli_slash_path(tmp_path: Path) -> None:
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
