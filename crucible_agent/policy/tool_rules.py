"""Deterministic stage-aware mutation and terminal command classification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crucible_agent.domain.enums import RunProfile, RunStage
from crucible_agent.domain.models import PolicyDecision, Run


DEFAULT_MUTATING_TOOLS = frozenset({"write_file", "patch", "edit_file", "execute_code", "terminal"})
PATH_KEYS = ("path", "file_path", "target", "destination")
_FORCE_PUSH = re.compile(r"(?:^|[;&|]\s*)git\s+push\b[^\r\n]*(?:--force(?:-with-lease)?\b|(?:^|\s)-f(?:\s|$))", re.I)
_RESET_HARD = re.compile(r"\bgit\s+reset\s+--hard\b", re.I)
_GIT_CLEAN = re.compile(r"\bgit\s+clean\b[^\r\n]*\s-[a-z]*f", re.I)
_DELETE_TREE = re.compile(r"(?:\brm\s+-[a-z]*r[a-z]*f|\bremove-item\b[^\r\n]*-recurse|\bdel\s+/s\b)", re.I)
_DEPLOY = re.compile(
    r"\b(?:vercel\s+deploy|kubectl\s+(?:apply|delete)|terraform\s+(?:apply|destroy)|npm\s+publish|twine\s+upload|docker\s+push)\b",
    re.I,
)


@dataclass(frozen=True, slots=True)
class ToolPolicyContext:
    run: Run
    project_root: Path
    artifact_directory: Path
    mutating_tools: frozenset[str] = DEFAULT_MUTATING_TOOLS

    def __init__(
        self,
        run: Run,
        project_root: str | Path,
        artifact_directory: str | Path,
        mutating_tools: frozenset[str] = DEFAULT_MUTATING_TOOLS,
    ) -> None:
        object.__setattr__(self, "run", run)
        object.__setattr__(self, "project_root", Path(project_root).resolve())
        object.__setattr__(self, "artifact_directory", Path(artifact_directory).resolve())
        object.__setattr__(self, "mutating_tools", mutating_tools)


def _allow(rule: str, reason: str) -> PolicyDecision:
    return PolicyDecision("allow", rule, reason)


def _block(rule: str, reason: str) -> PolicyDecision:
    return PolicyDecision("block", rule, reason)


def _approval(rule: str, reason: str) -> PolicyDecision:
    return PolicyDecision("approval", rule, reason, True)


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
    if _FORCE_PUSH.search(command):
        return _block("terminal.immutable.force_push", "Force push is blocked by immutable Crucible policy.")
    destructive_rule: str | None = None
    if _RESET_HARD.search(command):
        destructive_rule = "terminal.destructive.git_reset_hard"
    elif _GIT_CLEAN.search(command):
        destructive_rule = "terminal.destructive.git_clean"
    elif _DELETE_TREE.search(command):
        destructive_rule = "terminal.destructive.recursive_delete"
    if destructive_rule:
        if context.run.profile is RunProfile.CRITICAL:
            return _approval(destructive_rule, "Critical destructive command requires human confirmation.")
        return _block(destructive_rule, "Destructive command is blocked for this Crucible profile.")
    if _DEPLOY.search(command):
        if context.run.stage is not RunStage.DELIVER:
            return _block("terminal.deployment.before_deliver", "Deployment is blocked before DELIVER.")
        if context.run.profile is RunProfile.CRITICAL:
            return _approval("terminal.deployment.critical", "Critical deployment requires human confirmation.")
    return None


def evaluate_tool_call(
    tool_name: str,
    args: dict[str, Any],
    context: ToolPolicyContext | None,
    *,
    state_error: bool = False,
    profile_hint: RunProfile | None = None,
) -> PolicyDecision:
    """Classify a known tool call as allow, block, or approval-required."""
    if state_error:
        if profile_hint in {RunProfile.STANDARD, RunProfile.CRITICAL} and tool_name in DEFAULT_MUTATING_TOOLS:
            return _block(
                "state.unavailable.fail_closed",
                "Crucible policy state is unavailable; mutation is blocked until recovery.",
            )
        return _allow("state.unavailable.fail_open", "Quick or non-mutating action passes on state error.")
    if context is None:
        return _allow("run.none", "No active Crucible run applies policy.")
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
