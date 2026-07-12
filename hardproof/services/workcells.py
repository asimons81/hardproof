"""Approved-plan Workcell graph creation and deterministic wave persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from hardproof.domain.enums import ApprovalGate, ArtifactKind, RunProfile, RunStage
from hardproof.domain.models import new_id
from hardproof.domain.workcells import TaskState, WorkcellTask, plan_waves, validate_graph
from hardproof.storage.repository import RunRepository


@dataclass(frozen=True, slots=True)
class WorkcellTaskSpec:
    key: str
    title: str
    objective: str
    acceptance: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    required: bool = True
    read_scope: tuple[str, ...] = ()
    write_scope: tuple[str, ...] = ()
    priority: int = 0
    model_tier: str | None = None


@dataclass(frozen=True, slots=True)
class CreatedWorkcellGraph:
    graph_revision_id: str
    revision: int
    waves: tuple[tuple[str, ...], ...]


class WorkcellService:
    def __init__(self, repository: RunRepository, *, maximum_attempts: int, default_model_tier: str) -> None:
        self.repository = repository
        self.maximum_attempts = maximum_attempts
        self.default_model_tier = default_model_tier

    def create_graph(self, run_id: str, specs: tuple[WorkcellTaskSpec, ...]) -> CreatedWorkcellGraph:
        run = self.repository.get_run(run_id)
        if run.stage is not RunStage.IMPLEMENT:
            raise PermissionError("Workcell graph creation requires IMPLEMENT stage")
        plans = [item for item in self.repository.list_artifacts(run_id) if item.kind is ArtifactKind.PLAN]
        approvals = self.repository.list_approvals(run_id)
        if run.profile in {RunProfile.STANDARD, RunProfile.CRITICAL} and not any(
            item.gate is ApprovalGate.PLAN for item in approvals
        ):
            raise PermissionError("Workcell graph creation requires human plan approval")
        if run.profile in {RunProfile.STANDARD, RunProfile.CRITICAL} and not plans:
            raise ValueError("Workcell graph creation requires a plan artifact")
        if not specs:
            raise ValueError("Workcell graph requires at least one task")
        revision = self.repository.next_workcell_graph_revision(run_id)
        tasks = tuple(
            WorkcellTask(
                new_id("workcell-task"), run_id, spec.key, spec.title, spec.objective,
                tuple(spec.acceptance), spec.required, tuple(spec.dependencies), tuple(spec.read_scope),
                tuple(spec.write_scope), revision, spec.priority, TaskState.PENDING,
            )
            for spec in specs
        )
        validated = validate_graph(tasks)
        canonical = json.dumps(
            [item.to_dict() for item in validated], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        plan = max(plans, key=lambda item: (item.created_at, item.id)) if plans else None
        graph_id = self.repository.create_workcell_graph_revision(
            run_id, revision, hashlib.sha256(canonical).hexdigest(), actor="human",
            rationale="created from approved implementation plan",
            approved_plan_artifact_id=plan.id if plan else None,
            approved_plan_sha256=plan.sha256 if plan else None,
        )
        by_key = {item.key: item for item in validated}
        specs_by_key = {item.key: item for item in specs}
        for task in validated:
            spec = specs_by_key[task.key]
            tier = spec.model_tier or self.default_model_tier
            self.repository.add_workcell_task(task, graph_id, maximum_attempts=self.maximum_attempts, model_tier=tier)
        for task in validated:
            for dependency in task.dependencies:
                self.repository.add_workcell_dependency(task.task_id, by_key[dependency].task_id)
        waves = plan_waves(validated).waves
        for wave_number, wave in enumerate(waves, 1):
            for key in wave:
                self.repository.set_workcell_wave(by_key[key].task_id, wave_number)
        return CreatedWorkcellGraph(graph_id, revision, waves)

    def refresh_readiness(self, run_id: str) -> tuple[str, ...]:
        """Re-evaluate durable dependencies before the scheduler attempts a claim."""
        return self.repository.refresh_workcell_readiness(run_id)
