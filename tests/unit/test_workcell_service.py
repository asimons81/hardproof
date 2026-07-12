from __future__ import annotations

from pathlib import Path

import pytest

from hardproof.domain.enums import ApprovalGate, ArtifactKind, RunProfile, RunStage
from hardproof.domain.models import Approval, Artifact, Run
from hardproof.services.workcells import WorkcellService, WorkcellTaskSpec
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def repository_at(path: Path) -> RunRepository:
    database = Database(path)
    migrate(database)
    return RunRepository(database)


def test_standard_workcell_graph_requires_plan_approval_and_persists_waves(tmp_path: Path) -> None:
    repository = repository_at(tmp_path / "state.db")
    run = Run.create(str(tmp_path), "Workcells", RunProfile.STANDARD)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.IMPLEMENT, reason="test")
    repository.add_artifact(Artifact("plan-1", run.id, ArtifactKind.PLAN, "plan.md", "a" * 64, run.created_at))
    service = WorkcellService(repository, maximum_attempts=3, default_model_tier="standard")
    with pytest.raises(PermissionError, match="plan approval"):
        service.create_graph(run.id, (WorkcellTaskSpec("build", "Build", "Build", ("tests pass",)),))
    repository.add_approval(Approval("approval-1", run.id, ApprovalGate.PLAN, "human", "cli", "approved", run.created_at))
    result = service.create_graph(
        run.id,
        (
            WorkcellTaskSpec("build", "Build", "Build", ("tests pass",), priority=2),
            WorkcellTaskSpec("lint", "Lint", "Lint", ("lint passes",), priority=1),
            WorkcellTaskSpec("verify", "Verify", "Verify", ("all pass",), dependencies=("build", "lint")),
        ),
    )
    assert result.waves == (("lint", "build"), ("verify",))
    rows = repository.list_workcell_task_rows(run.id)
    assert [(item["task_key"], item["wave_number"]) for item in rows] == [("lint", 1), ("build", 1), ("verify", 2)]
