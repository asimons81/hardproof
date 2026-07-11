from __future__ import annotations

import pytest

from hardproof.domain.enums import RiskLevel, RunProfile, RunStage
from hardproof.domain.models import PolicyDecisionRecord, RiskSuggestion, Waiver
from hardproof.policy.trace import RuleTrace


NOW = "2026-07-11T18:00:00Z"
LATER = "2026-07-12T18:00:00Z"


def test_policy_decision_record_requires_complete_matching_trace() -> None:
    trace = (RuleTrace("stage.artifact_write", "matched", "artifact path"),)
    record = PolicyDecisionRecord(
        "policy-1", "run-1", "write_file", "allow", "stage.artifact_write",
        "artifact path", trace, "a" * 64, "b" * 64, None, RiskLevel.LOW, NOW,
    )
    assert PolicyDecisionRecord.from_dict(record.to_dict()) == record
    with pytest.raises(ValueError, match="final trace rule"):
        PolicyDecisionRecord(
            "policy-2", "run-1", "write_file", "allow", "tool.non_mutating",
            "mismatch", trace, "a" * 64, "b" * 64, None, RiskLevel.LOW, NOW,
        )


def test_waiver_rejects_immutable_rule_and_invalid_expiry() -> None:
    with pytest.raises(ValueError, match="immutable"):
        Waiver(
            "waiver-1", None, "never", "terminal.immutable.force_push", None, None,
            None, None, None, "reason", "person", "cli", NOW, LATER,
        )
    with pytest.raises(ValueError, match="after creation"):
        Waiver(
            "waiver-2", None, "expired", "project.example", None, None, None,
            RunProfile.STANDARD, RunStage.IMPLEMENT, "reason", "person", "cli", NOW, NOW,
        )


def test_risk_suggestion_round_trips_override_rationale() -> None:
    suggestion = RiskSuggestion(
        "risk-1", "run-1", "task-1", RiskLevel.HIGH,
        ("migration path", "database command"), RiskLevel.CRITICAL,
        "production database", NOW, "person", "cli", NOW,
    )
    assert RiskSuggestion.from_dict(suggestion.to_dict()) == suggestion
