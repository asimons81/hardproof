from __future__ import annotations

from datetime import datetime, timezone

import pytest

from crucible_agent.domain.enums import EvidenceStatus, RunProfile, RunStage, RunStatus
from crucible_agent.domain.models import Evidence, Run, TransitionResult, new_id
from crucible_agent.domain.snapshots import WorkspaceSnapshot


def test_run_serialization_round_trip() -> None:
    run = Run.create(project_root="C:/work/project", request="Add a safe feature", profile=RunProfile.STANDARD)
    assert Run.from_dict(run.to_dict()) == run
    assert run.stage is RunStage.INTAKE
    assert run.status is RunStatus.ACTIVE


def test_timestamps_normalize_to_utc() -> None:
    run = Run(
        id="run-1",
        project_root="C:/work/project",
        request="request",
        profile=RunProfile.QUICK,
        stage=RunStage.INTAKE,
        status=RunStatus.ACTIVE,
        created_at="2026-07-10T12:00:00-05:00",
        updated_at=datetime(2026, 7, 10, 17, tzinfo=timezone.utc),
    )
    assert run.created_at == "2026-07-10T17:00:00Z"
    assert run.updated_at == "2026-07-10T17:00:00Z"


def test_invalid_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        Run.create(".", "request", RunProfile.QUICK, now="yesterday")


def test_generated_ids_are_unique_and_prefixed() -> None:
    ids = {new_id("run") for _ in range(200)}
    assert len(ids) == 200
    assert all(identifier.startswith("run-") for identifier in ids)


def test_transition_result_invariants() -> None:
    allowed = TransitionResult.allow(RunStage.DESIGN)
    assert allowed.allowed and not allowed.blockers
    denied = TransitionResult.deny(RunStage.DESIGN, "discovery artifact missing")
    assert not denied.allowed and denied.blockers
    with pytest.raises(ValueError):
        TransitionResult(True, RunStage.DESIGN, ("contradiction",))
    with pytest.raises(ValueError):
        TransitionResult(False, RunStage.DESIGN, ())


def test_evidence_round_trip_preserves_enum() -> None:
    evidence = Evidence(
        id="evidence-1",
        run_id="run-1",
        check_name="tests",
        command="python -m pytest",
        exit_code=0,
        status=EvidenceStatus.PASSED,
        head_sha="a" * 40,
        diff_sha256="b" * 64,
        untracked_sha256="c" * 64,
        output_path="evidence/tests.txt",
        output_sha256="d" * 64,
        started_at="2026-07-10T17:00:00Z",
        completed_at="2026-07-10T17:00:01Z",
    )
    assert Evidence.from_dict(evidence.to_dict()) == evidence


def test_workspace_snapshot_round_trip_and_validation() -> None:
    snapshot = WorkspaceSnapshot("a" * 40, "b" * 64, "c" * 64)
    assert WorkspaceSnapshot.from_dict(snapshot.to_dict()) == snapshot
    with pytest.raises(ValueError, match="diff_sha256"):
        WorkspaceSnapshot("a" * 40, "not-a-hash", "c" * 64)
