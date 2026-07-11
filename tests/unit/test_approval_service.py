from pathlib import Path

import pytest

from crucible_agent.domain.enums import ApprovalGate, RunProfile
from crucible_agent.domain.models import Run
from crucible_agent.services.approvals import ApprovalService
from crucible_agent.storage.database import Database
from crucible_agent.storage.migrations import migrate
from crucible_agent.storage.repository import RunRepository


def test_human_surface_can_create_attributable_approval(tmp_path: Path) -> None:
    database = Database(tmp_path / "crucible.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "approval", RunProfile.STANDARD)
    repository.create_run(run)
    approval = ApprovalService(repository).create_human(
        run.id, ApprovalGate.DESIGN, actor="tony", source="slash", reason="reviewed"
    )
    assert approval.actor == "tony"
    assert repository.list_approvals(run.id) == (approval,)


@pytest.mark.parametrize(
    ("actor", "source"),
    [("model", "tool"), ("agent", "slash"), ("tony", "tool")],
)
def test_non_human_or_model_surface_cannot_create_approval(
    tmp_path: Path, actor: str, source: str
) -> None:
    database = Database(tmp_path / "crucible.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "approval", RunProfile.STANDARD)
    repository.create_run(run)
    with pytest.raises(PermissionError):
        ApprovalService(repository).create_human(
            run.id, ApprovalGate.PLAN, actor=actor, source=source
        )


def test_waiver_requires_reason(tmp_path: Path) -> None:
    database = Database(tmp_path / "crucible.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "waiver", RunProfile.STANDARD)
    repository.create_run(run)
    with pytest.raises(ValueError, match="reason"):
        ApprovalService(repository).create_human(
            run.id, ApprovalGate.WAIVER, actor="tony", source="cli"
        )
