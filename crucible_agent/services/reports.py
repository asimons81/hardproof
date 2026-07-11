"""Deterministic secret-safe Markdown and JSON run reports."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from crucible_agent.domain.enums import ApprovalGate, ArtifactKind, EvidenceStatus, TaskStatus
from crucible_agent.services.evidence import evidence_with_freshness
from crucible_agent.storage.repository import RunRepository


_SECRET = re.compile(
    r"(?i)\b(api[_-]?key|token|password|authorization|cookie|secret)\s*[:=]\s*([^\s,;]+)"
)


def _redact(value: str) -> str:
    return _SECRET.sub(lambda match: f"{match.group(1)}=[REDACTED]", value)


def _safe(value: Any) -> Any:
    if isinstance(value, str):
        return _redact(value)
    if isinstance(value, list):
        return [_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    return value


class ReportService:
    def __init__(
        self,
        repository: RunRepository,
        project_root: str | Path,
        run_directory: str | Path,
    ) -> None:
        self.repository = repository
        self.project_root = Path(project_root).resolve()
        self.run_directory = Path(run_directory).resolve()

    def _files_changed(self) -> list[str]:
        tracked = subprocess.run(
            ["git", "-C", str(self.project_root), "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, check=False, timeout=30,
        )
        untracked = subprocess.run(
            ["git", "-C", str(self.project_root), "ls-files", "--others", "--exclude-standard", "-z"],
            capture_output=True, check=False, timeout=30,
        )
        paths = set(tracked.stdout.splitlines() if tracked.returncode == 0 else [])
        if untracked.returncode == 0:
            paths.update(
                item.decode("utf-8", errors="replace")
                for item in untracked.stdout.split(b"\0") if item
            )
        return sorted(path.replace("\\", "/") for path in paths if path)

    def build_payload(self, run_id: str) -> dict[str, Any]:
        run = self.repository.get_run(run_id)
        events = self.repository.list_events(run_id)
        artifacts = self.repository.list_artifacts(run_id)
        decisions = self.repository.list_decisions(run_id)
        tasks = self.repository.list_tasks(run_id)
        approvals = self.repository.list_approvals(run_id)
        checks = self.repository.list_verification_checks(run_id)
        evidence = evidence_with_freshness(
            self.repository.list_evidence(run_id), self.project_root
        )
        latest_evidence: dict[str, Any] = {}
        for item in sorted(evidence, key=lambda record: (record.completed_at, record.id)):
            latest_evidence[item.check_name] = item
        checks_by_name = {check.name: check for check in checks}
        check_names = sorted(set(checks_by_name) | set(latest_evidence))
        stages = [
            {
                "at": event.created_at,
                "from": event.payload.get("from_stage"),
                "to": event.payload.get("to_stage", event.payload.get("stage")),
                "reason": event.payload.get("reason"),
            }
            for event in events
            if event.event_type in {"run_created", "stage_transitioned"}
        ]
        review_artifacts = [item for item in artifacts if item.kind is ArtifactKind.REVIEW]
        review_approved = any(event.event_type == "review_approved" for event in events)
        learning_artifacts = [item for item in artifacts if item.kind is ArtifactKind.LEARNING]
        learning_skipped = [event for event in events if event.event_type == "learning_skipped"]
        payload = {
            "schema_version": 1,
            "run": {
                "id": run.id,
                "request": run.request,
                "profile": run.profile.value,
                "stage": run.stage.value,
                "status": run.status.value,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "completed_at": run.completed_at,
            },
            "stage_history": stages,
            "artifacts": [
                {"kind": item.kind.value, "path": item.path, "sha256": item.sha256}
                for item in sorted(artifacts, key=lambda value: (value.kind.value, value.path))
            ],
            "approved_decisions": [
                {"key": item.key, "question": item.question, "choice": item.choice, "rationale": item.rationale}
                for item in sorted(decisions, key=lambda value: value.key)
                if item.status.lower() in {"accepted", "approved"}
            ],
            "tasks_completed": [
                {
                    "key": item.task_key, "title": item.title,
                    "acceptance_notes": item.acceptance_notes, "files": list(item.files),
                }
                for item in sorted(tasks, key=lambda value: value.task_key)
                if item.status is TaskStatus.COMPLETED
            ],
            "files_changed": self._files_changed(),
            "review": {
                "outcome": "approved" if review_approved else (
                    "recorded; approval outcome not recorded" if review_artifacts else "not recorded"
                ),
                "artifacts": [item.path for item in review_artifacts],
            },
            "verification_checks": [
                {
                    "name": name,
                    "command": checks_by_name[name].command if name in checks_by_name else latest_evidence[name].command,
                    "required": checks_by_name[name].required if name in checks_by_name else False,
                    "status": latest_evidence[name].status.value if name in latest_evidence else "missing",
                    "exit_code": latest_evidence[name].exit_code if name in latest_evidence else None,
                    "output_path": latest_evidence[name].output_path if name in latest_evidence else None,
                }
                for name in check_names
            ],
            "evidence_freshness": "fresh" if evidence and all(
                item.status is EvidenceStatus.PASSED for item in latest_evidence.values()
            ) else ("missing" if not evidence else "failed, indeterminate, or stale"),
            "waivers": [
                {"actor": item.actor, "source": item.source, "reason": item.reason}
                for item in approvals if item.gate is ApprovalGate.WAIVER
            ],
            "remaining_risks": [item.path for item in artifacts if item.kind is ArtifactKind.RISK],
            "rollback_instructions": "See completion artifact" if any(
                item.kind is ArtifactKind.COMPLETION for item in artifacts
            ) else "No structured rollback instructions recorded",
            "learning": (
                {"status": "captured", "artifacts": [item.path for item in learning_artifacts]}
                if learning_artifacts else {
                    "status": "skipped" if learning_skipped else "not recorded",
                    "reason": learning_skipped[-1].payload.get("reason") if learning_skipped else None,
                }
            ),
        }
        return cast(dict[str, Any], _safe(payload))

    @staticmethod
    def _items(values: list[str]) -> str:
        return "\n".join(f"- {value}" for value in values) if values else "- None recorded"

    def render_markdown(self, run_id: str) -> str:
        data = self.build_payload(run_id)
        run = data["run"]
        history = [
            f"{item['at']}: {item.get('from') or 'START'} -> {item.get('to') or 'UNKNOWN'}"
            + (f" ({item['reason']})" if item.get("reason") else "")
            for item in data["stage_history"]
        ]
        artifacts = [
            f"{item['kind']}: [{item['path']}]({item['path']}) sha256={item['sha256']}"
            for item in data["artifacts"]
        ]
        decisions = [
            f"{item['key']}: {item['choice']} — {item['rationale']}"
            for item in data["approved_decisions"]
        ]
        tasks = [
            f"{item['key']}: {item['title']} — {item.get('acceptance_notes') or 'no acceptance notes'}"
            for item in data["tasks_completed"]
        ]
        checks = [
            f"{item['name']}: {item['status']} exit={item['exit_code']}"
            + (f" output=[{item['output_path']}]({item['output_path']})" if item.get("output_path") else "")
            for item in data["verification_checks"]
        ]
        waivers = [
            f"{item['reason']} — {item['actor']} via {item['source']}" for item in data["waivers"]
        ]
        learning = data["learning"]
        learning_text = learning["status"] + (
            f": {learning.get('reason')}" if learning.get("reason") else ""
        )
        sections = [
            "# Crucible Completion Report",
            "## Request", str(run["request"]),
            "## Profile", str(run["profile"]),
            "## Final status", f"Stage: {run['stage']}\n\nStatus: {run['status']}",
            "## Stage history", self._items(history),
            "## Artifacts", self._items(artifacts),
            "## Approved decisions", self._items(decisions),
            "## Tasks completed", self._items(tasks),
            "## Files changed", self._items(data["files_changed"]),
            "## Review outcome", f"{data['review']['outcome']}\n\n{self._items(data['review']['artifacts'])}",
            "## Verification checks", self._items(checks),
            "## Evidence freshness", str(data["evidence_freshness"]),
            "## Waivers", self._items(waivers),
            "## Remaining risks", self._items(data["remaining_risks"]),
            "## Rollback instructions", str(data["rollback_instructions"]),
            "## Learning captured or skipped", learning_text,
            "## Run timestamps",
            f"Created: {run['created_at']}\n\nUpdated: {run['updated_at']}\n\nCompleted: {run['completed_at'] or 'not completed'}",
        ]
        return "\n\n".join(sections) + "\n"

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, path)

    def export(
        self,
        run_id: str,
        *,
        destination: str | Path | None = None,
        format: str = "both",
    ) -> dict[str, Path]:
        if format not in {"markdown", "json", "both"}:
            raise ValueError("format must be markdown, json, or both")
        supplied = Path(destination).expanduser().resolve() if destination is not None else None
        if supplied is None:
            markdown_path = self.run_directory / "completion.md"
            json_path = self.run_directory / "completion.json"
        elif supplied.suffix.lower() in {".md", ".json"}:
            base = supplied.with_suffix("")
            markdown_path = supplied if supplied.suffix.lower() == ".md" else base.with_suffix(".md")
            json_path = supplied if supplied.suffix.lower() == ".json" else base.with_suffix(".json")
        else:
            markdown_path = supplied / "completion.md"
            json_path = supplied / "completion.json"
        written: dict[str, Path] = {}
        if format in {"markdown", "both"}:
            self._write(markdown_path, self.render_markdown(run_id))
            written["markdown"] = markdown_path
        if format in {"json", "both"}:
            content = json.dumps(self.build_payload(run_id), indent=2, sort_keys=True) + "\n"
            self._write(json_path, content)
            written["json"] = json_path
        return written
