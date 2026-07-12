"""Typed repository operations over short-lived SQLite connections."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

from hardproof.domain.models import (
    Approval,
    Artifact,
    Decision,
    Evidence,
    Event,
    PolicyDecisionRecord,
    RiskSuggestion,
    Run,
    SessionBinding,
    Task,
    VerificationCheck,
    Waiver,
    WaiverEvent,
    new_id,
    utc_now,
)
from hardproof.domain.enums import RiskLevel, RunStage, RunStatus
from hardproof.domain.workcells import AttemptState, TaskState, WorkcellAttempt, WorkcellTask
from hardproof.storage.database import Database


class RunNotFoundError(LookupError):
    """No run exists with the requested public run ID."""


class RunRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_run(self, run: Run) -> None:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """INSERT INTO runs(
                        id, project_root, request, profile, stage, status,
                        created_at, updated_at, completed_at, aborted_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run.id, run.project_root, run.request, run.profile.value,
                        run.stage.value, run.status.value, run.created_at, run.updated_at,
                        run.completed_at, run.aborted_reason,
                    ),
                )
                self._append_event(
                    connection, run.id, "run_created",
                    {"profile": run.profile.value, "stage": run.stage.value}, run.created_at,
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def get_run(self, run_id: str) -> Run:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise RunNotFoundError(run_id)
        return Run.from_dict(dict(row))

    def list_runs(self) -> tuple[Run, ...]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM runs ORDER BY created_at, id").fetchall()
        return tuple(Run.from_dict(dict(row)) for row in rows)

    @staticmethod
    def _append_event(
        connection: Any,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
        created_at: str,
    ) -> int:
        cursor = connection.execute(
            "INSERT INTO events(run_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (run_id, event_type, json.dumps(payload, sort_keys=True, separators=(",", ":")), created_at),
        )
        return int(cursor.lastrowid)

    def append_event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> int:
        timestamp = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                sequence = self._append_event(connection, run_id, event_type, payload, timestamp)
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
                return sequence

    def list_events(self, run_id: str) -> tuple[Event, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY sequence", (run_id,)
            ).fetchall()
        return tuple(
            Event(
                sequence=int(row["sequence"]), run_id=str(row["run_id"]),
                event_type=str(row["event_type"]), payload=json.loads(row["payload_json"]),
                created_at=str(row["created_at"]),
            )
            for row in rows
        )

    def transition_run(
        self,
        run_id: str,
        target_stage: RunStage,
        *,
        reason: str,
        audit_events: tuple[tuple[str, dict[str, object]], ...] = (),
    ) -> Run:
        current = self.get_run(run_id)
        timestamp = utc_now()
        status = current.status
        completed_at = current.completed_at
        if target_stage is RunStage.COMPLETE:
            status = RunStatus.COMPLETE
            completed_at = timestamp
        elif target_stage is RunStage.ABORTED:
            status = RunStatus.ABORTED
        elif target_stage is RunStage.PAUSED:
            status = RunStatus.PAUSED
        elif status is RunStatus.PAUSED:
            status = RunStatus.ACTIVE
        updated = replace(
            current, stage=target_stage, status=status,
            updated_at=timestamp, completed_at=completed_at,
            aborted_reason=reason if target_stage is RunStage.ABORTED else current.aborted_reason,
        )
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.execute(
                    """UPDATE runs SET stage=?, status=?, updated_at=?, completed_at=?, aborted_reason=?
                    WHERE id=? AND stage=? AND updated_at=?""",
                    (
                        updated.stage.value, updated.status.value, updated.updated_at,
                        updated.completed_at, updated.aborted_reason, run_id,
                        current.stage.value, current.updated_at,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("run changed concurrently; reload before transitioning")
                for event_type, payload in audit_events:
                    self._append_event(connection, run_id, event_type, payload, timestamp)
                self._append_event(
                    connection, run_id, "stage_transitioned",
                    {"from_stage": current.stage.value, "reason": reason, "to_stage": target_stage.value},
                    timestamp,
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return updated

    def save_session_binding(self, binding: SessionBinding) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO session_bindings(session_id, run_id, platform, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    run_id=excluded.run_id, platform=excluded.platform, updated_at=excluded.updated_at""",
                (binding.session_id, binding.run_id, binding.platform, binding.updated_at),
            )

    def get_session_binding(self, session_id: str) -> SessionBinding | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM session_bindings WHERE session_id=?", (session_id,)
            ).fetchone()
        return SessionBinding.from_dict(dict(row)) if row is not None else None

    def add_artifact(self, artifact: Artifact) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO artifacts(id, run_id, kind, path, sha256, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    artifact.id, artifact.run_id, artifact.kind.value, artifact.path,
                    artifact.sha256, artifact.created_at,
                ),
            )

    def list_artifacts(self, run_id: str) -> tuple[Artifact, ...]:
        return self._list_models(
            "SELECT * FROM artifacts WHERE run_id=? ORDER BY created_at, id", run_id, Artifact
        )

    def add_approval(self, approval: Approval) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO approvals(id, run_id, gate, actor, source, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    approval.id, approval.run_id, approval.gate.value, approval.actor,
                    approval.source, approval.reason, approval.created_at,
                ),
            )

    def list_approvals(self, run_id: str) -> tuple[Approval, ...]:
        return self._list_models(
            "SELECT * FROM approvals WHERE run_id=? ORDER BY created_at, id", run_id, Approval
        )

    def upsert_decision(self, decision: Decision) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO decisions(id, run_id, key, question, choice, rationale, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id, key) DO UPDATE SET
                    id=excluded.id, question=excluded.question, choice=excluded.choice,
                    rationale=excluded.rationale, status=excluded.status, created_at=excluded.created_at""",
                (
                    decision.id, decision.run_id, decision.key, decision.question,
                    decision.choice, decision.rationale, decision.status, decision.created_at,
                ),
            )

    def list_decisions(self, run_id: str) -> tuple[Decision, ...]:
        return self._list_models(
            "SELECT * FROM decisions WHERE run_id=? ORDER BY key", run_id, Decision
        )

    def add_task(self, task: Task) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO tasks(
                    id, run_id, task_key, title, description, status, risk,
                    dependencies_json, acceptance_json, files_json, acceptance_notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.id, task.run_id, task.task_key, task.title, task.description,
                    task.status.value, task.risk.value, json.dumps(task.dependencies),
                    json.dumps(task.acceptance), json.dumps(task.files), task.acceptance_notes,
                    task.created_at, task.updated_at,
                ),
            )

    def list_tasks(self, run_id: str) -> tuple[Task, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM tasks WHERE run_id=? ORDER BY task_key", (run_id,)
            ).fetchall()
        tasks: list[Task] = []
        for row in rows:
            payload = dict(row)
            payload["dependencies"] = json.loads(payload.pop("dependencies_json"))
            payload["acceptance"] = json.loads(payload.pop("acceptance_json"))
            payload["files"] = json.loads(payload.pop("files_json"))
            tasks.append(Task.from_dict(payload))
        return tuple(tasks)

    def update_task(self, task: Task) -> None:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE tasks SET status=?, risk=?, dependencies_json=?, acceptance_json=?,
                    files_json=?, acceptance_notes=?, updated_at=? WHERE id=? AND run_id=?""",
                (
                    task.status.value, task.risk.value, json.dumps(task.dependencies),
                    json.dumps(task.acceptance), json.dumps(task.files), task.acceptance_notes,
                    task.updated_at, task.id, task.run_id,
                ),
            )
        if cursor.rowcount != 1:
            raise LookupError(f"task not found: {task.task_key}")

    def create_workcell_graph_revision(
        self, run_id: str, revision: int, graph_sha256: str, *, actor: str, rationale: str,
        approved_plan_artifact_id: str | None = None, approved_plan_sha256: str | None = None,
    ) -> str:
        if revision < 1 or len(graph_sha256) != 64 or not actor.strip() or not rationale.strip():
            raise ValueError("invalid Workcell graph revision")
        graph_id = new_id("workcell-graph")
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO workcell_graph_revisions(
                    id, run_id, revision, approved_plan_artifact_id, approved_plan_sha256,
                    graph_sha256, created_at, created_by, rationale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    graph_id, run_id, revision, approved_plan_artifact_id, approved_plan_sha256,
                    graph_sha256, utc_now(), actor, rationale,
                ),
            )
        return graph_id

    def next_workcell_graph_revision(self, run_id: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(revision), 0) FROM workcell_graph_revisions WHERE run_id=?", (run_id,)
            ).fetchone()
        return int(row[0]) + 1

    def add_workcell_task(
        self, task: WorkcellTask, graph_revision_id: str, *, maximum_attempts: int, model_tier: str
    ) -> None:
        if not 1 <= maximum_attempts <= 10 or not model_tier.strip():
            raise ValueError("invalid Workcell task attempt bound or model tier")
        timestamp = utc_now()
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO workcell_tasks(
                    id, run_id, graph_revision_id, task_key, title, objective, acceptance_json,
                    required, read_scope_json, write_scope_json, brief_path, context_manifest_path,
                    result_path, wave_number, priority, model_tier, maximum_attempts, attempt_count,
                    status, blocking_reason, escalation_state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?, ?, 0, ?, NULL, NULL, ?, ?)""",
                (
                    task.task_id, task.run_id, graph_revision_id, task.key, task.title, task.objective,
                    json.dumps(task.acceptance), int(task.required), json.dumps(task.read_scope),
                    json.dumps(task.write_scope), task.priority, model_tier, maximum_attempts,
                    task.state.value, timestamp, timestamp,
                ),
            )

    def add_workcell_dependency(
        self, task_id: str, dependency_task_id: str, *, required: bool = True
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO workcell_task_dependencies(task_id, dependency_task_id, required, created_at)
                VALUES (?, ?, ?, ?)""",
                (task_id, dependency_task_id, int(required), utc_now()),
            )

    def set_workcell_wave(self, task_id: str, wave_number: int) -> None:
        if wave_number < 1:
            raise ValueError("Workcell wave number must be positive")
        with self.database.connect() as connection:
            cursor = connection.execute(
                "UPDATE workcell_tasks SET wave_number=?, updated_at=? WHERE id=?",
                (wave_number, utc_now(), task_id),
            )
        if cursor.rowcount != 1:
            raise LookupError("Workcell task not found")

    def claim_workcell_task(
        self,
        task_id: str,
        *,
        claimant: str,
        model_tier: str,
        context_sha256: str,
        brief_path: str,
        context_manifest_path: str,
        result_path: str,
    ) -> WorkcellAttempt:
        """Atomically create the sole active attempt for a ready Workcell task."""
        if not claimant.strip() or not model_tier.strip() or len(context_sha256) != 64:
            raise ValueError("invalid Workcell claim")
        timestamp = utc_now()
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM workcell_tasks WHERE id=?", (task_id,)
                ).fetchone()
                if row is None:
                    raise LookupError("Workcell task not found")
                if row["status"] != "ready":
                    raise ValueError("Workcell task is not ready to claim")
                if int(row["attempt_count"]) >= int(row["maximum_attempts"]):
                    raise ValueError("Workcell task has exhausted its attempts")
                attempt_id = new_id("workcell-attempt")
                launch_token = new_id("workcell-launch")
                attempt_number = int(row["attempt_count"]) + 1
                connection.execute(
                    """INSERT INTO workcell_attempts(
                        id, run_id, task_id, attempt_number, state, launch_token, model_tier,
                        context_sha256, brief_path, context_manifest_path, result_path,
                        child_session_id, child_handle_json, started_at, ended_at, created_at,
                        updated_at, terminal_reason
                    ) VALUES (?, ?, ?, ?, 'starting', ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?, NULL)""",
                    (
                        attempt_id, row["run_id"], task_id, attempt_number, launch_token,
                        model_tier, context_sha256, brief_path, context_manifest_path, result_path,
                        timestamp, timestamp,
                    ),
                )
                connection.execute(
                    """INSERT INTO workcell_claims(task_id, attempt_id, claim_token, claimant, acquired_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (task_id, attempt_id, launch_token, claimant, timestamp, expires_at),
                )
                cursor = connection.execute(
                    """UPDATE workcell_tasks SET status='starting', attempt_count=?, updated_at=?
                    WHERE id=? AND status='ready'""",
                    (attempt_number, timestamp, task_id),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("Workcell task changed concurrently")
                connection.execute(
                    """INSERT INTO workcell_lifecycle_events(
                        run_id, task_id, attempt_id, event_type, actor, child_session_id,
                        previous_state, new_state, details_json, correlation_id, created_at
                    ) VALUES (?, ?, ?, 'claim_acquired', ?, NULL, 'ready', 'starting', '{}', ?, ?)""",
                    (row["run_id"], task_id, attempt_id, claimant, launch_token, timestamp),
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return WorkcellAttempt.create(
            attempt_id, str(row["run_id"]), task_id, attempt_number, launch_token, model_tier, context_sha256
        )

    def list_workcell_attempts(self, task_id: str) -> tuple[WorkcellAttempt, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM workcell_attempts WHERE task_id=? ORDER BY attempt_number", (task_id,)
            ).fetchall()
        return tuple(
            WorkcellAttempt(
                str(row["id"]), str(row["run_id"]), str(row["task_id"]), int(row["attempt_number"]),
                str(row["launch_token"]), str(row["model_tier"]), str(row["context_sha256"]),
                AttemptState(str(row["state"])), row["child_session_id"], row["terminal_reason"],
            )
            for row in rows
        )

    def _get_workcell_attempt(self, attempt_id: str) -> WorkcellAttempt:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM workcell_attempts WHERE id=?", (attempt_id,)
            ).fetchone()
        if row is None:
            raise LookupError("Workcell attempt not found")
        return WorkcellAttempt(
            str(row["id"]), str(row["run_id"]), str(row["task_id"]), int(row["attempt_number"]),
            str(row["launch_token"]), str(row["model_tier"]), str(row["context_sha256"]),
            AttemptState(str(row["state"])), row["child_session_id"], row["terminal_reason"],
        )

    def get_workcell_attempt_detail(self, attempt_id: str) -> dict[str, object]:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT attempt.id, attempt.run_id, attempt.task_id, attempt.attempt_number,
                attempt.state, attempt.result_path, attempt.child_session_id, task.task_key,
                task.acceptance_json
                FROM workcell_attempts AS attempt JOIN workcell_tasks AS task ON task.id=attempt.task_id
                WHERE attempt.id=?""",
                (attempt_id,),
            ).fetchone()
        if row is None:
            raise LookupError("Workcell attempt not found")
        result = {str(key): row[key] for key in row.keys()}
        result["acceptance"] = tuple(json.loads(result.pop("acceptance_json")))
        return result

    def record_workcell_result_received(self, attempt_id: str, *, actor: str, summary: str) -> None:
        """Append a bounded validation receipt before closing an attempt."""
        if not actor.strip():
            raise ValueError("Workcell result receipt requires actor")
        timestamp = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT run_id, task_id, launch_token, child_session_id, state FROM workcell_attempts WHERE id=?",
                    (attempt_id,),
                ).fetchone()
                if row is None:
                    raise LookupError("Workcell attempt not found")
                if row["state"] not in {"starting", "running"}:
                    raise ValueError("Workcell result belongs to a closed attempt")
                connection.execute(
                    """INSERT INTO workcell_lifecycle_events(
                        run_id, task_id, attempt_id, event_type, actor, child_session_id,
                        previous_state, new_state, details_json, correlation_id, created_at
                    ) VALUES (?, ?, ?, 'child_result_received', ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row["run_id"], row["task_id"], attempt_id, actor, row["child_session_id"],
                        row["state"], row["state"], json.dumps({"summary": summary[:500]}, sort_keys=True),
                        row["launch_token"], timestamp,
                    ),
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def mark_workcell_attempt_running(
        self, attempt_id: str, *, child_session_id: str | None, child_handle: dict[str, object]
    ) -> WorkcellAttempt:
        """Record a public child launch before any result can be authoritative."""
        timestamp = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM workcell_attempts WHERE id=?", (attempt_id,)
                ).fetchone()
                if row is None:
                    raise LookupError("Workcell attempt not found")
                if row["state"] != AttemptState.STARTING.value:
                    raise ValueError("Workcell attempt is not awaiting launch")
                cursor = connection.execute(
                    """UPDATE workcell_attempts SET state='running', child_session_id=?,
                    child_handle_json=?, started_at=?, updated_at=? WHERE id=? AND state='starting'""",
                    (child_session_id, json.dumps(child_handle, sort_keys=True), timestamp, timestamp, attempt_id),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("Workcell attempt changed concurrently")
                connection.execute(
                    "UPDATE workcell_tasks SET status='running', updated_at=? WHERE id=?",
                    (timestamp, row["task_id"]),
                )
                connection.execute(
                    """INSERT INTO workcell_lifecycle_events(
                        run_id, task_id, attempt_id, event_type, actor, child_session_id,
                        previous_state, new_state, details_json, correlation_id, created_at
                    ) VALUES (?, ?, ?, 'child_started', 'parent', ?, 'starting', 'running', ?, ?, ?)""",
                    (
                        row["run_id"], row["task_id"], attempt_id, child_session_id,
                        json.dumps(child_handle, sort_keys=True), row["launch_token"], timestamp,
                    ),
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return self._get_workcell_attempt(attempt_id)

    def close_workcell_attempt(
        self, attempt_id: str, *, outcome: str, actor: str, reason: str
    ) -> WorkcellAttempt:
        """Close an active attempt atomically after parent-side validation."""
        target = AttemptState(outcome)
        if target not in {
            AttemptState.SUCCEEDED, AttemptState.BLOCKED, AttemptState.FAILED,
            AttemptState.INTERRUPTED, AttemptState.CANCELLED,
        } or not actor.strip() or not reason.strip():
            raise ValueError("invalid Workcell attempt closure")
        timestamp = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    "SELECT * FROM workcell_attempts WHERE id=?", (attempt_id,)
                ).fetchone()
                if row is None:
                    raise LookupError("Workcell attempt not found")
                if row["state"] not in {AttemptState.STARTING.value, AttemptState.RUNNING.value}:
                    raise ValueError("terminal Workcell attempt is immutable")
                cursor = connection.execute(
                    """UPDATE workcell_attempts SET state=?, ended_at=?, updated_at=?, terminal_reason=?
                    WHERE id=? AND state IN ('starting', 'running')""",
                    (target.value, timestamp, timestamp, reason, attempt_id),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("Workcell attempt changed concurrently")
                task_state = TaskState(target.value).value
                connection.execute(
                    "UPDATE workcell_tasks SET status=?, updated_at=?, blocking_reason=? WHERE id=?",
                    (task_state, timestamp, None if target is AttemptState.SUCCEEDED else reason, row["task_id"]),
                )
                connection.execute("DELETE FROM workcell_claims WHERE attempt_id=?", (attempt_id,))
                connection.execute(
                    """INSERT INTO workcell_lifecycle_events(
                        run_id, task_id, attempt_id, event_type, actor, child_session_id,
                        previous_state, new_state, details_json, correlation_id, created_at
                    ) VALUES (?, ?, ?, 'attempt_closed', ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        row["run_id"], row["task_id"], attempt_id, actor, row["child_session_id"],
                        row["state"], target.value, json.dumps({"reason": reason}, sort_keys=True),
                        row["launch_token"], timestamp,
                    ),
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return self._get_workcell_attempt(attempt_id)

    def authorize_workcell_retry(
        self,
        task_id: str,
        previous_attempt_id: str,
        *,
        actor: str,
        reason: str,
        material_change: str,
        new_context_sha256: str,
        new_model_tier: str,
    ) -> str:
        """Record an attributed material retry decision and return a task to ready."""
        if not actor.strip() or not reason.strip() or len(new_context_sha256) != 64 or not new_model_tier.strip():
            raise ValueError("invalid Workcell retry request")
        timestamp = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                row = connection.execute(
                    """SELECT attempt.*, task.maximum_attempts, task.attempt_count, task.status AS task_status
                    FROM workcell_attempts AS attempt JOIN workcell_tasks AS task ON task.id=attempt.task_id
                    WHERE attempt.id=? AND attempt.task_id=?""",
                    (previous_attempt_id, task_id),
                ).fetchone()
                if row is None:
                    raise LookupError("Workcell attempt not found for task")
                if row["state"] not in {
                    AttemptState.BLOCKED.value, AttemptState.FAILED.value,
                    AttemptState.INTERRUPTED.value, AttemptState.CANCELLED.value,
                }:
                    raise ValueError("only a closed unsuccessful Workcell attempt can be retried")
                if int(row["attempt_count"]) >= int(row["maximum_attempts"]):
                    raise ValueError("Workcell task has exhausted its attempts")
                changed = (
                    bool(material_change.strip())
                    or new_context_sha256 != row["context_sha256"]
                    or new_model_tier != row["model_tier"]
                )
                if not changed:
                    raise ValueError("Workcell retry requires a material change")
                decision_id = new_id("workcell-retry")
                connection.execute(
                    """INSERT INTO workcell_retry_decisions(
                        id, task_id, previous_attempt_id, actor, reason, material_change,
                        old_context_sha256, new_context_sha256, old_model_tier, new_model_tier, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        decision_id, task_id, previous_attempt_id, actor, reason, material_change,
                        row["context_sha256"], new_context_sha256, row["model_tier"], new_model_tier, timestamp,
                    ),
                )
                cursor = connection.execute(
                    """UPDATE workcell_tasks SET status='ready', blocking_reason=NULL, model_tier=?, updated_at=?
                    WHERE id=? AND status=?""",
                    (new_model_tier, timestamp, task_id, row["task_status"]),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("Workcell task changed concurrently")
                connection.execute(
                    """INSERT INTO workcell_lifecycle_events(
                        run_id, task_id, attempt_id, event_type, actor, child_session_id,
                        previous_state, new_state, details_json, correlation_id, created_at
                    ) VALUES (?, ?, ?, 'retry_authorized', ?, ?, ?, 'ready', ?, ?, ?)""",
                    (
                        row["run_id"], task_id, previous_attempt_id, actor, row["child_session_id"],
                        row["state"], json.dumps({"reason": reason, "material_change": material_change}, sort_keys=True),
                        decision_id, timestamp,
                    ),
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return decision_id

    def reconcile_workcell_attempt(self, attempt_id: str, *, actor: str) -> WorkcellAttempt:
        """Fail closed when public Hermes cannot prove a recorded child is alive."""
        if not actor.strip():
            raise ValueError("Workcell reconciliation requires actor")
        attempt = self._get_workcell_attempt(attempt_id)
        if attempt.state not in {AttemptState.STARTING, AttemptState.RUNNING}:
            return attempt
        return self.close_workcell_attempt(
            attempt_id,
            outcome=AttemptState.INTERRUPTED.value,
            actor=actor,
            reason="public Hermes child status is unavailable; recovery required",
        )

    def list_workcell_task_rows(self, run_id: str) -> tuple[dict[str, object], ...]:
        """Return bounded inspectable Workcell task state in deterministic order."""
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT id, task_key, title, status, wave_number, priority, model_tier,
                maximum_attempts, attempt_count, blocking_reason, escalation_state
                FROM workcell_tasks WHERE run_id=? ORDER BY wave_number, priority, task_key""",
                (run_id,),
            ).fetchall()
        return tuple({str(key): row[key] for key in row.keys()} for row in rows)

    def get_workcell_task_detail(self, task_id: str) -> dict[str, object]:
        with self.database.connect() as connection:
            row = connection.execute(
                """SELECT id, run_id, task_key, title, objective, acceptance_json, required,
                read_scope_json, write_scope_json, graph_revision_id, wave_number, priority,
                model_tier, maximum_attempts, attempt_count, status
                FROM workcell_tasks WHERE id=?""",
                (task_id,),
            ).fetchone()
        if row is None:
            raise LookupError("Workcell task not found")
        result = {str(key): row[key] for key in row.keys()}
        for key in ("acceptance", "read_scope", "write_scope"):
            result[key] = tuple(json.loads(result.pop(f"{key}_json")))
        result["required"] = bool(result["required"])
        return result

    def list_workcell_lifecycle_events(self, attempt_id: str) -> tuple[dict[str, object], ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT sequence, event_type, actor, child_session_id, previous_state,
                new_state, details_json, correlation_id, created_at
                FROM workcell_lifecycle_events WHERE attempt_id=? ORDER BY sequence""",
                (attempt_id,),
            ).fetchall()
        return tuple(
            {
                "sequence": int(row["sequence"]), "event_type": str(row["event_type"]),
                "actor": str(row["actor"]), "child_session_id": row["child_session_id"],
                "previous_state": row["previous_state"], "new_state": row["new_state"],
                "details": json.loads(row["details_json"]), "correlation_id": str(row["correlation_id"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        )

    def refresh_workcell_readiness(self, run_id: str) -> tuple[str, ...]:
        """Promote dependency-satisfied pending tasks, blocking failed dependency paths."""
        timestamp = utc_now()
        unsuccessful = {"blocked", "failed", "interrupted", "cancelled", "escalated"}
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                tasks = connection.execute(
                    "SELECT id, task_key FROM workcell_tasks WHERE run_id=? AND status='pending' ORDER BY wave_number, priority, task_key",
                    (run_id,),
                ).fetchall()
                ready: list[str] = []
                for task in tasks:
                    dependencies = connection.execute(
                        """SELECT dependency.status, dependency.task_key, edge.required
                        FROM workcell_task_dependencies AS edge
                        JOIN workcell_tasks AS dependency ON dependency.id=edge.dependency_task_id
                        WHERE edge.task_id=? ORDER BY dependency.task_key""",
                        (task["id"],),
                    ).fetchall()
                    failed = next(
                        (
                            row for row in dependencies
                            if bool(row["required"]) and str(row["status"]) in unsuccessful
                        ),
                        None,
                    )
                    if failed is not None:
                        connection.execute(
                            "UPDATE workcell_tasks SET status='blocked', blocking_reason=?, updated_at=? WHERE id=? AND status='pending'",
                            (f"required dependency failed: {failed['task_key']}", timestamp, task["id"]),
                        )
                        continue
                    if all(not bool(row["required"]) or str(row["status"]) == "succeeded" for row in dependencies):
                        cursor = connection.execute(
                            "UPDATE workcell_tasks SET status='ready', updated_at=? WHERE id=? AND status='pending'",
                            (timestamp, task["id"]),
                        )
                        if cursor.rowcount == 1:
                            ready.append(str(task["task_key"]))
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return tuple(ready)

    def add_verification_check(self, check: VerificationCheck) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO verification_checks(id, run_id, name, command, required, timeout_seconds)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    check.id, check.run_id, check.name, check.command,
                    int(check.required), check.timeout_seconds,
                ),
            )

    def list_verification_checks(self, run_id: str) -> tuple[VerificationCheck, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM verification_checks WHERE run_id=? ORDER BY name", (run_id,)
            ).fetchall()
        return tuple(
            VerificationCheck.from_dict({**dict(row), "required": bool(row["required"])})
            for row in rows
        )

    def add_evidence(self, evidence: Evidence) -> None:
        data = evidence.to_dict()
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO evidence(
                    id, run_id, check_name, command, exit_code, status, head_sha,
                    diff_sha256, untracked_sha256, output_path, output_sha256,
                    started_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tuple(data[key] for key in (
                    "id", "run_id", "check_name", "command", "exit_code", "status", "head_sha",
                    "diff_sha256", "untracked_sha256", "output_path", "output_sha256",
                    "started_at", "completed_at",
                )),
            )

    def list_evidence(self, run_id: str) -> tuple[Evidence, ...]:
        return self._list_models(
            "SELECT * FROM evidence WHERE run_id=? ORDER BY completed_at, id", run_id, Evidence
        )

    def add_waiver(self, waiver: Waiver) -> None:
        data = waiver.to_dict()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """INSERT INTO waivers(
                        id, run_id, name, rule_key, tool_name, command_sha256, path_scope,
                        profile, stage, rationale, actor, source, created_at, expires_at,
                        revoked_at, revoked_by, revocation_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    tuple(data[key] for key in (
                        "id", "run_id", "name", "rule_key", "tool_name", "command_sha256",
                        "path_scope", "profile", "stage", "rationale", "actor", "source",
                        "created_at", "expires_at", "revoked_at", "revoked_by",
                        "revocation_reason",
                    )),
                )
                connection.execute(
                    """INSERT INTO waiver_events(
                        waiver_id, event_type, actor, source, rationale, created_at
                    ) VALUES (?, 'created', ?, ?, ?, ?)""",
                    (waiver.id, waiver.actor, waiver.source, waiver.rationale, waiver.created_at),
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def list_waivers(self, run_id: str | None = None) -> tuple[Waiver, ...]:
        with self.database.connect() as connection:
            if run_id is None:
                rows = connection.execute("SELECT * FROM waivers ORDER BY created_at, id").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM waivers WHERE run_id=? ORDER BY created_at, id", (run_id,)
                ).fetchall()
        return tuple(Waiver.from_dict(dict(row)) for row in rows)

    def list_applicable_waivers(self, run_id: str) -> tuple[Waiver, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """SELECT * FROM waivers
                WHERE run_id IS NULL OR run_id=? ORDER BY created_at, id""",
                (run_id,),
            ).fetchall()
        return tuple(Waiver.from_dict(dict(row)) for row in rows)

    def get_waiver(self, name: str) -> Waiver:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM waivers WHERE name=?", (name,)).fetchone()
        if row is None:
            raise LookupError(f"waiver not found: {name}")
        return Waiver.from_dict(dict(row))

    def revoke_waiver(
        self, name: str, actor: str, source: str, reason: str, now: str
    ) -> Waiver:
        current = self.get_waiver(name)
        if current.revoked_at is not None:
            raise ValueError(f"waiver already revoked: {name}")
        updated = replace(
            current, revoked_at=now, revoked_by=actor, revocation_reason=reason
        )
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                cursor = connection.execute(
                    """UPDATE waivers SET revoked_at=?, revoked_by=?, revocation_reason=?
                    WHERE id=? AND revoked_at IS NULL""",
                    (updated.revoked_at, updated.revoked_by, updated.revocation_reason, updated.id),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("waiver changed concurrently; reload before revoking")
                connection.execute(
                    """INSERT INTO waiver_events(
                        waiver_id, event_type, actor, source, rationale, created_at
                    ) VALUES (?, 'revoked', ?, ?, ?, ?)""",
                    (updated.id, actor, source, reason, updated.revoked_at),
                )
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return updated

    def expire_due_waivers(self, now: str) -> tuple[str, ...]:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                rows = connection.execute(
                    """SELECT id FROM waivers
                    WHERE revoked_at IS NULL AND expires_at<=? ORDER BY expires_at, id""",
                    (now,),
                ).fetchall()
                recorded: list[str] = []
                for row in rows:
                    cursor = connection.execute(
                        """INSERT OR IGNORE INTO waiver_events(
                            waiver_id, event_type, actor, source, rationale, created_at
                        ) VALUES (?, 'expired', 'system', 'policy', 'expiry reached', ?)""",
                        (row["id"], now),
                    )
                    if cursor.rowcount == 1:
                        recorded.append(str(row["id"]))
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()
        return tuple(recorded)

    def list_waiver_events(self, waiver_id: str) -> tuple[WaiverEvent, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM waiver_events WHERE waiver_id=? ORDER BY sequence", (waiver_id,)
            ).fetchall()
        return tuple(WaiverEvent.from_dict(dict(row)) for row in rows)

    def add_policy_decision(self, record: PolicyDecisionRecord) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO policy_decisions(
                    id, run_id, tool_name, action, rule_key, reason, trace_json,
                    arguments_sha256, config_sha256, waiver_id, suggested_risk, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id, record.run_id, record.tool_name, record.action, record.rule_key,
                    record.reason,
                    json.dumps([item.to_dict() for item in record.trace], sort_keys=True),
                    record.arguments_sha256, record.config_sha256, record.waiver_id,
                    record.suggested_risk.value if record.suggested_risk else None,
                    record.created_at,
                ),
            )

    def list_policy_decisions(self, run_id: str) -> tuple[PolicyDecisionRecord, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM policy_decisions WHERE run_id=? ORDER BY sequence", (run_id,)
            ).fetchall()
        records: list[PolicyDecisionRecord] = []
        for row in rows:
            payload = dict(row)
            payload["trace"] = json.loads(payload.pop("trace_json"))
            records.append(PolicyDecisionRecord.from_dict(payload))
        return tuple(records)

    def get_policy_decision(self, run_id: str, sequence: int) -> PolicyDecisionRecord:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM policy_decisions WHERE run_id=? AND sequence=?",
                (run_id, sequence),
            ).fetchone()
        if row is None:
            raise LookupError(f"policy decision not found: {sequence}")
        payload = dict(row)
        payload["trace"] = json.loads(payload.pop("trace_json"))
        return PolicyDecisionRecord.from_dict(payload)

    def add_risk_suggestion(self, suggestion: RiskSuggestion) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """INSERT INTO risk_suggestions(
                    id, run_id, task_id, suggested_risk, reasons_json, accepted_risk,
                    override_rationale, created_at, accepted_by, accepted_source, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    suggestion.id, suggestion.run_id, suggestion.task_id,
                    suggestion.suggested_risk.value, json.dumps(suggestion.reasons),
                    suggestion.accepted_risk.value if suggestion.accepted_risk else None,
                    suggestion.override_rationale, suggestion.created_at,
                    suggestion.accepted_by, suggestion.accepted_source, suggestion.decided_at,
                ),
            )

    def list_risk_suggestions(self, run_id: str) -> tuple[RiskSuggestion, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM risk_suggestions WHERE run_id=? ORDER BY sequence", (run_id,)
            ).fetchall()
        suggestions: list[RiskSuggestion] = []
        for row in rows:
            payload = dict(row)
            payload.pop("sequence")
            payload["reasons"] = json.loads(payload.pop("reasons_json"))
            suggestions.append(RiskSuggestion.from_dict(payload))
        return tuple(suggestions)

    def get_risk_suggestion(self, suggestion_id: str) -> RiskSuggestion:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM risk_suggestions WHERE id=?", (suggestion_id,)
            ).fetchone()
        if row is None:
            raise LookupError(f"risk suggestion not found: {suggestion_id}")
        payload = dict(row)
        payload.pop("sequence")
        payload["reasons"] = json.loads(payload.pop("reasons_json"))
        return RiskSuggestion.from_dict(payload)

    def decide_risk_suggestion(
        self,
        suggestion_id: str,
        accepted_risk: RiskLevel,
        rationale: str,
        actor: str,
        source: str,
        now: str,
    ) -> RiskSuggestion:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """UPDATE risk_suggestions SET accepted_risk=?, override_rationale=?,
                accepted_by=?, accepted_source=?, decided_at=?
                WHERE id=? AND accepted_risk IS NULL""",
                (accepted_risk.value, rationale or None, actor, source, now, suggestion_id),
            )
        if cursor.rowcount != 1:
            raise ValueError("risk suggestion not found or already decided")
        return self.get_risk_suggestion(suggestion_id)

    def _list_models(self, sql: str, run_id: str, model: Any) -> tuple[Any, ...]:
        with self.database.connect() as connection:
            rows = connection.execute(sql, (run_id,)).fetchall()
        return tuple(model.from_dict(dict(row)) for row in rows)
