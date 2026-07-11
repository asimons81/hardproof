from __future__ import annotations

from pathlib import Path

from crucible_agent.config import PolicyConfig, PolicyRuleConfig
from crucible_agent.domain.enums import RunProfile, RunStage, RunStatus
from crucible_agent.domain.models import Run
from crucible_agent.domain.models import Waiver
from crucible_agent.policy.tool_rules import ToolPolicyContext, evaluate_tool_call


NOW = "2026-07-11T20:00:00Z"


def run(stage: RunStage, profile: RunProfile = RunProfile.STANDARD) -> Run:
    return Run("run-1", ".", "request", profile, stage, RunStatus.ACTIVE, NOW, NOW)


def rule(key: str, effect: str, **kwargs: object) -> PolicyRuleConfig:
    return PolicyRuleConfig(
        key, effect, tuple(kwargs.get("tools", ("terminal",))), str(kwargs.get("rationale", key)),
        kwargs.get("command_regex"), kwargs.get("path_glob"),
        tuple(kwargs.get("profiles", ())), tuple(kwargs.get("stages", ())),
    )  # type: ignore[arg-type]


def context(tmp_path: Path, rules: tuple[PolicyRuleConfig, ...], stage: RunStage = RunStage.IMPLEMENT) -> ToolPolicyContext:
    return ToolPolicyContext(
        run(stage), tmp_path, tmp_path / ".crucible/runs/run-1",
        policy=PolicyConfig("profile", rules, (), {}), config_sha256="a" * 64,
    )


def test_immutable_precedes_matching_project_deny(tmp_path: Path) -> None:
    policy = context(tmp_path, (rule("project.all-terminal", "deny", command_regex=".*"),))
    decision = evaluate_tool_call("terminal", {"command": "git push --force origin main"}, policy)
    assert decision.rule_key == "terminal.immutable.force_push"
    assert [item.rule_key for item in decision.trace] == ["terminal.immutable.force_push"]


def test_project_deny_precedes_approval_regardless_of_config_order(tmp_path: Path) -> None:
    rules = (
        rule("project.publish.approval", "approval", command_regex="npm publish"),
        rule("project.publish.deny", "deny", command_regex="npm publish"),
    )
    decision = evaluate_tool_call("terminal", {"command": "npm publish"}, context(tmp_path, rules))
    assert decision.action == "block" and decision.rule_key == "project.publish.deny"
    assert decision.trace[-1].outcome == "matched"


def test_project_approval_precedes_stage_and_returns_ordered_trace(tmp_path: Path) -> None:
    rules = (rule("project.generator.approval", "approval", tools=("write_file",), path_glob="generated/**"),)
    decision = evaluate_tool_call(
        "write_file", {"path": "generated/client.py"}, context(tmp_path, rules, RunStage.DESIGN)
    )
    assert decision.action == "approval"
    assert decision.rule_key == "project.generator.approval"
    assert decision.trace[-1].rule_key == decision.rule_key


def test_project_allow_cannot_bypass_stage_source_block(tmp_path: Path) -> None:
    rules = (rule("project.generated.allow", "allow", tools=("write_file",), path_glob="generated/**"),)
    decision = evaluate_tool_call(
        "write_file", {"path": "generated/client.py"}, context(tmp_path, rules, RunStage.DESIGN)
    )
    assert decision.action == "block"
    assert decision.rule_key == "stage.before_implement.source_mutation"
    assert all(item.rule_key != "project.generated.allow" for item in decision.trace)
    assert decision.trace[-1].rule_key == decision.rule_key


def test_matching_allow_explains_already_safe_artifact_write(tmp_path: Path) -> None:
    rules = (rule("project.artifact.allow", "allow", tools=("write_file",), path_glob=".crucible/runs/**"),)
    decision = evaluate_tool_call(
        "write_file", {"path": ".crucible/runs/run-1/design.md"},
        context(tmp_path, rules, RunStage.DESIGN),
    )
    assert decision.action == "allow" and decision.rule_key == "project.artifact.allow"
    assert decision.trace[-1].outcome == "matched"


def test_configurable_state_failure_modes_never_open_for_critical_mutation() -> None:
    opened = evaluate_tool_call(
        "write_file", {}, None, state_error=True,
        profile_hint=RunProfile.STANDARD, failure_mode="open",
    )
    closed = evaluate_tool_call(
        "write_file", {}, None, state_error=True,
        profile_hint=RunProfile.QUICK, failure_mode="closed",
    )
    critical = evaluate_tool_call(
        "write_file", {}, None, state_error=True,
        profile_hint=RunProfile.CRITICAL, failure_mode="open",
    )
    assert opened.action == "allow" and opened.rule_key == "state.unavailable.fail_open"
    assert closed.action == "block" and critical.action == "block"
    assert all(item.trace[-1].rule_key == item.rule_key for item in (opened, closed, critical))


def test_exact_scoped_waiver_converts_stage_block_to_audited_allow(tmp_path: Path) -> None:
    policy = context(tmp_path, (), RunStage.DESIGN)
    waiver = Waiver(
        "waiver-1", "run-1", "generated", "stage.before_implement.source_mutation",
        "write_file", None, "generated/**", RunProfile.STANDARD, RunStage.DESIGN,
        "reviewed", "person", "cli", NOW, "2026-07-12T20:00:00Z",
    )
    object.__setattr__(policy, "waivers", (waiver,))
    object.__setattr__(policy, "effective_time", NOW)
    decision = evaluate_tool_call("write_file", {"path": "generated/client.py"}, policy)
    assert decision.action == "allow"
    assert decision.rule_key == "stage.before_implement.source_mutation"
    assert decision.waiver_id == waiver.id
    assert decision.trace[-1].outcome == "waived"
