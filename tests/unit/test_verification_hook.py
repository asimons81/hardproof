from __future__ import annotations

import subprocess
from pathlib import Path

from crucible_agent.commands.shared import CommandContext, CommandService
from crucible_agent.domain.enums import RunStage
from crucible_agent.hooks.verification import VerificationHook
from crucible_agent.services.evidence import CommandResult, EvidenceService
from crucible_agent.services.sessions import SessionService


class Runner:
    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        return CommandResult(0, "passed")


def setup(tmp_path: Path) -> tuple[CommandService, VerificationHook, EvidenceService]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / "code.py").write_text("VALUE=1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "code.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "initial"], check=True)
    commands = CommandService(CommandContext(tmp_path, actor="user", source="cli"))
    commands.execute(["start", "quick", "verify"])
    commands.repository.transition_run(commands.active_run_id(), RunStage.VERIFY, reason="fixture")
    service = EvidenceService(
        commands.repository, tmp_path,
        commands.paths.run_directory(commands.active_run_id()), Runner(),
    )
    hook = VerificationHook(
        SessionService(commands.repository, commands.paths), commands, service
    )
    return commands, hook, service


def test_one_shot_pre_verify_nudge_for_missing_evidence(tmp_path: Path) -> None:
    _, hook, _ = setup(tmp_path)
    first = hook(session_id="session-a", code_changed=True, attempt=0)
    assert first and first["action"] == "continue"
    assert "missing" in first["message"]
    assert hook(session_id="session-a", code_changed=True, attempt=1) is None


def test_fresh_evidence_allows_completion_hook(tmp_path: Path) -> None:
    commands, hook, service = setup(tmp_path)
    service.verify(commands.active_run_id())
    assert hook(session_id="session-a", code_changed=True, attempt=0) is None


def test_no_code_change_or_early_stage_is_noop(tmp_path: Path) -> None:
    commands, hook, _ = setup(tmp_path)
    assert hook(session_id="session-a", code_changed=False, attempt=0) is None
    commands.repository.transition_run(commands.active_run_id(), RunStage.IMPLEMENT, reason="fixture")
    assert hook(session_id="session-a", code_changed=True, attempt=0) is None
