from __future__ import annotations

import pytest

from hardproof.domain.enums import (
    ApprovalGate,
    ArtifactKind,
    EvidenceStatus,
    RiskLevel,
    RunProfile,
    RunStage,
    RunStatus,
    TaskStatus,
)


@pytest.mark.parametrize(
    ("enum_type", "value"),
    [
        (RunProfile, "standard"),
        (RunStage, "IMPLEMENT"),
        (RunStatus, "active"),
        (ArtifactKind, "design"),
        (ApprovalGate, "plan"),
        (TaskStatus, "completed"),
        (RiskLevel, "critical"),
        (EvidenceStatus, "passed"),
    ],
)
def test_string_enums_accept_documented_values(enum_type: type, value: str) -> None:
    assert enum_type(value).value == value


@pytest.mark.parametrize("enum_type", [RunProfile, RunStage, RunStatus, EvidenceStatus])
def test_string_enums_reject_unknown_values(enum_type: type) -> None:
    with pytest.raises(ValueError):
        enum_type("not-a-protocol-value")


def test_stage_set_includes_terminal_states() -> None:
    assert {RunStage.PAUSED, RunStage.ABORTED, RunStage.COMPLETE} <= set(RunStage)
