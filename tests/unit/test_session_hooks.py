from __future__ import annotations

import subprocess
from pathlib import Path

from crucible_agent.commands.shared import CommandContext, CommandService
from crucible_agent.domain.enums import RunProfile, RunStage
from crucible_agent.domain.models import Run, utc_now
from crucible_agent.hooks.context import ContextHook
from crucible_agent.hooks.sessions import SessionHooks
from crucible_agent.services.sessions import SessionService
from crucible_agent.storage.repository import RunRepository


def setup(tmp_path: Path) -> tuple[RunRepository, CommandService, SessionService]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    commands = CommandService(CommandContext(tmp_path, actor="user", source="cli"))
    sessions = SessionService(commands.repository, commands.paths)
    return commands.repository, commands, sessions


def test_first_turn_falls_back_to_active_pointer_and_persists_binding(tmp_path: Path) -> None:
    repository, commands, sessions = setup(tmp_path)
    started = commands.execute(["start", "standard", "Feature"])
    hook = ContextHook(sessions, commands)
    result = hook(session_id="session-a", is_first_turn=True)
    assert result is not None
    assert "CRUCIBLE RUN ACTIVE" in result["context"]
    assert started.run_id in result["context"]
    assert repository.get_session_binding("session-a") is not None


def test_later_turn_uses_session_binding_before_different_workspace_pointer(tmp_path: Path) -> None:
    repository, commands, sessions = setup(tmp_path)
    first = commands.execute(["start", "quick", "First"])
    sessions.bind("session-a", first.run_id or "", "cli")
    second = commands.execute(["start", "standard", "Second"])
    assert second.run_id != first.run_id
    context = ContextHook(sessions, commands)(session_id="session-a")["context"]  # type: ignore[index]
    assert first.run_id in context
    assert second.run_id not in context


def test_no_active_run_has_no_injection(tmp_path: Path) -> None:
    _, commands, sessions = setup(tmp_path)
    assert ContextHook(sessions, commands)(session_id="none") is None


def test_paused_run_injects_resume_action(tmp_path: Path) -> None:
    _, commands, sessions = setup(tmp_path)
    commands.execute(["start", "quick", "Pause"])
    commands.execute(["pause", "wait"])
    context = ContextHook(sessions, commands)(session_id="session-a")["context"]  # type: ignore[index]
    assert "Required next action: Resume the paused run" in context


def test_completed_run_does_not_inject(tmp_path: Path) -> None:
    repository, commands, sessions = setup(tmp_path)
    run = Run.create(str(tmp_path), "complete", RunProfile.QUICK)
    repository.create_run(run)
    repository.transition_run(run.id, RunStage.COMPLETE, reason="test")
    sessions.bind("session-a", run.id, "cli")
    assert ContextHook(sessions, commands)(session_id="session-a") is None


def test_stale_binding_falls_back_without_crashing(tmp_path: Path) -> None:
    repository, commands, sessions = setup(tmp_path)
    with repository.database.connect() as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "INSERT INTO session_bindings(session_id, run_id, platform, updated_at) VALUES (?, ?, ?, ?)",
            ("session-a", "missing-run", "cli", utc_now()),
        )
    assert ContextHook(sessions, commands)(session_id="session-a") is None


def test_two_sessions_remain_bound_to_different_runs(tmp_path: Path) -> None:
    _, commands, sessions = setup(tmp_path)
    first = commands.execute(["start", "quick", "First"])
    sessions.bind("session-a", first.run_id or "", "cli")
    second = commands.execute(["start", "quick", "Second"])
    sessions.bind("session-b", second.run_id or "", "cli")
    hook = ContextHook(sessions, commands)
    assert first.run_id in hook(session_id="session-a")["context"]  # type: ignore[index]
    assert second.run_id in hook(session_id="session-b")["context"]  # type: ignore[index]


def test_context_is_deterministic_bounded_and_contains_no_artifact_body(tmp_path: Path) -> None:
    _, commands, sessions = setup(tmp_path)
    commands.execute(["start", "standard", "Feature"])
    hook = ContextHook(sessions, commands)
    first = hook(session_id="session-a")
    second = hook(session_id="session-a")
    assert first == second
    assert first is not None and len(first["context"]) <= 2_500
    assert "Required skill: skill_view(\"crucible:orchestrate\")" in first["context"]


def test_finalize_and_reset_clear_cache_but_preserve_database(tmp_path: Path) -> None:
    repository, commands, sessions = setup(tmp_path)
    started = commands.execute(["start", "quick", "Feature"])
    context_hook = ContextHook(sessions, commands)
    context_hook(session_id="session-a")
    hooks = SessionHooks(sessions, context_hook)
    hooks.on_session_finalize(session_id="session-a")
    assert not context_hook.cache
    assert repository.get_run(started.run_id or "")
    context_hook(session_id="session-a")
    hooks.on_session_reset(old_session_id="session-a", new_session_id="session-b")
    assert not context_hook.cache
