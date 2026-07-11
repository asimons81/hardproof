from __future__ import annotations

import subprocess
from pathlib import Path

from crucible_agent.commands.shared import CommandContext, CommandService
from crucible_agent.domain.enums import RunStage
from crucible_agent.hooks.tool_policy import ToolPolicyHook
from crucible_agent.services.sessions import SessionService


def setup(tmp_path: Path) -> tuple[CommandService, ToolPolicyHook]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commands = CommandService(CommandContext(tmp_path, actor="user", source="cli"))
    commands.execute(["start", "critical", "Policy test"])
    commands.repository.transition_run(commands.active_run_id(), RunStage.IMPLEMENT, reason="fixture")
    sessions = SessionService(commands.repository, commands.paths)
    return commands, ToolPolicyHook(sessions, commands)


def test_hook_returns_public_hermes_approval_directive_and_audits_rule(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    directive = hook.pre_tool_call(
        session_id="session-a", tool_name="terminal", args={"command": "git reset --hard HEAD"}
    )
    assert directive == {
        "action": "approve",
        "message": "Critical destructive command requires human confirmation.",
        "rule_key": "crucible:terminal.destructive.git_reset_hard",
    }
    events = commands.repository.list_events(commands.active_run_id())
    assert events[-1].payload["rule_key"] == "terminal.destructive.git_reset_hard"


def test_hook_block_event_contains_no_secret_values(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    commands.repository.transition_run(commands.active_run_id(), RunStage.VERIFY, reason="fixture")
    secret = "token=never-store-this"
    directive = hook.pre_tool_call(
        session_id="session-a", tool_name="write_file",
        args={"path": "src.py", "content": secret},
    )
    assert directive and directive["action"] == "block"
    event = commands.repository.list_events(commands.active_run_id())[-1]
    assert "never-store-this" not in str(event.payload)


def test_post_tool_audit_records_metadata_not_output(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    hook.post_tool_call(
        session_id="session-a", tool_name="terminal", args={"command": "git status"},
        result="token=secret-output", duration_ms=12.5, status="ok",
    )
    event = commands.repository.list_events(commands.active_run_id())[-1]
    assert event.event_type == "tool_observed"
    assert event.payload["duration_ms"] == 12.5
    assert "secret-output" not in str(event.payload)


def test_hook_no_active_run_is_noop(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commands = CommandService(CommandContext(tmp_path, actor="user", source="cli"))
    hook = ToolPolicyHook(SessionService(commands.repository, commands.paths), commands)
    assert hook.pre_tool_call(session_id="none", tool_name="write_file", args={"path": "x"}) is None
