from __future__ import annotations

import json
import subprocess
from pathlib import Path

from hardproof.commands.shared import CommandContext, CommandService
from hardproof.domain.enums import RunStage
from hardproof.hooks.tool_policy import ToolPolicyHook
from hardproof.services.sessions import SessionService


def setup(tmp_path: Path) -> tuple[CommandService, ToolPolicyHook]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commands = CommandService(CommandContext(tmp_path, actor="person", source="cli"))
    commands.execute(["start", "standard", "explain policy"])
    commands.repository.transition_run(commands.active_run_id(), RunStage.VERIFY, reason="fixture")
    hook = ToolPolicyHook(SessionService(commands.repository, commands.paths), commands)
    return commands, hook


def test_historical_explanation_reproduces_durable_decision(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    directive = hook.pre_tool_call(
        session_id="session-a", tool_name="write_file", args={"path": "src.py"}
    )
    assert directive and directive["action"] == "block"
    record = commands.repository.list_policy_decisions(commands.active_run_id())[0]
    assert record.sequence == 1
    payload = commands.explain_policy(event_sequence=record.sequence)
    assert payload["action"] == record.action
    assert payload["rule_key"] == record.rule_key
    assert payload["trace"] == [item.to_dict() for item in record.trace]
    assert payload["arguments_sha256"] == record.arguments_sha256


def test_hypothetical_explanation_is_redacted_deterministic_and_read_only(tmp_path: Path) -> None:
    commands, _ = setup(tmp_path)
    secret = "token=never-return-this"
    before = commands.repository.list_policy_decisions(commands.active_run_id())
    first = commands.explain_policy(
        tool_name="terminal", args={"command": "git reset --hard HEAD", "content": secret},
        now="2026-07-11T20:00:00Z",
    )
    second = commands.explain_policy(
        tool_name="terminal", args={"command": "git reset --hard HEAD", "content": secret},
        now="2026-07-11T20:00:00Z",
    )
    assert first == second
    assert first["action"] == "block"
    assert len(first["arguments_sha256"]) == len(first["config_sha256"]) == 64
    assert secret not in json.dumps(first)
    assert commands.repository.list_policy_decisions(commands.active_run_id()) == before


def test_policy_explain_command_has_stable_human_and_json_forms(tmp_path: Path) -> None:
    commands, hook = setup(tmp_path)
    hook.pre_tool_call(session_id="session-a", tool_name="write_file", args={"path": "src.py"})
    human = commands.execute(["policy", "explain", "--event", "1"]).text
    encoded = commands.execute([
        "policy", "explain", "--event", "1", "--format", "json"
    ]).text
    assert "Action: block" in human and "Rule:" in human and "Trace:" in human
    assert json.loads(encoded)["sequence"] == 1
    assert encoded == commands.execute([
        "policy", "explain", "--event", "1", "--format", "json"
    ]).text
