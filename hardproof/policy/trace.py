"""Stable, immutable policy trace contracts shared by every adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


IMMUTABLE_RULE_PREFIX = "terminal.immutable."
STABLE_V01_RULE_KEYS = frozenset(
    {
        "run.none",
        "stage.after_implement.source_mutation",
        "stage.artifact_write",
        "stage.before_implement.source_mutation",
        "stage.implement.source_mutation",
        "state.unavailable.fail_closed",
        "state.unavailable.fail_open",
        "terminal.deployment.before_deliver",
        "terminal.deployment.critical",
        "terminal.destructive.git_clean",
        "terminal.destructive.git_reset_hard",
        "terminal.destructive.recursive_delete",
        "terminal.immutable.force_push",
        "tool.non_mutating",
    }
)
TRACE_OUTCOMES = frozenset({"matched", "not_matched", "superseded", "waived"})


@dataclass(frozen=True, slots=True)
class RuleTrace:
    """One bounded explanation step in deterministic evaluation order."""

    rule_key: str
    outcome: str
    explanation: str

    def __post_init__(self) -> None:
        if not self.rule_key.strip() or not self.explanation.strip():
            raise ValueError("trace rule_key and explanation must be non-empty")
        if self.outcome not in TRACE_OUTCOMES:
            raise ValueError(f"trace outcome must be one of {sorted(TRACE_OUTCOMES)}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
