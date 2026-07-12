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


def test_workcell_task_rejects_invalid_key_and_negative_revision() -> None:
    with pytest.raises(ValueError, match="task key must be filename-safe"):
        WorkcellTask("id", "run", "../unsafe", "title", "obj", ("acc",), True, (), (), (), 1, 0)
    with pytest.raises(ValueError, match="graph_revision must be positive"):
        WorkcellTask("id", "run", "safe-key", "title", "obj", ("acc",), True, (), (), (), 0, 0)


def test_workcell_attempt_rejects_invalid_sha256_and_nonsense_transitions() -> None:
    with pytest.raises(ValueError, match="context_sha256 must be a SHA-256 digest"):
        WorkcellAttempt.create("a", "run", "task", 1, "token", "standard", "not-a-sha256")
    with pytest.raises(ValueError, match="attempt_number must be positive"):
        WorkcellAttempt.create("a", "run", "task", 0, "token", "standard", "a" * 64)
    with pytest.raises(ValueError, match="must be non-empty"):
        WorkcellAttempt.create("", "run", "task", 1, "token", "standard", "a" * 64)
    terminal = transition_attempt(
        WorkcellAttempt.create("a", "run", "task", 1, "token", "standard", "a" * 64),
        AttemptState.FAILED, actor="parent", reason="stopped",
    )
    with pytest.raises(ValueError, match="terminal"):
        transition_attempt(terminal, AttemptState.RUNNING, actor="scheduler")


def test_transition_attempt_requires_actor_and_reason_for_terminal() -> None:
    attempt = WorkcellAttempt.create("a", "run", "task", 1, "token", "standard", "a" * 64)
    with pytest.raises(ValueError, match="actor"):
        transition_attempt(attempt, AttemptState.RUNNING, actor="")
    running = transition_attempt(attempt, AttemptState.RUNNING, actor="scheduler")
    result = transition_attempt(running, AttemptState.SUCCEEDED, actor="parent")
    assert result.terminal_reason == "transitioned by parent"


def test_validate_graph_rejects_self_dependency() -> None:
    with pytest.raises(ValueError, match="self dependency"):
        validate_graph((task("a", ("a",)),))


def test_plan_waves_yields_empty_waves_when_all_terminal() -> None:
    done = WorkcellTask(**{**task("done").to_dict(), "state": TaskState.SUCCEEDED})
    plan = plan_waves((done,))
    assert plan.waves == ()


def test_plan_waves_omits_running_from_candidates() -> None:
    """Running tasks are already claimed -- they don't appear in waves or blocked."""
    a = task("a")
    b = WorkcellTask(**{**task("b", ("a",)).to_dict(), "state": TaskState.RUNNING})
    plan = plan_waves((a, b))
    assert "b" not in plan.blocked
    assert "b" not in [task for wave in plan.waves for task in wave]


def test_failed_dependency_blocks_all_dependents_consistently() -> None:
    failed = WorkcellTask(**{**task("base").to_dict(), "state": TaskState.FAILED})
    child = WorkcellTask(**{**task("child", ("base",)).to_dict(), "state": TaskState.PENDING})
    mid = WorkcellTask(**{**task("mid", ("base",)).to_dict(), "state": TaskState.PENDING})
    plan = plan_waves((failed, child, mid))
    assert plan.waves == ()
    assert plan.blocked["child"] == "required dependency failed: base"
    assert plan.blocked["mid"] == "required dependency failed: base"


def test_workcell_task_rejects_empty_fields() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        WorkcellTask("", "run", "key", "title", "obj", ("acc",), True, (), (), (), 1, 0)


def test_plan_waves_interrupted_base_blocks_dependents() -> None:
    interrupted = WorkcellTask(**{**task("base").to_dict(), "state": TaskState.INTERRUPTED})
    dep = WorkcellTask(**{**task("dep", ("base",)).to_dict(), "state": TaskState.PENDING})
    plan = plan_waves((interrupted, dep))
    assert "dep" in plan.blocked


def test_escaped_task_with_satisfied_deps_can_succeed() -> None:
    """Escalated tasks are terminal; dependents on escalated base should block."""
    escalated = WorkcellTask(**{**task("base").to_dict(), "state": TaskState.ESCALATED})
    child = WorkcellTask(**{**task("child", ("base",)).to_dict(), "state": TaskState.PENDING})
    plan = plan_waves((escalated, child))
    assert "child" in plan.blocked


def test_workcell_attempt_requires_terminal_reason() -> None:
    """__post_init__ rejects terminal state without reason, and non-terminal with reason."""
    with pytest.raises(ValueError, match="terminal attempt requires terminal_reason"):
        WorkcellAttempt("a", "run", "task", 1, "tok", "standard", "a" * 64, state=AttemptState.FAILED)
    with pytest.raises(ValueError, match="non-terminal attempt cannot have terminal_reason"):
        WorkcellAttempt("a", "run", "task", 1, "tok", "standard", "a" * 64, state=AttemptState.STARTING, terminal_reason="should not have this")


def test_validate_graph_rejects_duplicate_task_keys() -> None:
    with pytest.raises(ValueError, match="duplicate task key"):
        validate_graph((task("dup"), task("dup")))


def test_plan_waves_breaks_when_no_roots_in_candidates() -> None:
    """When remaining candidates all depend on non-candidate (e.g. STARTING) tasks,
    the wave loop breaks and remaining tasks get blocked as unresolved."""
    starting = WorkcellTask(**{**task("starter").to_dict(), "state": TaskState.STARTING})
    dep = WorkcellTask(**{**task("dependent", ("starter",)).to_dict(), "state": TaskState.PENDING})
    plan = plan_waves((starting, dep))
    assert plan.waves == ()
    # dependent can't be scheduled because its dep is STARTING (not completed, not in candidates)
    assert "dependent" in plan.blocked
    assert plan.blocked["dependent"] == "required dependency unresolved"
