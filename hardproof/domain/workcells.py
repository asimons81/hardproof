"""Deterministic Workcell task graph primitives.

The graph layer is deliberately side-effect free. Persistence, claims, child
launches, and result validation belong to higher layers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from typing import Iterable


class TaskState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    STARTING = "starting"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"
    ESCALATED = "escalated"


class AttemptState(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


TERMINAL_TASK_STATES = frozenset(
    {TaskState.SUCCEEDED, TaskState.BLOCKED, TaskState.FAILED, TaskState.CANCELLED, TaskState.ESCALATED}
)
UNSUCCESSFUL_DEPENDENCY_STATES = frozenset(
    {TaskState.BLOCKED, TaskState.FAILED, TaskState.INTERRUPTED, TaskState.CANCELLED, TaskState.ESCALATED}
)
TERMINAL_ATTEMPT_STATES = frozenset(
    {AttemptState.SUCCEEDED, AttemptState.BLOCKED, AttemptState.FAILED, AttemptState.INTERRUPTED, AttemptState.CANCELLED}
)
ATTEMPT_TRANSITIONS: dict[AttemptState, frozenset[AttemptState]] = {
    AttemptState.STARTING: frozenset({AttemptState.RUNNING, AttemptState.BLOCKED, AttemptState.FAILED, AttemptState.INTERRUPTED, AttemptState.CANCELLED}),
    AttemptState.RUNNING: frozenset({AttemptState.SUCCEEDED, AttemptState.BLOCKED, AttemptState.FAILED, AttemptState.INTERRUPTED, AttemptState.CANCELLED}),
}


@dataclass(frozen=True, slots=True)
class WorkcellTask:
    task_id: str
    run_id: str
    key: str
    title: str
    objective: str
    acceptance: tuple[str, ...]
    required: bool
    dependencies: tuple[str, ...]
    read_scope: tuple[str, ...]
    write_scope: tuple[str, ...]
    graph_revision: int
    priority: int
    state: TaskState = TaskState.PENDING

    def __post_init__(self) -> None:
        for name in ("task_id", "run_id", "key", "title", "objective"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if not self.key.replace("-", "").replace("_", "").isalnum():
            raise ValueError("task key must be filename-safe")
        if self.graph_revision < 1:
            raise ValueError("graph_revision must be positive")
        object.__setattr__(self, "state", TaskState(self.state))
        for name in ("acceptance", "dependencies", "read_scope", "write_scope"):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["state"] = self.state.value
        return result


@dataclass(frozen=True, slots=True)
class WorkcellAttempt:
    attempt_id: str
    run_id: str
    task_id: str
    attempt_number: int
    launch_token: str
    model_tier: str
    context_sha256: str
    state: AttemptState = AttemptState.STARTING
    child_session_id: str | None = None
    terminal_reason: str | None = None

    def __post_init__(self) -> None:
        for name in ("attempt_id", "run_id", "task_id", "launch_token", "model_tier"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive")
        if len(self.context_sha256) != 64 or any(char not in "0123456789abcdef" for char in self.context_sha256.lower()):
            raise ValueError("context_sha256 must be a SHA-256 digest")
        object.__setattr__(self, "state", AttemptState(self.state))
        if self.state in TERMINAL_ATTEMPT_STATES and not (self.terminal_reason or "").strip():
            raise ValueError("terminal attempt requires terminal_reason")
        if self.state not in TERMINAL_ATTEMPT_STATES and self.terminal_reason is not None:
            raise ValueError("non-terminal attempt cannot have terminal_reason")

    @classmethod
    def create(
        cls,
        attempt_id: str,
        run_id: str,
        task_id: str,
        attempt_number: int,
        launch_token: str,
        model_tier: str,
        context_sha256: str,
    ) -> "WorkcellAttempt":
        return cls(attempt_id, run_id, task_id, attempt_number, launch_token, model_tier, context_sha256)


def transition_attempt(
    attempt: WorkcellAttempt,
    target: AttemptState,
    *,
    actor: str,
    reason: str | None = None,
) -> WorkcellAttempt:
    """Validate an authoritative attempt transition without side effects."""
    if not actor.strip():
        raise ValueError("attempt transition requires actor")
    target = AttemptState(target)
    if attempt.state in TERMINAL_ATTEMPT_STATES:
        raise ValueError("terminal attempt is immutable")
    if target not in ATTEMPT_TRANSITIONS.get(attempt.state, frozenset()):
        raise ValueError(f"invalid attempt transition: {attempt.state} -> {target}")
    if target in TERMINAL_ATTEMPT_STATES and not (reason or "").strip():
        reason = f"transitioned by {actor}"
    return replace(attempt, state=target, terminal_reason=reason if target in TERMINAL_ATTEMPT_STATES else None)


@dataclass(frozen=True, slots=True)
class WavePlan:
    waves: tuple[tuple[str, ...], ...]
    blocked: dict[str, str]


def validate_graph(tasks: Iterable[WorkcellTask]) -> tuple[WorkcellTask, ...]:
    """Validate stable keys and dependency edges, returning deterministic tasks."""
    ordered = tuple(sorted(tasks, key=lambda item: item.key))
    by_key = {task.key: task for task in ordered}
    if len(by_key) != len(ordered):
        raise ValueError("duplicate task key")
    for task in ordered:
        if len(set(task.dependencies)) != len(task.dependencies):
            raise ValueError(f"duplicate dependency for task: {task.key}")
        if task.key in task.dependencies:
            raise ValueError(f"self dependency for task: {task.key}")
        unknown = sorted(set(task.dependencies) - set(by_key))
        if unknown:
            raise ValueError(f"unknown dependency for task {task.key}: {', '.join(unknown)}")

    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(key: str) -> None:
        if key in visiting:
            raise ValueError("task dependency cycle detected")
        if key in visited:
            return
        visiting.add(key)
        for dependency in by_key[key].dependencies:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in by_key:
        visit(key)
    return ordered


def plan_waves(tasks: Iterable[WorkcellTask]) -> WavePlan:
    """Return deterministic dependency-safe waves and durable blocking reasons."""
    ordered = validate_graph(tasks)
    by_key = {task.key: task for task in ordered}
    blocked: dict[str, str] = {}
    candidates: set[str] = set()
    for task in ordered:
        failed = next(
            (dependency for dependency in task.dependencies if by_key[dependency].state in UNSUCCESSFUL_DEPENDENCY_STATES),
            None,
        )
        if failed is not None:
            blocked[task.key] = f"required dependency failed: {failed}"
        elif task.state not in TERMINAL_TASK_STATES and task.state not in {TaskState.STARTING, TaskState.RUNNING}:
            candidates.add(task.key)

    completed = {task.key for task in ordered if task.state is TaskState.SUCCEEDED}
    waves: list[tuple[str, ...]] = []
    while candidates:
        ready = [key for key in candidates if all(dep in completed for dep in by_key[key].dependencies)]
        if not ready:
            break
        ready.sort(key=lambda key: (by_key[key].priority, key))
        wave = tuple(ready)
        waves.append(wave)
        candidates.difference_update(wave)
        completed.update(wave)
    for key in sorted(candidates):
        blocked.setdefault(key, "required dependency unresolved")
    return WavePlan(tuple(waves), blocked)
