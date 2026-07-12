"""Bounded, atomic Workcell handoff artifacts and child-result validation."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from hardproof.paths import safe_project_relative


_SECRET_KEY = re.compile(r"(?i)(api[_-]?key|token|password|authorization|cookie|secret)")
_SECRET_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|authorization|cookie|secret)\s*[:=]\s*([^\s,;]+)"
)
_REPORTED_STATUSES = frozenset({"succeeded", "blocked", "failed", "cancelled"})
_CONTRACT_VERSION = 1


def _redact(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): "[REDACTED]" if _SECRET_KEY.search(str(key)) else _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _redact_text(value: str) -> str:
    return _SECRET_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


@dataclass(frozen=True, slots=True)
class ChildResult:
    contract_version: int
    run_id: str
    task_id: str
    attempt_id: str
    child_session_id: str
    reported_status: str
    summary: str
    changed_paths: tuple[str, ...]
    commands_executed: tuple[str, ...]
    tests_executed: tuple[dict[str, object], ...]
    artifacts_produced: tuple[str, ...]
    remaining_blockers: tuple[str, ...]
    policy_blockers: tuple[str, ...]
    approval_blockers: tuple[str, ...]
    evidence_references: tuple[str, ...]
    recommended_next_action: str


class WorkcellArtifactStore:
    """Write only attempt-local artifacts, rejecting traversal and symlink escape."""

    def __init__(
        self, project_root: str | Path, run_id: str, task_id: str, attempt_number: int,
        *, maximum_bytes: int = 262_144,
    ) -> None:
        if attempt_number < 1 or maximum_bytes < 1:
            raise ValueError("invalid Workcell artifact bounds")
        for value in (run_id, task_id):
            if not value or any(char in value for char in "/\\") or value in {".", ".."}:
                raise ValueError("invalid Workcell artifact identity")
        self.project_root = Path(project_root).resolve()
        self.maximum_bytes = maximum_bytes
        self.attempt_directory = (
            self.project_root / ".hardproof" / "runs" / run_id / "tasks" / task_id / "attempts" / str(attempt_number)
        )

    def _target(self, name: str | Path) -> Path:
        try:
            relative = safe_project_relative(name)
        except ValueError as exc:
            raise ValueError(f"invalid Workcell artifact path: {exc}") from exc
        self.attempt_directory.mkdir(parents=True, exist_ok=True)
        root = self.attempt_directory.resolve()
        current = self.attempt_directory
        for part in relative.parts[:-1]:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ValueError("invalid Workcell artifact path: symlink traversal is not allowed")
            current.mkdir(exist_ok=True)
            try:
                current.resolve().relative_to(root)
            except ValueError as exc:
                raise ValueError("invalid Workcell artifact path: path escapes attempt directory") from exc
        target = self.attempt_directory / relative
        if target.exists() and target.is_symlink():
            raise ValueError("invalid Workcell artifact path: symlink target is not allowed")
        try:
            target.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError("invalid Workcell artifact path: path escapes attempt directory") from exc
        return target

    def write_text(self, name: str | Path, content: str) -> Path:
        if not isinstance(content, str):
            raise TypeError("Workcell artifact content must be text")
        encoded = content.encode("utf-8")
        if len(encoded) > self.maximum_bytes:
            raise ValueError("Workcell artifact exceeds size limit")
        target = self._target(name)
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(encoded)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def write_json(self, name: str | Path, payload: object) -> Path:
        serialized = json.dumps(_redact(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return self.write_text(name, serialized + "\n")


def _strings(payload: object, name: str) -> tuple[str, ...]:
    if not isinstance(payload, list) or any(not isinstance(item, str) for item in payload):
        raise ValueError(f"child result {name} must be a list of strings")
    return tuple(payload)


def validate_child_result(
    payload: object,
    *,
    run_id: str,
    task_id: str,
    attempt_id: str,
    child_session_id: str,
    project_root: str | Path,
    maximum_bytes: int = 262_144,
) -> ChildResult:
    """Validate untrusted child output before authoritative state processing."""
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(encoded) > maximum_bytes:
        raise ValueError("child result exceeds size limit")
    if not isinstance(payload, dict):
        raise ValueError("child result must be an object")
    required = {
        "contract_version", "run_id", "task_id", "attempt_id", "child_session_id", "reported_status",
        "summary", "changed_paths", "commands_executed", "tests_executed", "artifacts_produced",
        "remaining_blockers", "policy_blockers", "approval_blockers", "evidence_references", "recommended_next_action",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"child result missing required fields: {', '.join(missing)}")
    if payload["contract_version"] != _CONTRACT_VERSION:
        raise ValueError("unsupported child result contract version")
    for key, expected, label in (
        ("run_id", run_id, "run"), ("task_id", task_id, "task"), ("attempt_id", attempt_id, "attempt"),
        ("child_session_id", child_session_id, "child session"),
    ):
        if payload[key] != expected:
            raise ValueError(f"child result {label} identity mismatch")
    status = payload["reported_status"]
    if status not in _REPORTED_STATUSES:
        raise ValueError("child result reported status is invalid")
    for name in ("summary", "recommended_next_action"):
        if not isinstance(payload[name], str) or not payload[name].strip():
            raise ValueError(f"child result {name} must be non-empty text")
    changed = _strings(payload["changed_paths"], "changed_paths")
    artifacts = _strings(payload["artifacts_produced"], "artifacts_produced")
    root = Path(project_root).resolve()
    for value in (*changed, *artifacts):
        relative = safe_project_relative(value)
        if (root / relative).resolve().is_relative_to(root) is False:
            raise ValueError("child result path escapes project root")
    tests = payload["tests_executed"]
    if not isinstance(tests, list) or any(not isinstance(item, dict) for item in tests):
        raise ValueError("child result tests_executed must be a list of objects")
    return ChildResult(
        _CONTRACT_VERSION, run_id, task_id, attempt_id, child_session_id, status,
        _redact_text(str(payload["summary"])), changed,
        tuple(_redact_text(value) for value in _strings(payload["commands_executed"], "commands_executed")),
        tuple({str(key): value for key, value in item.items()} for item in tests), artifacts,
        tuple(_redact_text(value) for value in _strings(payload["remaining_blockers"], "remaining_blockers")),
        tuple(_redact_text(value) for value in _strings(payload["policy_blockers"], "policy_blockers")),
        tuple(_redact_text(value) for value in _strings(payload["approval_blockers"], "approval_blockers")),
        tuple(_redact_text(value) for value in _strings(payload["evidence_references"], "evidence_references")),
        _redact_text(str(payload["recommended_next_action"])),
    )
