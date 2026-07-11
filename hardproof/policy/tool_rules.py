"""Deterministic stage-aware mutation and terminal command classification."""

from __future__ import annotations

import fnmatch
import hashlib
import re
from dataclasses import dataclass
from dataclasses import replace
from pathlib import Path
from typing import Any

from hardproof.config import PolicyConfig, PolicyRuleConfig
from hardproof.domain.enums import RunProfile, RunStage
from hardproof.domain.models import PolicyDecision, Run, Waiver
from hardproof.policy.trace import RuleTrace
from hardproof.policy.terminal import TerminalCategory, classify_terminal
from hardproof.policy.waivers import WaiverScope, match_waiver
from hardproof.policy.packs import classify_with_packs


DEFAULT_MUTATING_TOOLS = frozenset({"write_file", "patch", "edit_file", "execute_code", "terminal"})
DEFAULT_POLICY = PolicyConfig("profile", (), (), {})
PATH_KEYS = ("path", "file_path", "target", "destination")


@dataclass(frozen=True, slots=True)
class ToolPolicyContext:
    run: Run
    project_root: Path
    artifact_directory: Path
    mutating_tools: frozenset[str] = DEFAULT_MUTATING_TOOLS
    policy: PolicyConfig = DEFAULT_POLICY
    config_sha256: str = "0" * 64
    waivers: tuple[Waiver, ...] = ()
    effective_time: str = "1970-01-01T00:00:00Z"

    def __init__(
        self,
        run: Run,
        project_root: str | Path,
        artifact_directory: str | Path,
        mutating_tools: frozenset[str] = DEFAULT_MUTATING_TOOLS,
        *,
        policy: PolicyConfig = DEFAULT_POLICY,
        config_sha256: str = "0" * 64,
        waivers: tuple[Waiver, ...] = (),
        effective_time: str = "1970-01-01T00:00:00Z",
    ) -> None:
        object.__setattr__(self, "run", run)
        object.__setattr__(self, "project_root", Path(project_root).resolve())
        object.__setattr__(self, "artifact_directory", Path(artifact_directory).resolve())
        object.__setattr__(self, "mutating_tools", mutating_tools)
        object.__setattr__(self, "policy", policy)
        object.__setattr__(self, "config_sha256", config_sha256)
        object.__setattr__(self, "waivers", tuple(waivers))
        object.__setattr__(self, "effective_time", effective_time)


def _allow(rule: str, reason: str) -> PolicyDecision:
    return PolicyDecision("allow", rule, reason, trace=(RuleTrace(rule, "matched", reason),))


def _block(rule: str, reason: str) -> PolicyDecision:
    return PolicyDecision("block", rule, reason, trace=(RuleTrace(rule, "matched", reason),))


def _approval(rule: str, reason: str) -> PolicyDecision:
    return PolicyDecision(
        "approval", rule, reason, True, (RuleTrace(rule, "matched", reason),)
    )


def _command(args: dict[str, Any]) -> str:
    for key in ("command", "cmd", "code"):
        value = args.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def _target(args: dict[str, Any], root: Path) -> Path | None:
    for key in PATH_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value.strip():
            candidate = Path(value)
            return (candidate if candidate.is_absolute() else root / candidate).resolve()
    return None


def _inside(path: Path | None, parent: Path) -> bool:
    if path is None:
        return False
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _terminal_policy(command: str, context: ToolPolicyContext) -> PolicyDecision | None:
    classification = classify_terminal(command)
    primary = classification.primary
    packed = classify_with_packs(primary.tokens, context.policy.packs)
    if packed is not None:
        primary = packed
    if primary.category is TerminalCategory.AMBIGUOUS:
        return _block(primary.rule_key, primary.explanation)
    if primary.rule_key == "terminal.immutable.force_push":
        return _block("terminal.immutable.force_push", "Force push is blocked by immutable Hardproof policy.")
    if primary.category is TerminalCategory.DESTRUCTIVE:
        if context.run.profile is RunProfile.CRITICAL:
            return _approval(primary.rule_key, "Critical destructive command requires human confirmation.")
        return _block(primary.rule_key, "Destructive command is blocked for this Hardproof profile.")
    if primary.category is TerminalCategory.DEPLOYMENT:
        if context.run.stage is not RunStage.DELIVER:
            return _block("terminal.deployment.before_deliver", "Deployment is blocked before DELIVER.")
        if context.run.profile is RunProfile.CRITICAL:
            return _approval("terminal.deployment.critical", "Critical deployment requires human confirmation.")
    return None


def _relative_target(args: dict[str, Any], context: ToolPolicyContext) -> str | None:
    target = _target(args, context.project_root)
    if target is None:
        return None
    try:
        return target.relative_to(context.project_root).as_posix()
    except ValueError:
        return None


def _rule_matches(
    rule: PolicyRuleConfig,
    tool_name: str,
    args: dict[str, Any],
    context: ToolPolicyContext,
) -> bool:
    if tool_name not in rule.tools:
        return False
    if rule.profiles and context.run.profile not in rule.profiles:
        return False
    if rule.stages and context.run.stage not in rule.stages:
        return False
    if rule.command_regex is not None and re.search(rule.command_regex, _command(args)) is None:
        return False
    if rule.path_glob is not None:
        relative = _relative_target(args, context)
        if relative is None or not fnmatch.fnmatchcase(relative, rule.path_glob):
            return False
    return True


def _rule_trace(rule: PolicyRuleConfig, matched: bool) -> RuleTrace:
    outcome = "matched" if matched else "not_matched"
    explanation = f"Project {rule.effect} rule {rule.key} {'matched' if matched else 'did not match'}."
    return RuleTrace(rule.key, outcome, explanation)


def _waiver_scope(
    rule_key: str, tool_name: str, args: dict[str, Any], context: ToolPolicyContext
) -> WaiverScope:
    command = _command(args)
    command_sha256 = hashlib.sha256(command.encode("utf-8")).hexdigest() if command else None
    return WaiverScope(
        rule_key, tool_name, command_sha256, _relative_target(args, context),
        context.run.profile, context.run.stage, context.run.id, context.effective_time,
    )


def _apply_waiver(
    decision: PolicyDecision,
    tool_name: str,
    args: dict[str, Any],
    context: ToolPolicyContext,
) -> PolicyDecision:
    if decision.action not in {"block", "approval"}:
        return decision
    waiver = match_waiver(context.waivers, _waiver_scope(decision.rule_key, tool_name, args, context))
    if waiver is None:
        return decision
    trace = decision.trace[:-1] + (
        RuleTrace(decision.rule_key, "waived", "An active exact-scope human waiver matched."),
    )
    return PolicyDecision(
        "allow", decision.rule_key, "An active exact-scope human waiver matched.",
        False, trace, waiver.id,
    )


def _core_decision(
    tool_name: str, args: dict[str, Any], context: ToolPolicyContext
) -> PolicyDecision:
    if tool_name not in context.mutating_tools:
        return _allow("tool.non_mutating", "Tool is not configured as mutating.")
    if tool_name == "terminal":
        terminal = _terminal_policy(_command(args), context)
        if terminal is not None:
            return terminal
    target = _target(args, context.project_root)
    if _inside(target, context.artifact_directory):
        return _allow("stage.artifact_write", "Run artifact writes are allowed in every active stage.")
    if context.run.stage is RunStage.IMPLEMENT:
        return _allow("stage.implement.source_mutation", "Project mutation is allowed during IMPLEMENT.")
    if context.run.stage in {RunStage.VERIFY, RunStage.DELIVER, RunStage.LEARN}:
        return _block(
            "stage.after_implement.source_mutation",
            "Source mutation is blocked after IMPLEMENT; transition back to IMPLEMENT first.",
        )
    return _block(
        "stage.before_implement.source_mutation",
        "Source mutation is blocked before IMPLEMENT; record artifacts in the run directory.",
    )


def evaluate_tool_call(
    tool_name: str,
    args: dict[str, Any],
    context: ToolPolicyContext | None,
    *,
    state_error: bool = False,
    profile_hint: RunProfile | None = None,
    failure_mode: str = "profile",
) -> PolicyDecision:
    """Classify a known tool call as allow, block, or approval-required."""
    if state_error:
        fail_closed = failure_mode == "closed" or (
            failure_mode == "profile" and profile_hint in {RunProfile.STANDARD, RunProfile.CRITICAL}
        ) or (profile_hint is RunProfile.CRITICAL and failure_mode == "open")
        if fail_closed and tool_name in DEFAULT_MUTATING_TOOLS:
            return _block(
                "state.unavailable.fail_closed",
                "Hardproof policy state is unavailable; mutation is blocked until recovery.",
            )
        return _allow("state.unavailable.fail_open", "Quick or non-mutating action passes on state error.")
    if context is None:
        return _allow("run.none", "No active Hardproof run applies policy.")

    prefix: list[RuleTrace] = []
    if tool_name == "terminal":
        classification = classify_terminal(_command(args))
        if classification.primary.category is TerminalCategory.IMMUTABLE:
            return _block(
                "terminal.immutable.force_push",
                "Force push is blocked by immutable Hardproof policy.",
            )
        prefix.append(
            RuleTrace(
                "terminal.immutable.force_push",
                "not_matched",
                "Immutable force-push rule did not match.",
            )
        )

    rules = context.policy.rules
    for effect in ("deny", "approval"):
        for rule in (item for item in rules if item.effect == effect):
            matched = _rule_matches(rule, tool_name, args, context)
            prefix.append(_rule_trace(rule, matched))
            if matched:
                action = "block" if effect == "deny" else "approval"
                decision = (
                    _block(rule.key, f"Project deny rule {rule.key} matched.")
                    if action == "block"
                    else _approval(rule.key, f"Project approval rule {rule.key} matched.")
                )
                return _apply_waiver(
                    replace(decision, trace=tuple(prefix)), tool_name, args, context
                )

    core = _core_decision(tool_name, args, context)
    if core.action != "allow":
        return _apply_waiver(
            replace(core, trace=tuple(prefix) + core.trace), tool_name, args, context
        )

    core_trace = RuleTrace(core.rule_key, "superseded", core.reason)
    allow_traces: list[RuleTrace] = []
    for rule in (item for item in rules if item.effect == "allow"):
        matched = _rule_matches(rule, tool_name, args, context)
        allow_traces.append(_rule_trace(rule, matched))
        if matched:
            decision = _allow(rule.key, f"Project allow rule {rule.key} matched.")
            return replace(decision, trace=tuple(prefix) + (core_trace,) + tuple(allow_traces))
    return replace(core, trace=tuple(prefix) + tuple(allow_traces) + core.trace)
