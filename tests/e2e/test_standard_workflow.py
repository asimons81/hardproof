from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from hardproof.commands.shared import CommandContext, CommandService
from hardproof.domain.enums import ArtifactKind, EvidenceStatus, RunStage, TaskStatus
from hardproof.plugin import register
from hardproof.services.artifacts import ArtifactService
from hardproof.services.evidence import CommandResult, EvidenceService
from hardproof.services.reports import ReportService
from hardproof.tools.handlers import HandlerDependencies, create_handlers


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


class LocalPytestRunner:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        assert command == "python -m pytest"
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=self.project_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return CommandResult(completed.returncode, completed.stdout + completed.stderr)


def git_project(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
    (root / ".gitignore").write_text(".hardproof/\n__pycache__/\n.pytest_cache/\n.DS_Store\n", encoding="utf-8")
    (root / "tiny.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    (root / "test_tiny.py").write_text("from tiny import value\n\ndef test_value():\n    assert value() == 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)


def test_full_standard_workflow_survives_restart_and_reproves_after_edit(tmp_path: Path) -> None:
    git_project(tmp_path)
    plugin = FakePluginContext()
    register(plugin)
    assert len(plugin.tools) == 6
    assert len(plugin.skills) == 9
    assert "hardproof" in plugin.commands and "hardproof" in plugin.cli_commands

    commands = CommandService(CommandContext(
        tmp_path, actor="human", source="cli", session_id="session-e2e"
    ))
    handlers = create_handlers(HandlerDependencies(commands))

    started = handlers["hardproof_run"]({
        "action": "start", "profile": "standard", "request": "Change value to two",
    })
    assert '"ok":true' in started
    run_id = commands.active_run_id()
    run_dir = commands.paths.run_directory(run_id)

    commands.run_service.transition(
        run_id, RunStage.DISCOVERY, commands.transition_facts(run_id), reason="intake understood"
    )
    artifacts = ArtifactService(commands.repository, run_dir)
    artifacts.write(run_id, ArtifactKind.DISCOVERY, "discovery.md", "# Discovery\nValue is one.\n")
    commands.run_service.transition(
        run_id, RunStage.DESIGN, commands.transition_facts(run_id), reason="discovery recorded"
    )
    artifacts.write(run_id, ArtifactKind.DESIGN, "design.md", "# Design\nReturn two.\n")

    denied = commands.run_service.try_transition(
        run_id, RunStage.PLAN, commands.transition_facts(run_id), reason="too early"
    )
    assert not denied.allowed and "human design approval missing" in denied.blockers
    commands.execute(["approve", "design", "reviewed"])
    commands.run_service.transition(
        run_id, RunStage.PLAN, commands.transition_facts(run_id), reason="design approved"
    )
    artifacts.write(run_id, ArtifactKind.PLAN, "plan.md", "# Plan\nEdit code and test.\n")
    commands.execute(["approve", "plan", "reviewed"])
    commands.run_service.transition(
        run_id, RunStage.IMPLEMENT, commands.transition_facts(run_id), reason="plan approved"
    )

    task = handlers["hardproof_task"]({
        "action": "create", "key": "T1", "title": "Change value",
        "description": "Return two", "risk": "low", "acceptance": ["test passes"],
        "files": ["tiny.py", "test_tiny.py"],
    })
    assert '"ok":true' in task
    (tmp_path / "tiny.py").write_text("def value():\n    return 2\n", encoding="utf-8")
    (tmp_path / "test_tiny.py").write_text("from tiny import value\n\ndef test_value():\n    assert value() == 2\n", encoding="utf-8")
    handlers["hardproof_task"]({
        "action": "update", "key": "T1", "status": TaskStatus.COMPLETED.value,
        "acceptance_notes": "focused test passes",
    })
    commands.run_service.transition(
        run_id, RunStage.REVIEW, commands.transition_facts(run_id), reason="task complete"
    )
    artifacts.write(run_id, ArtifactKind.REVIEW, "review.md", "# Review\nApproved.\n")
    commands.repository.append_event(run_id, "review_approved", {"reviewer": "independent-fixture"})
    commands.run_service.transition(
        run_id, RunStage.VERIFY, commands.transition_facts(run_id), reason="review approved"
    )

    evidence = EvidenceService(commands.repository, tmp_path, run_dir, LocalPytestRunner(tmp_path))
    first = evidence.verify(run_id)
    assert first[0].status is EvidenceStatus.PASSED and evidence.is_fresh(first[0])
    (tmp_path / "tiny.py").write_text("def value():\n    return 2  # clarified\n", encoding="utf-8")
    assert evidence.freshness_status(first[0]) is EvidenceStatus.STALE
    blocked = commands.run_service.try_transition(
        run_id, RunStage.DELIVER, commands.transition_facts(run_id), reason="stale attempt"
    )
    assert not blocked.allowed and "found 0" in blocked.blockers[0]
    second = evidence.verify(run_id)
    assert evidence.is_fresh(second[0])
    commands.run_service.transition(
        run_id, RunStage.DELIVER, commands.transition_facts(run_id), reason="fresh proof"
    )

    reports = ReportService(commands.repository, tmp_path, run_dir)
    exported = reports.export(run_id, format="both")
    report_text = exported["markdown"].read_text(encoding="utf-8")
    artifacts.write(run_id, ArtifactKind.COMPLETION, "completion.md", report_text)
    commands.run_service.transition(
        run_id, RunStage.LEARN, commands.transition_facts(run_id), reason="report ready"
    )
    artifacts.write(run_id, ArtifactKind.LEARNING, "learning.md", "# Learning\nKeep evidence fresh.\n")
    commands.run_service.transition(
        run_id, RunStage.COMPLETE, commands.transition_facts(run_id), reason="learning captured"
    )

    restarted = CommandService(CommandContext(tmp_path, actor="human", source="cli"))
    completed = restarted.repository.get_run(run_id)
    assert completed.stage is RunStage.COMPLETE
    assert restarted.repository.list_tasks(run_id)[0].status is TaskStatus.COMPLETED
    assert restarted.repository.list_evidence(run_id)[-1].status is EvidenceStatus.PASSED
