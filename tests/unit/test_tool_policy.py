from __future__ import annotations

from pathlib import Path

import pytest

from hardproof.domain.enums import RunProfile, RunStage, RunStatus
from hardproof.domain.models import Run
from hardproof.policy.tool_rules import ToolPolicyContext, evaluate_tool_call


NOW = "2026-07-11T09:00:00Z"


def run(stage: RunStage, profile: RunProfile = RunProfile.STANDARD) -> Run:
    return Run("run-1", ".", "request", profile, stage, RunStatus.ACTIVE, NOW, NOW)


def context(tmp_path: Path, stage: RunStage, profile: RunProfile = RunProfile.STANDARD) -> ToolPolicyContext:
    return ToolPolicyContext(
        run(stage, profile),
        project_root=tmp_path,
        artifact_directory=tmp_path / ".hardproof" / "runs" / "run-1",
    )


def test_artifact_write_allowed_during_design(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "write_file", {"path": str(tmp_path / ".hardproof/runs/run-1/design.md")},
        context(tmp_path, RunStage.DESIGN),
    )
    assert decision.action == "allow"
    assert decision.rule_key == "stage.artifact_write"


def test_source_write_blocked_during_design(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "write_file", {"path": str(tmp_path / "src/module.py")},
        context(tmp_path, RunStage.DESIGN),
    )
    assert decision.action == "block"
    assert decision.rule_key == "stage.before_implement.source_mutation"


def test_source_write_allowed_during_implement(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "edit_file", {"file_path": str(tmp_path / "src/module.py")},
        context(tmp_path, RunStage.IMPLEMENT),
    )
    assert decision.action == "allow"


def test_reset_hard_requires_human_approval_in_critical(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "terminal", {"command": "git reset --hard HEAD~1"},
        context(tmp_path, RunStage.IMPLEMENT, RunProfile.CRITICAL),
    )
    assert decision.action == "approval"
    assert decision.rule_key == "terminal.destructive.git_reset_hard"


@pytest.mark.parametrize("command", ["git push --force origin main", "git push -f", "git push --force-with-lease"])
def test_force_push_is_always_blocked(tmp_path: Path, command: str) -> None:
    decision = evaluate_tool_call(
        "terminal", {"command": command}, context(tmp_path, RunStage.DELIVER, RunProfile.CRITICAL)
    )
    assert decision.action == "block"
    assert decision.rule_key == "terminal.immutable.force_push"


def test_deployment_blocked_before_deliver(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "terminal", {"command": "vercel deploy --prod"},
        context(tmp_path, RunStage.IMPLEMENT),
    )
    assert decision.action == "block"
    assert decision.rule_key == "terminal.deployment.before_deliver"


@pytest.mark.parametrize(
    ("command", "rule"),
    [
        ("git clean -fd", "terminal.destructive.git_clean"),
        ("Remove-Item build -Recurse", "terminal.destructive.recursive_delete"),
    ],
)
def test_destructive_commands_are_blocked_outside_critical(
    tmp_path: Path, command: str, rule: str
) -> None:
    decision = evaluate_tool_call(
        "terminal", {"cmd": command}, context(tmp_path, RunStage.IMPLEMENT)
    )
    assert decision.action == "block"
    assert decision.rule_key == rule


def test_critical_deployment_requires_approval_at_deliver(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "terminal",
        {"code": "twine upload dist/*"},
        context(tmp_path, RunStage.DELIVER, RunProfile.CRITICAL),
    )
    assert decision.action == "approval"
    assert decision.rule_key == "terminal.deployment.critical"


def test_verify_blocks_unrelated_source_edit(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "patch", {"path": str(tmp_path / "src/module.py")}, context(tmp_path, RunStage.VERIFY)
    )
    assert decision.action == "block"
    assert decision.rule_key == "stage.after_implement.source_mutation"


@pytest.mark.parametrize(
    ("profile", "expected"),
    [(RunProfile.QUICK, "allow"), (RunProfile.STANDARD, "block"), (RunProfile.CRITICAL, "block")],
)
def test_state_load_failure_behavior_by_profile(
    tmp_path: Path, profile: RunProfile, expected: str
) -> None:
    decision = evaluate_tool_call(
        "write_file", {"path": str(tmp_path / "src.py")}, None,
        state_error=True, profile_hint=profile,
    )
    assert decision.action == expected


def test_no_active_run_passes_through(tmp_path: Path) -> None:
    assert evaluate_tool_call("write_file", {"path": str(tmp_path / "src.py")}, None).action == "allow"


def test_mutating_tool_names_are_feature_configurable(tmp_path: Path) -> None:
    policy = ToolPolicyContext(
        run(RunStage.DESIGN), tmp_path, tmp_path / ".hardproof/runs/run-1",
        mutating_tools=frozenset({"future_write"}),
    )
    assert evaluate_tool_call("future_write", {"path": "src.py"}, policy).action == "block"
    assert evaluate_tool_call("write_file", {"path": "src.py"}, policy).action == "allow"


def test_missing_target_is_never_treated_as_an_artifact_write(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "write_file", {"destination": "   "}, context(tmp_path, RunStage.DESIGN)
    )
    assert decision.action == "block"
    assert decision.rule_key == "stage.before_implement.source_mutation"


def test_chained_force_push_cannot_hide_after_safe_command(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "terminal",
        {"command": "python -m pytest && git push origin main --force-with-lease"},
        context(tmp_path, RunStage.DELIVER, RunProfile.CRITICAL),
    )
    assert decision.action == "block"
    assert decision.rule_key == "terminal.immutable.force_push"


def test_malformed_terminal_input_is_blocked_with_safe_explanation(tmp_path: Path) -> None:
    decision = evaluate_tool_call(
        "terminal", {"command": "echo 'unterminated"}, context(tmp_path, RunStage.IMPLEMENT)
    )
    assert decision.action == "block"
    assert decision.rule_key == "terminal.ambiguous"
    assert "unterminated" not in decision.reason
