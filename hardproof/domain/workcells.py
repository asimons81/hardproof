"""Deterministic Workcell task graph primitives.

The graph layer is deliberately side-effect free. Persistence, claims, child
launches, and result validation belong to higher layers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
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


TERMINAL_TASK_STATES = frozenset(
    {TaskState.SUCCEEDED, TaskState.BLOCKED, TaskState.FAILED, TaskState.CANCELLED, TaskState.ESCALATED}
)
UNSUCCESSFUL_DEPENDENCY_STATES = frozenset(
    {TaskState.BLOCKED, TaskState.FAILED, TaskState.INTERRUPTED, TaskState.CANCELLED, TaskState.ESCALATED}
)


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
