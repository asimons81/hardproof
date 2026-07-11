from __future__ import annotations

import subprocess
from pathlib import Path

from crucible_agent.commands.shared import CommandContext, CommandService
from crucible_agent.domain.enums import RunStage
from crucible_agent.hooks.tool_policy import ToolPolicyHook
from crucible_agent.services.sessions import SessionService
from crucible_agent.services.waivers import WaiverService


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


def test_hook_persists_redacted_trace_for_allowed_action(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    secret = "never-persist-this-value"
    assert hook.pre_tool_call(
        session_id="session-a", tool_name="write_file",
        args={"path": "src.py", "content": secret},
    ) is None
    records = commands.repository.list_policy_decisions(commands.active_run_id())
    assert len(records) == 1
    assert records[0].action == "allow"
    assert records[0].trace[-1].rule_key == records[0].rule_key
    assert secret not in str(records[0].to_dict())
    assert len(records[0].arguments_sha256) == len(records[0].config_sha256) == 64


def test_hook_fails_closed_when_required_policy_audit_cannot_persist(
    tmp_path: Path, monkeypatch
) -> None:
    commands, hook = setup(tmp_path)

    def unavailable(*args, **kwargs):
        raise OSError("database unavailable")

    monkeypatch.setattr(commands.repository, "add_policy_decision", unavailable)
    directive = hook.pre_tool_call(
        session_id="session-a", tool_name="write_file", args={"path": "src.py"}
    )
    assert directive and directive["action"] == "block"
    assert "state.unavailable.fail_closed" in directive["message"]


def test_yaml_project_rule_flows_through_hook_and_durable_trace(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    commands.paths.config.write_text(
        """schema_version: 2
policy:
  rules:
    - key: project.echo.deny
      effect: deny
      tools: [terminal]
      command_regex: '^echo\\b'
      rationale: Echo is disabled for this fixture.
""",
        encoding="utf-8",
    )
    directive = hook.pre_tool_call(
        session_id="session-a", tool_name="terminal", args={"command": "echo hello"}
    )
    assert directive and directive["action"] == "block"
    assert "project.echo.deny" in directive["message"]
    record = commands.repository.list_policy_decisions(commands.active_run_id())[-1]
    assert record.rule_key == "project.echo.deny"
    assert record.trace[-1].outcome == "matched"


def test_hook_applies_exact_waiver_and_persists_waiver_identity(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    commands.repository.transition_run(commands.active_run_id(), RunStage.VERIFY, reason="fixture")
    waiver = WaiverService(commands.repository).create_human(
        run_id=commands.active_run_id(), name="verify-edit",
        rule_key="stage.after_implement.source_mutation", rationale="reviewed exception",
        actor="person", source="cli", created_at="2026-07-11T00:00:00Z",
        expires_at="2099-07-12T00:00:00Z", tool_name="write_file",
        path_scope="generated/**", stage=RunStage.VERIFY,
    )
    assert hook.pre_tool_call(
        session_id="session-a", tool_name="write_file", args={"path": "generated/client.py"}
    ) is None
    record = commands.repository.list_policy_decisions(commands.active_run_id())[-1]
    assert record.action == "allow" and record.waiver_id == waiver.id
    assert record.trace[-1].outcome == "waived"
