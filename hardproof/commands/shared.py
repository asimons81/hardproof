"""Single command implementation used by every human-facing surface."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import yaml

from hardproof.compat import inspect_context
from hardproof.config import DEFAULTS, ConfigError, load_config
from hardproof.domain.enums import ApprovalGate, RunProfile, RunStage
from hardproof.domain.models import Run, SessionBinding, VerificationCheck, new_id, utc_now
from hardproof.paths import ProjectPaths
from hardproof.policy.stage_rules import TransitionFacts
from hardproof.services.approvals import ApprovalService
from hardproof.services.evidence import evidence_with_freshness
from hardproof.services.runs import RunService
from hardproof.services.reports import ReportService
from hardproof.storage.database import Database, DatabaseCorruptionError
from hardproof.storage.migrations import MigrationError, migrate
from hardproof.storage.repository import RunRepository


_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|token|password|authorization|cookie)\s*[:=]\s*([^\s,;]+)"
)


def _redact(value: str) -> str:
    return _SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


@dataclass(frozen=True, slots=True)
class CommandContext:
    project_root: Path
    actor: str
    source: str
    session_id: str | None = None
    platform: str | None = None
    hermes_context: Any | None = None

    def __init__(
        self,
        project_root: str | Path,
        *,
        actor: str,
        source: str,
        session_id: str | None = None,
        platform: str | None = None,
        hermes_context: Any | None = None,
    ) -> None:
        object.__setattr__(self, "project_root", Path(project_root).resolve())
        object.__setattr__(self, "actor", actor)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "platform", platform)
        object.__setattr__(self, "hermes_context", hermes_context)


@dataclass(frozen=True, slots=True)
class CommandResult:
    ok: bool
    text: str
    run_id: str | None = None


class CommandService:
    def __init__(self, context: CommandContext) -> None:
        self.context = context
        self.paths = ProjectPaths(context.project_root)
        self.database = Database(self.paths.database)
        migrate(self.database)
        self.repository = RunRepository(self.database)
        self.run_service = RunService(self.repository)

    @property
    def _active_pointer(self) -> Path:
        return self.paths.root / "state" / "active-run"

    def _set_active(self, run_id: str) -> None:
        self._active_pointer.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._active_pointer.with_name(f"active-run.{uuid4().hex}.tmp")
        temporary.write_text(f"{run_id}\n", encoding="utf-8")
        os.replace(temporary, self._active_pointer)

    def active_run_id(self) -> str:
        if not self._active_pointer.exists():
            raise LookupError("no active Hardproof run in this workspace")
        run_id = self._active_pointer.read_text(encoding="utf-8").strip()
        if not run_id:
            raise LookupError("active run pointer is empty")
        self.repository.get_run(run_id)
        return run_id

    def _git_root(self) -> Path | None:
        result = subprocess.run(
            ["git", "-C", str(self.context.project_root), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None

    def _ensure_state_ignored(self, git_root: Path) -> None:
        probe = subprocess.run(
            ["git", "-C", str(git_root), "check-ignore", "-q", ".hardproof/state/probe"],
            capture_output=True, check=False, timeout=10,
        )
        if probe.returncode == 0:
            return
        exclude = git_root / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        separator = "" if not existing or existing.endswith("\n") else "\n"
        exclude.write_text(existing + separator + ".hardproof/\n", encoding="utf-8")

    def _facts(self, run_id: str) -> TransitionFacts:
        events = self.repository.list_events(run_id)
        return TransitionFacts(
            artifacts=self.repository.list_artifacts(run_id),
            approvals=self.repository.list_approvals(run_id),
            tasks=self.repository.list_tasks(run_id),
            evidence=evidence_with_freshness(
                self.repository.list_evidence(run_id), self.context.project_root
            ),
            approved_review=any(event.event_type == "review_approved" for event in events),
            recorded_change=any(event.event_type == "change_recorded" for event in events),
            learning_skipped=any(event.event_type == "learning_skipped" for event in events),
        )

    def transition_facts(self, run_id: str) -> TransitionFacts:
        """Return current durable facts for model-requested transition evaluation."""
        return self._facts(run_id)

    def execute(self, argv: list[str]) -> CommandResult:
        if not argv:
            raise ValueError("a Hardproof subcommand is required")
        command, rest = argv[0], argv[1:]
        handlers: dict[str, Callable[[list[str]], CommandResult]] = {
            "start": self._start, "status": self._status, "approve": self._approve,
            "waive": self._waive, "pause": self._pause, "resume": self._resume,
            "abort": self._abort, "evidence": self._evidence, "export": self._export,
            "doctor": self._doctor, "runs": self._runs, "show": self._show,
            "config": self._config, "db": self._db, "complete": self._complete,
            "migrate-state": self._migrate_state,
        }
        if command not in handlers:
            raise ValueError(f"unknown Hardproof subcommand: {command}")
        return handlers[command](rest)

    @staticmethod
    def _expect_no_args(command: str, rest: list[str]) -> None:
        if rest:
            raise ValueError(f"{command} does not accept arguments")

    def _start(self, rest: list[str]) -> CommandResult:
        if len(rest) < 2:
            raise ValueError("usage: start <quick|standard|critical> <request>")
        git_root = self._git_root()
        if git_root is None:
            raise ValueError("Hardproof managed runs require a Git repository")
        self._ensure_state_ignored(git_root)
        try:
            profile = RunProfile(rest[0])
        except ValueError as exc:
            raise ValueError("profile must be quick, standard, or critical") from exc
        request = " ".join(rest[1:]).strip()
        run = Run.create(str(self.context.project_root), request, profile)
        self.repository.create_run(run)
        config = load_config(self.paths.config)
        for item in config.verification_checks:
            self.repository.add_verification_check(VerificationCheck(
                new_id("check"), run.id, item.name, item.command, item.required, item.timeout_seconds
            ))
        if self.context.session_id:
            self.repository.save_session_binding(SessionBinding(
                self.context.session_id, run.id, self.context.platform, utc_now()
            ))
        self._set_active(run.id)
        return CommandResult(True, f"Hardproof run {run.id} started in INTAKE ({profile.value}).", run.id)

    def _status(self, rest: list[str]) -> CommandResult:
        self._expect_no_args("status", rest)
        run = self.repository.get_run(self.active_run_id())
        return CommandResult(
            True,
            f"Run: {run.id}\nProfile: {run.profile.value}\nStage: {run.stage.value}\nStatus: {run.status.value}",
            run.id,
        )

    def _approve(self, rest: list[str]) -> CommandResult:
        if not rest:
            raise ValueError("usage: approve <design|plan|completion> [reason]")
        try:
            gate = ApprovalGate(rest[0])
        except ValueError as exc:
            raise ValueError("approval gate must be design, plan, or completion") from exc
        if gate not in {ApprovalGate.DESIGN, ApprovalGate.PLAN, ApprovalGate.COMPLETION}:
            raise ValueError("approval gate must be design, plan, or completion")
        ApprovalService(self.repository).create_human(
            self.active_run_id(), gate, actor=self.context.actor,
            source=self.context.source, reason=" ".join(rest[1:]) or None,
        )
        return CommandResult(True, f"Human {gate.value} approval recorded.", self.active_run_id())

    def _waive(self, rest: list[str]) -> CommandResult:
        if len(rest) < 2:
            raise ValueError("usage: waive <gate> <reason>")
        reason = f"{rest[0]}: {' '.join(rest[1:])}"
        ApprovalService(self.repository).create_human(
            self.active_run_id(), ApprovalGate.WAIVER, actor=self.context.actor,
            source=self.context.source, reason=reason,
        )
        return CommandResult(True, f"Human waiver recorded for {rest[0]}.", self.active_run_id())

    def _pause(self, rest: list[str]) -> CommandResult:
        run = self.run_service.pause(self.active_run_id(), reason=" ".join(rest) or "human pause")
        return CommandResult(True, f"Run {run.id} is {run.stage.value}.", run.id)

    def _resume(self, rest: list[str]) -> CommandResult:
        if len(rest) > 1:
            raise ValueError("usage: resume [run-id]")
        if rest:
            self.repository.get_run(rest[0])
            self._set_active(rest[0])
        run = self.run_service.resume(self.active_run_id(), reason="human resume")
        if self.context.session_id:
            self.repository.save_session_binding(SessionBinding(
                self.context.session_id, run.id, self.context.platform, utc_now()
            ))
        return CommandResult(True, f"Run {run.id} resumed at {run.stage.value}.", run.id)

    def _abort(self, rest: list[str]) -> CommandResult:
        if not rest:
            raise ValueError("usage: abort <reason>")
        run_id = self.active_run_id()
        run = self.run_service.transition(
            run_id, RunStage.ABORTED, self._facts(run_id), reason=" ".join(rest)
        )
        return CommandResult(True, f"Run {run.id} is {run.stage.value}.", run.id)

    def _evidence(self, rest: list[str]) -> CommandResult:
        self._expect_no_args("evidence", rest)
        run_id = self.active_run_id()
        evidence = self.repository.list_evidence(run_id)
        if not evidence:
            return CommandResult(True, "No verification evidence recorded.", run_id)
        lines = [
            f"{item.check_name}: {item.status.value} exit={item.exit_code if item.exit_code is not None else 'unknown'}"
            for item in evidence
        ]
        return CommandResult(True, "\n".join(lines), run_id)

    def _export(self, rest: list[str]) -> CommandResult:
        if len(rest) > 1:
            raise ValueError("usage: export [path]")
        run = self.repository.get_run(self.active_run_id())
        destination = Path(rest[0]).expanduser().resolve() if rest else None
        paths = ReportService(
            self.repository, self.context.project_root, self.paths.run_directory(run.id)
        ).export(run.id, destination=destination, format="both")
        rendered = ", ".join(str(path) for path in paths.values())
        return CommandResult(True, f"Export written to {rendered}.", run.id)

    def _doctor(self, rest: list[str]) -> CommandResult:
        self._expect_no_args("doctor", rest)
        checks: list[tuple[str, bool, str]] = []
        git_root = self._git_root()
        checks.append(("Git repository", git_root is not None, str(git_root) if git_root else "not found"))
        try:
            load_config(self.paths.config)
            checks.append(("Config", True, "valid"))
        except ConfigError as exc:
            checks.append(("Config", False, str(exc)))
        try:
            migrate(self.database)
            checks.append(("Database", True, "schema current"))
        except (MigrationError, DatabaseCorruptionError) as exc:
            checks.append(("Database", False, str(exc)))
        writable = os.access(self.paths.root, os.W_OK) if self.paths.root.exists() else os.access(self.context.project_root, os.W_OK)
        checks.append(("Write access", writable, "available" if writable else "denied"))
        if self.context.hermes_context is not None:
            report = inspect_context(self.context.hermes_context)
            checks.append(("Hermes API", report.compatible, report.hermes_version or "unknown version"))
        try:
            active = self.active_run_id()
            checks.append(("Active binding", True, active))
        except LookupError:
            checks.append(("Active binding", True, "none"))
        text = "\n".join(f"{'PASS' if ok else 'FAIL'} {name}: {detail}" for name, ok, detail in checks)
        return CommandResult(all(ok for _, ok, _ in checks), text)

    def _runs(self, rest: list[str]) -> CommandResult:
        self._expect_no_args("runs", rest)
        runs = self.repository.list_runs()
        text = "\n".join(f"{run.id} {run.profile.value} {run.stage.value} {run.status.value}" for run in runs)
        return CommandResult(True, text or "No Hardproof runs found.")

    def _show(self, rest: list[str]) -> CommandResult:
        if len(rest) != 1:
            raise ValueError("usage: show <run-id>")
        run = self.repository.get_run(rest[0])
        return CommandResult(
            True,
            f"Run: {run.id}\nRequest: {_redact(run.request)}\nProfile: {run.profile.value}\nStage: {run.stage.value}\nStatus: {run.status.value}",
            run.id,
        )

    def _config(self, rest: list[str]) -> CommandResult:
        if len(rest) != 1 or rest[0] not in {"init", "validate"}:
            raise ValueError("usage: config <init|validate>")
        if rest[0] == "validate":
            load_config(self.paths.config)
            return CommandResult(True, f"Config is valid: {self.paths.config}")
        if self.paths.config.exists():
            raise ValueError(f"config already exists: {self.paths.config}")
        self.paths.config.parent.mkdir(parents=True, exist_ok=True)
        self.paths.config.write_text(yaml.safe_dump(DEFAULTS, sort_keys=True), encoding="utf-8")
        load_config(self.paths.config)
        return CommandResult(True, f"Config initialized: {self.paths.config}")

    def _db(self, rest: list[str]) -> CommandResult:
        if rest != ["migrate"]:
            raise ValueError("usage: db migrate")
        applied = migrate(self.database)
        detail = ", ".join(map(str, applied)) if applied else "already current"
        return CommandResult(True, f"Database migration: {detail}")

    def _migrate_state(self, rest: list[str]) -> CommandResult:
        """Migrate a pre-rename .crucible state directory to .hardproof."""
        self._expect_no_args("migrate-state", rest)
        project = self.context.project_root
        old_dir = project / ".crucible"
        new_dir = project / ".hardproof"
        backup_dir = project / ".hardproof.backup"

        old_exists = old_dir.exists()
        new_exists = new_dir.exists()

        if not old_exists:
            return CommandResult(
                False,
                f"No pre-rename state directory found at {old_dir}. Nothing to migrate."
            )
        if new_exists and old_exists:
            # CommandService.__init__ may have auto-created .hardproof/state/.
            # If the new directory is empty aside from that skeleton, remove it
            # so migration can proceed.
            auto_created = True
            for item in new_dir.rglob("*"):
                rel = item.relative_to(new_dir)
                parts = rel.parts
                if parts[0] == "state" and len(parts) <= 2:
                    continue  # state/ or state/hardproof.db*
                auto_created = False
                break
            if auto_created:
                shutil.rmtree(new_dir, ignore_errors=True)
            else:
                return CommandResult(
                    False,
                    f"Both {old_dir} and {new_dir} exist and {new_dir} has active state. "
                    f"Resolve manually: remove one directory before migrating."
                )
        if new_exists and not old_exists:
            return CommandResult(False, f"{new_dir} already exists. Nothing to migrate.")
        if backup_dir.exists():
            return CommandResult(
                False,
                f"Backup directory {backup_dir} already exists. "
                f"Remove it or rename it before retrying migration."
            )

        try:
            shutil.copytree(old_dir, backup_dir, symlinks=False)
        except OSError as exc:
            return CommandResult(False, f"Failed to create backup at {backup_dir}: {exc}")

        db_path = old_dir / "state" / "hardproof.db"
        db_integrity_ok = True
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()
                if result and result[0] != "ok":
                    db_integrity_ok = False
            except Exception as exc:
                return CommandResult(
                    False,
                    f"Source database at {db_path} is unreadable: {exc}. "
                    f"Backup preserved at {backup_dir}."
                )

        if not db_integrity_ok:
            return CommandResult(
                False,
                f"Source database at {db_path} failed integrity check. "
                f"Backup preserved at {backup_dir}. Manual recovery required."
            )

        try:
            shutil.copytree(old_dir, new_dir, symlinks=False)
        except OSError as exc:
            shutil.rmtree(backup_dir, ignore_errors=True)
            return CommandResult(False, f"Failed to copy {old_dir} to {new_dir}: {exc}")

        new_db = new_dir / "state" / "hardproof.db"
        if new_db.exists():
            try:
                conn = sqlite3.connect(str(new_db))
                cursor = conn.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                conn.close()
                if not result or result[0] != "ok":
                    shutil.rmtree(new_dir, ignore_errors=True)
                    return CommandResult(
                        False,
                        f"Migrated database at {new_db} failed integrity check. "
                        f"New directory removed. Backup preserved at {backup_dir}."
                    )
            except Exception as exc:
                shutil.rmtree(new_dir, ignore_errors=True)
                return CommandResult(
                    False,
                    f"Migrated database at {new_db} is unreadable: {exc}. "
                    f"New directory removed. Backup preserved at {backup_dir}."
                )

        report = {
            "migrated_at": utc_now(),
            "source": str(old_dir),
            "destination": str(new_dir),
            "backup": str(backup_dir),
            "database_integrity": "ok",
        }
        report_path = new_dir / "migration-report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        return CommandResult(
            True,
            f"State migrated from {old_dir} to {new_dir}.\n"
            f"Backup preserved at {backup_dir}.\n"
            f"Migration report at {report_path}.\n"
            f"The old .crucible directory was not removed. Delete it after confirming the migration."
        )

    def _complete(self, rest: list[str]) -> CommandResult:
        self._expect_no_args("complete", rest)
        run_id = self.active_run_id()
        run = self.run_service.transition(
            run_id, RunStage.COMPLETE, self._facts(run_id), reason="human completion command"
        )
        return CommandResult(True, f"Run {run.id} is COMPLETE.", run.id)
