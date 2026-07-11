"""Single command implementation used by every human-facing surface."""

from __future__ import annotations

import os
import re
import subprocess
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import yaml

from crucible_agent.compat import inspect_context
from crucible_agent.config import DEFAULTS, ConfigError, config_fingerprint, load_config
from crucible_agent.domain.enums import ApprovalGate, RiskLevel, RunProfile, RunStage
from crucible_agent.domain.models import Run, SessionBinding, VerificationCheck, new_id, utc_now
from crucible_agent.paths import ProjectPaths
from crucible_agent.policy.stage_rules import TransitionFacts
from crucible_agent.policy.tool_rules import ToolPolicyContext, evaluate_tool_call
from crucible_agent.services.approvals import ApprovalService
from crucible_agent.services.evidence import evidence_with_freshness
from crucible_agent.services.runs import RunService
from crucible_agent.services.reports import ReportService
from crucible_agent.services.risks import RiskService
from crucible_agent.services.waivers import WaiverService
from crucible_agent.storage.database import Database, DatabaseCorruptionError
from crucible_agent.storage.migrations import MigrationError, migrate
from crucible_agent.storage.repository import RunRepository


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
            raise LookupError("no active Crucible run in this workspace")
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
            ["git", "-C", str(git_root), "check-ignore", "-q", ".crucible/state/probe"],
            capture_output=True, check=False, timeout=10,
        )
        if probe.returncode == 0:
            return
        exclude = git_root / ".git" / "info" / "exclude"
        exclude.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        separator = "" if not existing or existing.endswith("\n") else "\n"
        exclude.write_text(existing + separator + ".crucible/\n", encoding="utf-8")

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

    @staticmethod
    def _policy_payload(
        *,
        sequence: int | None,
        identifier: str | None,
        tool_name: str,
        action: str,
        rule_key: str,
        reason: str,
        trace: tuple[Any, ...],
        arguments_sha256: str,
        config_sha256: str,
        waiver_id: str | None,
        created_at: str | None,
    ) -> dict[str, Any]:
        return {
            "sequence": sequence,
            "id": identifier,
            "tool_name": tool_name,
            "action": action,
            "rule_key": rule_key,
            "reason": reason,
            "trace": [item.to_dict() for item in trace],
            "arguments_sha256": arguments_sha256,
            "config_sha256": config_sha256,
            "waiver_id": waiver_id,
            "created_at": created_at,
        }

    def explain_policy(
        self,
        *,
        event_sequence: int | None = None,
        tool_name: str | None = None,
        args: dict[str, Any] | None = None,
        now: str | None = None,
    ) -> dict[str, Any]:
        run_id = self.active_run_id()
        if (event_sequence is None) == (tool_name is None):
            raise ValueError("choose exactly one policy event or hypothetical tool call")
        if event_sequence is not None:
            record = self.repository.get_policy_decision(run_id, event_sequence)
            return self._policy_payload(
                sequence=record.sequence, identifier=record.id, tool_name=record.tool_name,
                action=record.action, rule_key=record.rule_key, reason=record.reason,
                trace=record.trace, arguments_sha256=record.arguments_sha256,
                config_sha256=record.config_sha256, waiver_id=record.waiver_id,
                created_at=record.created_at,
            )
        safe_args = args if isinstance(args, dict) else {}
        canonical = json.dumps(safe_args, sort_keys=True, separators=(",", ":"), default=str)
        if len(canonical) > 16_384:
            raise ValueError("hypothetical policy arguments exceed 16384 characters")
        config = load_config(self.paths.config)
        run = self.repository.get_run(run_id)
        effective_time = now or utc_now()
        context = ToolPolicyContext(
            run, self.context.project_root, self.paths.run_directory(run.id),
            frozenset(config.mutating_tools), policy=config.policy,
            config_sha256=config_fingerprint(config),
            waivers=self.repository.list_applicable_waivers(run.id),
            effective_time=effective_time,
        )
        decision = evaluate_tool_call(str(tool_name), safe_args, context)
        return self._policy_payload(
            sequence=None, identifier=None, tool_name=str(tool_name), action=decision.action,
            rule_key=decision.rule_key, reason=decision.reason, trace=decision.trace,
            arguments_sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            config_sha256=context.config_sha256, waiver_id=decision.waiver_id,
            created_at=None,
        )

    @staticmethod
    def _render_policy_explanation(payload: dict[str, Any], format: str) -> str:
        if format == "json":
            return json.dumps(payload, sort_keys=True, separators=(",", ":"))
        lines = [
            f"Action: {payload['action']}", f"Rule: {payload['rule_key']}",
            f"Reason: {payload['reason']}", "Trace:",
        ]
        lines.extend(
            f"{index}. {item['rule_key']} [{item['outcome']}] {item['explanation']}"
            for index, item in enumerate(payload["trace"], 1)
        )
        lines.append(f"Arguments SHA-256: {payload['arguments_sha256']}")
        lines.append(f"Config SHA-256: {payload['config_sha256']}")
        return "\n".join(lines)

    def execute(self, argv: list[str]) -> CommandResult:
        if not argv:
            raise ValueError("a Crucible subcommand is required")
        command, rest = argv[0], argv[1:]
        handlers: dict[str, Callable[[list[str]], CommandResult]] = {
            "start": self._start, "status": self._status, "approve": self._approve,
            "waive": self._waive, "pause": self._pause, "resume": self._resume,
            "abort": self._abort, "evidence": self._evidence, "export": self._export,
            "doctor": self._doctor, "runs": self._runs, "show": self._show,
            "config": self._config, "db": self._db, "complete": self._complete,
            "policy": self._policy,
        }
        if command not in handlers:
            raise ValueError(f"unknown Crucible subcommand: {command}")
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
            raise ValueError("Crucible managed runs require a Git repository")
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
        return CommandResult(True, f"Crucible run {run.id} started in INTAKE ({profile.value}).", run.id)

    def _status(self, rest: list[str]) -> CommandResult:
        self._expect_no_args("status", rest)
        run = self.repository.get_run(self.active_run_id())
        pending_risks = sum(
            item.accepted_risk is None for item in self.repository.list_risk_suggestions(run.id)
        )
        return CommandResult(
            True,
            f"Run: {run.id}\nProfile: {run.profile.value}\nStage: {run.stage.value}\n"
            f"Status: {run.status.value}\nPending risk suggestions: {pending_risks}",
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
        return CommandResult(True, text or "No Crucible runs found.")

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

    @staticmethod
    def _command_options(rest: list[str], allowed: frozenset[str]) -> dict[str, str | bool]:
        options: dict[str, str | bool] = {}
        index = 0
        while index < len(rest):
            key = rest[index]
            if key not in allowed or key in options:
                raise ValueError(f"unknown or duplicate policy option: {key}")
            if key == "--global":
                options[key] = True
                index += 1
                continue
            if index + 1 >= len(rest):
                raise ValueError(f"policy option requires a value: {key}")
            options[key] = rest[index + 1]
            index += 2
        return options

    def _policy(self, rest: list[str]) -> CommandResult:
        if rest and rest[0] == "suggest-risk":
            options = self._command_options(
                rest[1:], frozenset({"--text", "--files", "--command", "--format"})
            )
            text_value = options.get("--text")
            if not isinstance(text_value, str) or not text_value.strip():
                raise ValueError("policy suggest-risk requires --text")
            files_value = str(options.get("--files", ""))
            files = tuple(item.strip() for item in files_value.split(",") if item.strip())
            suggestion = RiskService(self.repository).suggest(
                self.active_run_id(), text=text_value, files=files,
                command=str(options["--command"]) if "--command" in options else None,
                now=utc_now(),
            )
            payload = {
                "id": suggestion.id,
                "suggested_risk": suggestion.suggested_risk.value,
                "reasons": list(suggestion.reasons),
                "decision_required": True,
            }
            format_value = str(options.get("--format", "human"))
            if format_value == "json":
                text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            elif format_value == "human":
                text = (
                    f"Suggested risk: {suggestion.suggested_risk.value}\n"
                    f"Reasons: {', '.join(suggestion.reasons)}\n"
                    f"Suggestion ID: {suggestion.id}\nHuman decision: pending"
                )
            else:
                raise ValueError("policy suggest-risk --format must be human or json")
            return CommandResult(True, text, self.active_run_id())
        if len(rest) >= 2 and rest[:2] == ["risk", "decide"]:
            if len(rest) < 3:
                raise ValueError(
                    "usage: policy risk decide <suggestion-id> --risk <level> [--reason <text>]"
                )
            options = self._command_options(rest[3:], frozenset({"--risk", "--reason"}))
            risk_value = options.get("--risk")
            if not isinstance(risk_value, str):
                raise ValueError("policy risk decide requires --risk")
            decided = RiskService(self.repository).decide_human(
                rest[2], accepted_risk=RiskLevel(risk_value),
                actor=self.context.actor, source=self.context.source,
                rationale=str(options["--reason"]) if "--reason" in options else None,
                now=utc_now(),
            )
            assert decided.accepted_risk is not None
            return CommandResult(
                True, f"Risk suggestion decided: {decided.accepted_risk.value}.",
                self.active_run_id(),
            )
        if rest and rest[0] == "explain":
            options = self._command_options(
                rest[1:], frozenset({"--event", "--tool", "--args-json", "--format"})
            )
            event = options.get("--event")
            tool = options.get("--tool")
            if (event is None) == (tool is None):
                raise ValueError("policy explain requires exactly one of --event or --tool")
            format_value = str(options.get("--format", "human"))
            if format_value not in {"human", "json"}:
                raise ValueError("policy explain --format must be human or json")
            if event is not None:
                try:
                    sequence = int(str(event))
                except ValueError as exc:
                    raise ValueError("policy explain --event must be a positive integer") from exc
                if sequence < 1:
                    raise ValueError("policy explain --event must be a positive integer")
                payload = self.explain_policy(event_sequence=sequence)
            else:
                raw_json = str(options.get("--args-json", "{}"))
                if len(raw_json) > 16_384:
                    raise ValueError("policy explain --args-json exceeds 16384 characters")
                try:
                    parsed = json.loads(raw_json)
                except json.JSONDecodeError as exc:
                    raise ValueError("policy explain --args-json must be valid JSON") from exc
                if not isinstance(parsed, dict):
                    raise ValueError("policy explain --args-json root must be an object")
                payload = self.explain_policy(tool_name=str(tool), args=parsed)
            return CommandResult(
                True, self._render_policy_explanation(payload, format_value), self.active_run_id()
            )
        if len(rest) < 2 or rest[0] != "waivers":
            raise ValueError("usage: policy <explain|waivers>")
        action = rest[1]
        service = WaiverService(self.repository)
        run_id = self.active_run_id()
        if action == "list":
            if len(rest) != 2:
                raise ValueError("usage: policy waivers list")
            now = utc_now()
            service.expire_due(now)
            waivers = service.list_applicable(run_id)
            if not waivers:
                return CommandResult(True, "No applicable policy waivers.", run_id)
            lines = []
            for waiver in waivers:
                status = "revoked" if waiver.revoked_at else (
                    "expired" if waiver.expires_at <= now else "active"
                )
                lines.append(
                    f"{waiver.name} {waiver.rule_key} {status} expires={waiver.expires_at}"
                )
            return CommandResult(True, "\n".join(lines), run_id)
        if action == "create":
            if len(rest) < 4:
                raise ValueError(
                    "usage: policy waivers create <name> <rule-key> --expires <time> "
                    "--reason <text> [scope options]"
                )
            options = self._command_options(
                rest[4:],
                frozenset({
                    "--expires", "--reason", "--tool", "--command-sha256", "--path",
                    "--profile", "--stage", "--global",
                }),
            )
            expires = options.get("--expires")
            reason = options.get("--reason")
            if not isinstance(expires, str) or not isinstance(reason, str):
                raise ValueError("policy waiver creation requires --expires and --reason")
            profile_value = options.get("--profile")
            stage_value = options.get("--stage")
            waiver = service.create_human(
                run_id=None if options.get("--global") else run_id,
                name=rest[2], rule_key=rest[3], rationale=reason,
                actor=self.context.actor, source=self.context.source,
                created_at=utc_now(), expires_at=expires,
                tool_name=str(options["--tool"]) if "--tool" in options else None,
                command_sha256=(
                    str(options["--command-sha256"])
                    if "--command-sha256" in options else None
                ),
                path_scope=str(options["--path"]) if "--path" in options else None,
                profile=RunProfile(str(profile_value)) if profile_value is not None else None,
                stage=RunStage(str(stage_value)) if stage_value is not None else None,
            )
            return CommandResult(True, f"Policy waiver created: {waiver.name}.", run_id)
        if action == "revoke":
            if len(rest) < 3:
                raise ValueError("usage: policy waivers revoke <name> --reason <text>")
            options = self._command_options(rest[3:], frozenset({"--reason"}))
            reason = options.get("--reason")
            if not isinstance(reason, str):
                raise ValueError("policy waiver revocation requires --reason")
            waiver = service.revoke_human(
                rest[2], actor=self.context.actor, source=self.context.source,
                reason=reason, now=utc_now(),
            )
            return CommandResult(True, f"Policy waiver revoked: {waiver.name}.", run_id)
        raise ValueError("usage: policy waivers <list|create|revoke>")

    def _complete(self, rest: list[str]) -> CommandResult:
        self._expect_no_args("complete", rest)
        run_id = self.active_run_id()
        run = self.run_service.transition(
            run_id, RunStage.COMPLETE, self._facts(run_id), reason="human completion command"
        )
        return CommandResult(True, f"Run {run.id} is COMPLETE.", run.id)
