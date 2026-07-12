from __future__ import annotations

import pytest

from hardproof.domain.workcells import (
    AttemptState,
    TaskState,
    WorkcellAttempt,
    WorkcellTask,
    plan_waves,
    transition_attempt,
    validate_graph,
)


def task(key: str, dependencies: tuple[str, ...] = (), *, priority: int = 0) -> WorkcellTask:
    return WorkcellTask(
        task_id=f"task-{key}", run_id="run-1", key=key, title=key,
        objective=f"complete {key}", acceptance=("tests pass",), required=True,
        dependencies=dependencies, read_scope=(), write_scope=(f"{key}.py",),
        graph_revision=1, priority=priority, state=TaskState.PENDING,
    )


def test_validate_graph_rejects_cycles_unknown_and_duplicate_dependencies() -> None:
    with pytest.raises(ValueError, match="cycle"):
        validate_graph((task("a", ("b",)), task("b", ("a",))))
    with pytest.raises(ValueError, match="unknown"):
        validate_graph((task("a", ("missing",)),))
    with pytest.raises(ValueError, match="duplicate"):
        validate_graph((task("a", ("b", "b")), task("b")))


def test_plan_waves_is_dependency_safe_and_deterministic() -> None:
    tasks = (task("compile", priority=2), task("lint", priority=1), task("verify", ("compile", "lint")))
    assert plan_waves(tasks).waves == (("lint", "compile"), ("verify",))


def test_failed_required_dependency_blocks_dependent_task() -> None:
    done = task("done")
    failed = task("failed")
    failed = WorkcellTask(**{**failed.to_dict(), "state": TaskState.FAILED})
    dependent = task("dependent", ("done", "failed"))
    plan = plan_waves((done, failed, dependent))
    assert plan.waves == (("done",),)
    assert plan.blocked == {"dependent": "required dependency failed: failed"}


def test_attempt_transitions_are_finite_and_terminal_attempts_are_immutable() -> None:
    attempt = WorkcellAttempt.create("attempt-1", "run-1", "task-a", 1, "token-1", "standard", "a" * 64)
    running = transition_attempt(attempt, AttemptState.RUNNING, actor="scheduler")
    succeeded = transition_attempt(running, AttemptState.SUCCEEDED, actor="parent")
    assert succeeded.state is AttemptState.SUCCEEDED
    with pytest.raises(ValueError, match="terminal"):
        transition_attempt(succeeded, AttemptState.RUNNING, actor="scheduler")
    with pytest.raises(ValueError, match="invalid attempt transition"):
        transition_attempt(attempt, AttemptState.SUCCEEDED, actor="parent")
