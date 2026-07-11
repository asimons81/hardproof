from __future__ import annotations

import json
import subprocess
from pathlib import Path

from crucible_agent.plugin import register
from crucible_agent.commands.shared import CommandContext, CommandService


class FakePluginContext:
    profile_name = "default"

    def __init__(self) -> None:
        self.tools = {}
        self.hooks = {}
        self.skills = {}
        self.commands = {}
        self.cli_commands = {}

    def register_tool(self, name, handler, **kwargs): self.tools[name] = handler
    def register_hook(self, name, callback): self.hooks.setdefault(name, []).append(callback)
    def register_skill(self, name, path, description=""): self.skills[name] = path
    def register_command(self, name, handler, **kwargs): self.commands[name] = handler
    def register_cli_command(self, name, *args, **kwargs): self.cli_commands[name] = (args, kwargs)
    def dispatch_tool(self, tool_name, args, **kwargs): return '{"output":"passed","exit_code":0}'


def test_registered_report_tool_explains_hypothetical_without_raw_arguments(
    tmp_path: Path, monkeypatch
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    context = FakePluginContext()
    register(context)
    started = json.loads(context.tools["crucible_run"]({
        "action": "start", "profile": "standard", "request": "explain tool",
    }))
    assert started["ok"]
    secret = "token=must-not-return"
    result = json.loads(context.tools["crucible_report"]({
        "action": "policy_explain",
        "tool_name": "terminal",
        "arguments": {"command": "git reset --hard HEAD", "content": secret},
    }))
    assert result["ok"]
    explanation = result["explanation"]
    assert explanation["rule_key"] == "terminal.destructive.git_reset_hard"
    assert explanation["trace"][-1]["rule_key"] == explanation["rule_key"]
    assert secret not in json.dumps(result)


def test_registered_risk_suggestion_is_pure_and_advisory(tmp_path: Path, monkeypatch) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    context = FakePluginContext()
    register(context)
    json.loads(context.tools["crucible_run"]({
        "action": "start", "profile": "standard", "request": "risk tool",
    }))
    commands = CommandService(CommandContext(tmp_path, actor="model", source="tool"))
    run_id = commands.active_run_id()
    before_profile = commands.repository.get_run(run_id).profile
    result = json.loads(context.tools["crucible_report"]({
        "action": "risk_suggest", "text": "Deploy a production migration",
        "files": ["migrations/003.sql"], "command": "kubectl apply -f app.yaml",
    }))
    assert result["advisory"] is True and result["suggested_risk"] == "critical"
    assert commands.repository.list_risk_suggestions(run_id) == ()
    assert commands.repository.get_run(run_id).profile is before_profile
