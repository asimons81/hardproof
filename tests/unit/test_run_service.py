from pathlib import Path

from crucible_agent.domain.enums import RunProfile, RunStage
from crucible_agent.domain.models import Run
from crucible_agent.policy.stage_rules import TransitionFacts
from crucible_agent.services.runs import RunService
from crucible_agent.storage.database import Database
from crucible_agent.storage.migrations import migrate
from crucible_agent.storage.repository import RunRepository


def test_quick_skip_reason_is_durably_recorded(tmp_path: Path) -> None:
    database = Database(tmp_path / "crucible.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "localized fix", RunProfile.QUICK)
    repository.create_run(run)
    service = RunService(repository)
    updated = service.transition(
        run.id, RunStage.IMPLEMENT, TransitionFacts(), reason="start implementation",
        skip_reason="low-risk localized change",
    )
    assert updated.stage is RunStage.IMPLEMENT
    events = repository.list_events(run.id)
    assert any(event.event_type == "stages_skipped" for event in events)


def test_denied_transition_does_not_mutate_run(tmp_path: Path) -> None:
    database = Database(tmp_path / "crucible.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "standard change", RunProfile.STANDARD)
    repository.create_run(run)
    result = RunService(repository).try_transition(
        run.id, RunStage.IMPLEMENT, TransitionFacts(), reason="too early"
    )
    assert not result.allowed
    assert repository.get_run(run.id).stage is RunStage.INTAKE


def test_pause_and_resume_restore_durable_prior_stage(tmp_path: Path) -> None:
    database = Database(tmp_path / "crucible.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "pauseable change", RunProfile.STANDARD)
    repository.create_run(run)
    service = RunService(repository)
    assert service.pause(run.id, reason="waiting for input").stage is RunStage.PAUSED
    assert service.resume(run.id, reason="input received").stage is RunStage.INTAKE
