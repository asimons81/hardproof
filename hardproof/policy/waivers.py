"""Pure protected-namespace and exact-scope waiver matching."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from hardproof.domain.enums import RunProfile, RunStage
from hardproof.domain.models import Waiver


PROTECTED_RULE_PREFIXES = (
    "terminal.immutable.",
    "state.",
    "evidence.",
    "verification.",
    "migration.",
    "approval.authenticity.",
)


def is_protected_rule(rule_key: str) -> bool:
    return rule_key.startswith(PROTECTED_RULE_PREFIXES)


@dataclass(frozen=True, slots=True)
class WaiverScope:
    rule_key: str
    tool_name: str | None
    command_sha256: str | None
    path: str | None
    profile: RunProfile
    stage: RunStage
    run_id: str
    effective_time: str


def _matches(waiver: Waiver, scope: WaiverScope) -> bool:
    if is_protected_rule(scope.rule_key) or waiver.rule_key != scope.rule_key:
        return False
    if waiver.revoked_at is not None:
        return False
    if not (waiver.created_at <= scope.effective_time < waiver.expires_at):
        return False
    if waiver.run_id is not None and waiver.run_id != scope.run_id:
        return False
    if waiver.tool_name is not None and waiver.tool_name != scope.tool_name:
        return False
    if waiver.command_sha256 is not None and waiver.command_sha256 != scope.command_sha256:
        return False
    if waiver.path_scope is not None and (
        scope.path is None or not fnmatch.fnmatchcase(scope.path, waiver.path_scope)
    ):
        return False
    if waiver.profile is not None and waiver.profile is not scope.profile:
        return False
    if waiver.stage is not None and waiver.stage is not scope.stage:
        return False
    return True


def match_waiver(waivers: tuple[Waiver, ...], scope: WaiverScope) -> Waiver | None:
    """Return the first deterministically ordered active exact-scope waiver."""
    return next((waiver for waiver in waivers if _matches(waiver, scope)), None)
