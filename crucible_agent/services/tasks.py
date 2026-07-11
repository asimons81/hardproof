"""Dependency-safe implementation task ledger."""

from __future__ import annotations

from dataclasses import replace

from crucible_agent.domain.enums import RiskLevel, TaskStatus
from crucible_agent.domain.models import Task, new_id, utc_now
from crucible_agent.storage.repository import RunRepository


class TaskService:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    @staticmethod
    def _validate_dependencies(tasks: tuple[Task, ...], key: str, dependencies: tuple[str, ...]) -> None:
        graph = {task.task_key: set(task.dependencies) for task in tasks}
        known = set(graph)
        missing = sorted(set(dependencies) - known)
        if missing:
            raise ValueError(f"missing task dependencies: {', '.join(missing)}")
        graph[key] = set(dependencies)

        def visit(node: str, visiting: set[str], visited: set[str]) -> None:
            if node in visiting:
                raise ValueError("task dependency cycle detected")
            if node in visited:
                return
            visiting.add(node)
            for dependency in graph.get(node, set()):
                visit(dependency, visiting, visited)
            visiting.remove(node)
            visited.add(node)

        visited: set[str] = set()
        for node in graph:
            visit(node, set(), visited)

    def create(
        self,
        run_id: str,
        key: str,
        title: str,
        description: str,
        risk: RiskLevel,
        *,
        dependencies: tuple[str, ...] = (),
        acceptance: tuple[str, ...] = (),
        files: tuple[str, ...] = (),
    ) -> Task:
        tasks = self.repository.list_tasks(run_id)
        if any(task.task_key == key for task in tasks):
            raise ValueError(f"task key already exists: {key}")
        self._validate_dependencies(tasks, key, dependencies)
        timestamp = utc_now()
        task = Task(
            new_id("task"), run_id, key, title, description, TaskStatus.PENDING,
            risk, dependencies, acceptance, files, timestamp, timestamp,
        )
        self.repository.add_task(task)
        self.repository.append_event(run_id, "task_created", {"task_id": task.id, "task_key": key})
        return task

    def update(
        self,
        run_id: str,
        key: str,
        *,
        status: TaskStatus | None = None,
        dependencies: tuple[str, ...] | None = None,
        acceptance_notes: str | None = None,
    ) -> Task:
        tasks = self.repository.list_tasks(run_id)
        current = next((task for task in tasks if task.task_key == key), None)
        if current is None:
            raise LookupError(f"task not found: {key}")
        next_dependencies = dependencies if dependencies is not None else current.dependencies
        self._validate_dependencies(tasks, key, next_dependencies)
        next_status = status if status is not None else current.status
        notes = acceptance_notes if acceptance_notes is not None else current.acceptance_notes
        if next_status is TaskStatus.COMPLETED and not (notes or "").strip():
            raise ValueError("task completion requires acceptance notes")
        updated = replace(
            current, status=next_status, dependencies=next_dependencies,
            acceptance_notes=notes, updated_at=utc_now(),
        )
        self.repository.update_task(updated)
        self.repository.append_event(
            run_id, "task_updated", {"status": updated.status.value, "task_key": key}
        )
        return updated
