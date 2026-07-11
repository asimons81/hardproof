"""Typed repository operations over short-lived SQLite connections."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from crucible_agent.domain.models import (
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
    utc_now,
)
from crucible_agent.domain.enums import RiskLevel, RunStage, RunStatus
from crucible_agent.storage.database import Database


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
