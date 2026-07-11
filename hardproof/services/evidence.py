"""Workspace-bound verification execution, storage, and freshness checks."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Protocol

from hardproof.domain.enums import EvidenceStatus
from hardproof.domain.models import Evidence, Run, VerificationCheck, new_id, utc_now
from hardproof.domain.snapshots import WorkspaceSnapshot, capture_git_snapshot
from hardproof.policy.profiles import policy_for
from hardproof.storage.repository import RunRepository


_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|token|password|authorization|cookie|secret)\s*[:=]\s*([^\s,;]+)"
)


@dataclass(frozen=True, slots=True)
class CommandResult:
    exit_code: int | None
    output: str
    timed_out: bool = False


class CommandRunner(Protocol):
    def run(self, command: str, timeout_seconds: int) -> CommandResult: ...


class HermesCommandRunner:
    def __init__(self, ctx: Any) -> None:
        self.ctx = ctx

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        raw = self.ctx.dispatch_tool(
            "terminal", {"command": command, "timeout": timeout_seconds}
        )
        return parse_terminal_result(raw)


def parse_terminal_result(raw: Any) -> CommandResult:
    """Parse known Hermes terminal shapes; unknown structure remains indeterminate."""
    value = raw
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return CommandResult(None, value)
    if not isinstance(value, dict):
        return CommandResult(None, "" if value is None else str(value))
    if isinstance(value.get("result"), dict):
        value = value["result"]
    exit_code: int | None = None
    for key in ("exit_code", "returncode", "exitCode"):
        candidate = value.get(key)
        if isinstance(candidate, int) and not isinstance(candidate, bool):
            exit_code = candidate
            break
    output = ""
    for key in ("output", "stdout", "content", "message"):
        candidate = value.get(key)
        if isinstance(candidate, str):
            output = candidate
            break
    timed_out = bool(value.get("timed_out") or value.get("timeout"))
    return CommandResult(exit_code, output, timed_out)


def redact_output(output: str) -> str:
    return _SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", output)


def _bounded_utf8(text: str, maximum_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= maximum_bytes:
        return text
    marker = b"\n[TRUNCATED]\n"
    available = max(0, maximum_bytes - len(marker))
    prefix = encoded[:available].decode("utf-8", errors="ignore").encode("utf-8")
    return (prefix + marker)[:maximum_bytes].decode("utf-8", errors="ignore")


def evidence_with_freshness(
    records: tuple[Evidence, ...], project_root: str | Path
) -> tuple[Evidence, ...]:
    if not records:
        return ()
    current = capture_git_snapshot(project_root)
    adjusted: list[Evidence] = []
    for record in records:
        stored = WorkspaceSnapshot(record.head_sha, record.diff_sha256, record.untracked_sha256)
        adjusted.append(
            record if stored.matches_workspace(current) or record.status is not EvidenceStatus.PASSED
            else replace(record, status=EvidenceStatus.STALE)
        )
    return tuple(adjusted)


class EvidenceService:
    def __init__(
        self,
        repository: RunRepository,
        project_root: str | Path,
        run_directory: str | Path,
        runner: CommandRunner,
        *,
        snapshotter: Callable[[str | Path], WorkspaceSnapshot] = capture_git_snapshot,
        maximum_stored_output_size: int = 1_048_576,
    ) -> None:
        self.repository = repository
        self.project_root = Path(project_root).resolve()
        self.run_directory = Path(run_directory).resolve()
        self.runner = runner
        self.snapshotter = snapshotter
        self.maximum_stored_output_size = maximum_stored_output_size

    def _selected_checks(
        self, run_id: str, checks: tuple[str, ...] | None, all_required: bool
    ) -> tuple[VerificationCheck, ...]:
        configured = self.repository.list_verification_checks(run_id)
        by_name = {item.name: item for item in configured}
        if checks:
            missing = sorted(set(checks) - set(by_name))
            if missing:
                raise ValueError(f"verification checks not configured: {', '.join(missing)}")
            return tuple(by_name[name] for name in checks)
        selected = tuple(item for item in configured if item.required) if all_required else configured
        if not selected:
            raise ValueError("no verification checks selected")
        return selected

    def verify(
        self,
        run_id: str,
        *,
        checks: tuple[str, ...] | None = None,
        all_required: bool = True,
        timeout_override: int | None = None,
    ) -> tuple[Evidence, ...]:
        records: list[Evidence] = []
        evidence_directory = self.run_directory / "evidence"
        evidence_directory.mkdir(parents=True, exist_ok=True)
        for check in self._selected_checks(run_id, checks, all_required):
            before = self.snapshotter(self.project_root)
            started = utc_now()
            result = self.runner.run(check.command, timeout_override or check.timeout_seconds)
            completed = utc_now()
            after = self.snapshotter(self.project_root)
            if before != after:
                status = EvidenceStatus.INDETERMINATE
            elif result.timed_out:
                status = EvidenceStatus.TIMED_OUT
            elif result.exit_code == 0:
                status = EvidenceStatus.PASSED
            elif result.exit_code is None:
                status = EvidenceStatus.INDETERMINATE
            else:
                status = EvidenceStatus.FAILED
            stored_output = _bounded_utf8(
                redact_output(result.output), self.maximum_stored_output_size
            )
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", check.name).strip("-") or "check"
            identifier = new_id("evidence")
            output = evidence_directory / f"{safe_name}-{identifier}.log"
            temporary = output.with_suffix(".tmp")
            temporary.write_text(stored_output, encoding="utf-8")
            os.replace(temporary, output)
            record = Evidence(
                identifier, run_id, check.name, check.command, result.exit_code, status,
                before.head_sha, before.diff_sha256, before.untracked_sha256,
                output.relative_to(self.project_root).as_posix(),
                hashlib.sha256(stored_output.encode("utf-8")).hexdigest(),
                started, completed,
            )
            self.repository.add_evidence(record)
            self.repository.append_event(
                run_id,
                "verification_recorded",
                {
                    "check_name": check.name,
                    "exit_code": result.exit_code,
                    "output_preview": stored_output[:500],
                    "output_sha256": record.output_sha256,
                    "status": status.value,
                },
            )
            records.append(record)
        return tuple(records)

    def is_fresh(self, evidence: Evidence) -> bool:
        if evidence.status is not EvidenceStatus.PASSED or evidence.exit_code != 0:
            return False
        current = self.snapshotter(self.project_root)
        return current.matches_workspace(WorkspaceSnapshot(
            evidence.head_sha, evidence.diff_sha256, evidence.untracked_sha256
        ))

    def freshness_status(self, evidence: Evidence) -> EvidenceStatus:
        return evidence.status if self.is_fresh(evidence) else (
            EvidenceStatus.STALE if evidence.status is EvidenceStatus.PASSED else evidence.status
        )

    def required_evidence_blocker(self, run: Run) -> str | None:
        adjusted = evidence_with_freshness(self.repository.list_evidence(run.id), self.project_root)
        latest: dict[str, Evidence] = {}
        for item in sorted(adjusted, key=lambda value: (value.completed_at, value.id)):
            latest[item.check_name] = item
        passed = sum(
            item.status is EvidenceStatus.PASSED and item.exit_code == 0
            for item in latest.values()
        )
        required = policy_for(run.profile).minimum_verification_checks
        if passed < required:
            return f"{required} fresh passing verification check{'s' if required != 1 else ''} required; found {passed}"
        return None
