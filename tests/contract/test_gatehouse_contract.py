from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from hardproof.domain.models import PolicyDecision
from hardproof.policy.trace import IMMUTABLE_RULE_PREFIX, STABLE_V01_RULE_KEYS, RuleTrace


def test_v02_policy_trace_is_immutable_ordered_and_serializable() -> None:
    entry = RuleTrace("stage.artifact_write", "matched", "artifact path is allowed")
    decision = PolicyDecision(
        "allow", "stage.artifact_write", "artifact path is allowed", trace=(entry,)
    )
    assert decision.trace == (entry,)
    assert decision.to_dict()["trace"] == [entry.to_dict()]
    assert PolicyDecision.from_dict(decision.to_dict()) == decision
    with pytest.raises(FrozenInstanceError):
        entry.outcome = "waived"  # type: ignore[misc]


def test_v01_rule_keys_are_frozen_and_immutable_namespace_is_reserved() -> None:
    assert IMMUTABLE_RULE_PREFIX == "terminal.immutable."
    assert STABLE_V01_RULE_KEYS == frozenset(
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


def test_policy_decision_requires_trace_final_key_to_match() -> None:
    entry = RuleTrace("run.none", "matched", "no active run")
    with pytest.raises(ValueError, match="final trace rule"):
        PolicyDecision("allow", "tool.non_mutating", "mismatch", trace=(entry,))
