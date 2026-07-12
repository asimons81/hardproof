"""Approved-plan Workcell graph creation and deterministic wave persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from hardproof.domain.enums import ApprovalGate, ArtifactKind, RunProfile, RunStage
from hardproof.domain.models import new_id
from hardproof.domain.workcells import TaskState, WorkcellTask, plan_waves, validate_graph
from hardproof.services.hermes_children import ChildLaunch, ChildSessionAdapter
from hardproof.services.workcell_artifacts import WorkcellArtifactStore, validate_child_result
from hardproof.paths import safe_project_relative
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
    def __init__(
        self, repository: RunRepository, *, maximum_attempts: int, default_model_tier: str,
        brief_size_limit: int = 65_536, context_manifest_size_limit: int = 32_768,
        result_size_limit: int = 65_536, claim_timeout_seconds: int = 900,
        maximum_active_children: int = 1,
    ) -> None:
        self.repository = repository
        self.maximum_attempts = maximum_attempts
        self.default_model_tier = default_model_tier
        self.brief_size_limit = brief_size_limit
        self.context_manifest_size_limit = context_manifest_size_limit
        self.result_size_limit = result_size_limit
        self.claim_timeout_seconds = claim_timeout_seconds
        self.maximum_active_children = maximum_active_children

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

    def launch_next(
        self, run_id: str, *, project_root: str | Path, adapter: ChildSessionAdapter, claimant: str = "scheduler"
    ) -> ChildLaunch | None:
        """Claim, materialize, and launch one deterministic ready Workcell task.

        The attempt is claimed BEFORE the child context is finalized so the child
        receives its complete identity contract (including attempt_id) and can
        produce a valid result.json without post-launch repository introspection.
        """
        self.refresh_readiness(run_id)
        ready = [item for item in self.repository.list_workcell_task_rows(run_id) if item["status"] == "ready"]
        if not ready:
            return None
        selected = ready[0]
        # Scope check: run must be in IMPLEMENT and not paused/aborted
        run = self.repository.get_run(run_id)
        if run.stage is not RunStage.IMPLEMENT or run.status.value in ("paused", "aborted"):
            raise PermissionError("Workcell launch requires active IMPLEMENT stage")
        detail = self.repository.get_workcell_task_detail(str(selected["id"]))
        root = Path(project_root).resolve()

        # Pre-generate the attempt identity so the child receives it in its contract
        attempt_id = new_id("workcell-attempt")
        attempt_number = int(cast(int, detail["attempt_count"])) + 1
        store = WorkcellArtifactStore(
            root, run_id, str(detail["task_key"]), attempt_number,
            maximum_bytes=max(self.brief_size_limit, self.context_manifest_size_limit, self.result_size_limit),
        )
        relative_base = store.attempt_directory.relative_to(root).as_posix()

        brief = "\n".join((
            f"# Workcell task: {detail['task_key']}", "", f"## Objective\n{detail['objective']}",
            "", "## Acceptance criteria", *(f"- {item}" for item in cast(tuple[str, ...], detail["acceptance"])),
            "", "## Allowed read scope", *(f"- {item}" for item in cast(tuple[str, ...], detail["read_scope"]) or ("- none declared",)),
            "", "## Allowed write scope", *(f"- {item}" for item in cast(tuple[str, ...], detail["write_scope"]) or ("- none declared",)),
            "", "## Constraints\nDo not create approvals or waivers. Return only the versioned result contract.", "",
        ))

        # The child contract includes every identity the child must echo in result.json
        result_path = f"{relative_base}/result.json"
        context = {
            "version": 1,
            "run_id": run_id,
            "task_id": str(detail["id"]),
            "task_key": str(detail["task_key"]),
            "attempt_id": attempt_id,
            "attempt_number": attempt_number,
            "graph_revision_id": str(detail["graph_revision_id"]),
            "model_tier": str(detail["model_tier"]),
            "brief_path": "brief.md",
            "result_path": "result.json",
        }
        serialized_context = json.dumps(context, sort_keys=True, separators=(",", ":"))
        context_sha256 = hashlib.sha256(serialized_context.encode("utf-8")).hexdigest()

        # Enforce configured active-child bounds before attempting to claim
        active_count = len(self.repository.list_active_workcell_attempts(run_id))
        if active_count >= self.maximum_active_children:
            return None

        # Claim the attempt with pre-generated identity so the SHA-256 matches
        attempt = self.repository.claim_workcell_task(
            str(detail["id"]), claimant=claimant, model_tier=str(detail["model_tier"]),
            context_sha256=context_sha256, brief_path=f"{relative_base}/brief.md",
            context_manifest_path=f"{relative_base}/context.json",
            result_path=result_path,
            attempt_id=attempt_id, attempt_number=attempt_number,
            claim_timeout_seconds=self.claim_timeout_seconds,
        )
        try:
            if len(brief.encode("utf-8")) > self.brief_size_limit:
                raise ValueError("Workcell brief exceeds configured size limit")
            if len(serialized_context.encode("utf-8")) > self.context_manifest_size_limit:
                raise ValueError("Workcell context manifest exceeds configured size limit")
            store.write_text("brief.md", brief)
            store.write_json("context.json", context)
            launch = adapter.launch(brief, serialized_context, attempt.model_tier)
            self.repository.mark_workcell_attempt_running(
                attempt.attempt_id, child_session_id=launch.child_session_id, child_handle=launch.raw,
            )
            # Verify the child received the correct attempt_id by writing result.json
            result = store.attempt_directory / "result.json"
            if result.exists():
                raise RuntimeError("Workcell result path was pre-populated before child action")
        except Exception as exc:
            self.repository.close_workcell_attempt(
                attempt.attempt_id, outcome="failed", actor=claimant, reason=f"launch failed: {type(exc).__name__}",
            )
            raise
        return launch

    def process_result(self, attempt_id: str, *, project_root: str | Path, actor: str = "parent") -> str:
        """Validate a durable child result and apply the only authoritative outcome."""
        detail = self.repository.get_workcell_attempt_detail(attempt_id)
        child_session_id = detail["child_session_id"]
        if not isinstance(child_session_id, str) or not child_session_id:
            raise ValueError("Workcell attempt has no reported child session identity")
        # Scope check: verify the attempt belongs to a run in IMPLEMENT stage
        run = self.repository.get_run(str(detail["run_id"]))
        if run.stage is not RunStage.IMPLEMENT:
            raise PermissionError("Workcell result processing requires run in IMPLEMENT stage")
        root = Path(project_root).resolve()
        result_path = root / safe_project_relative(str(detail["result_path"]))
        if not result_path.is_file() or result_path.is_symlink():
            raise ValueError("Workcell result file is missing or unsafe")
        raw = result_path.read_bytes()
        if len(raw) > self.result_size_limit:
            raise ValueError("Workcell result exceeds configured size limit")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Workcell result is not valid UTF-8 JSON") from exc
        result = validate_child_result(
            payload, run_id=str(detail["run_id"]), task_id=str(detail["task_id"]), attempt_id=attempt_id,
            child_session_id=child_session_id, project_root=root, maximum_bytes=self.result_size_limit,
        )
        for value in (*result.changed_paths, *result.artifacts_produced):
            if not (root / safe_project_relative(value)).exists():
                raise ValueError("Workcell result claims a missing path")
        # Enforce write scope: every changed path and artifact must match declared write scope
        write_scope = cast(tuple[str, ...], detail.get("write_scope") or ())
        if write_scope:
            import fnmatch
            for path in (*result.changed_paths, *result.artifacts_produced):
                if not any(fnmatch.fnmatch(path.replace("\\", "/"), pattern) for pattern in write_scope):
                    raise ValueError(
                        f"Workcell result path '{path}' is outside declared write scope {sorted(write_scope)}"
                    )
        if result.reported_status == "succeeded":
            expected = set(cast(tuple[str, ...], detail["acceptance"]))
            if not expected.issubset(set(result.acceptance_completed)):
                raise ValueError("Workcell result does not satisfy task acceptance criteria")
        self.repository.record_workcell_result_received(attempt_id, actor=actor, summary=result.summary)
        self.repository.close_workcell_attempt(
            attempt_id, outcome=result.reported_status, actor=actor, reason=result.summary,
        )
        return result.reported_status
