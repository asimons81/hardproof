from __future__ import annotations

import json
import subprocess
from pathlib import Path

from crucible_agent.domain.enums import (
    ApprovalGate,
    ArtifactKind,
    EvidenceStatus,
    RiskLevel,
    RunProfile,
    TaskStatus,
)
from crucible_agent.domain.models import Approval, Artifact, Decision, Evidence, Run, Task
from crucible_agent.services.reports import ReportService
from crucible_agent.storage.database import Database
from crucible_agent.storage.migrations import migrate
from crucible_agent.storage.repository import RunRepository


NOW = "2026-07-11T10:00:00Z"


def setup(tmp_path: Path) -> tuple[ReportService, RunRepository, Run]:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / ".gitignore").write_text(".crucible/\n", encoding="utf-8")
    (tmp_path / "code.py").write_text("VALUE=1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".gitignore", "code.py"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "initial"], check=True)
    database = Database(tmp_path / ".crucible/state/crucible.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "Build feature token=never-export", RunProfile.STANDARD, now=NOW)
    repository.create_run(run)
    repository.add_artifact(Artifact(
        "artifact-design", run.id, ArtifactKind.DESIGN, "design.md", "a" * 64, NOW
    ))
    repository.add_artifact(Artifact(
        "artifact-review", run.id, ArtifactKind.REVIEW, "review.md", "b" * 64, NOW
    ))
    repository.upsert_decision(Decision(
        "decision-1", run.id, "storage", "Which?", "SQLite", "local", "accepted", NOW
    ))
    repository.add_approval(Approval(
        "waiver-1", run.id, ApprovalGate.WAIVER, "person", "slash", "review: known risk", NOW
    ))
    repository.add_task(Task(
        "task-1", run.id, "T1", "Implement", "change", TaskStatus.COMPLETED,
        RiskLevel.LOW, (), ("passes",), ("code.py",), NOW, NOW, "passed",
    ))
    repository.add_evidence(Evidence(
        "evidence-1", run.id, "tests", "python -m pytest", 0, EvidenceStatus.PASSED,
        subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip(),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        ".crucible/runs/evidence.log", "c" * 64, NOW, NOW,
    ))
    return ReportService(repository, tmp_path, tmp_path / ".crucible/runs" / run.id), repository, run


def test_completion_markdown_has_every_required_section_and_no_secret(tmp_path: Path) -> None:
    reports, _, run = setup(tmp_path)
    markdown = reports.render_markdown(run.id)
    for heading in (
        "## Request", "## Profile", "## Final status", "## Stage history",
        "## Artifacts", "## Approved decisions", "## Tasks completed",
        "## Files changed", "## Review outcome", "## Verification checks",
        "## Evidence freshness", "## Waivers", "## Remaining risks",
        "## Rollback instructions", "## Learning captured or skipped", "## Run timestamps",
    ):
        assert heading in markdown
    assert "never-export" not in markdown
    assert "design.md" in markdown


def test_json_export_has_schema_and_omits_internal_record_ids(tmp_path: Path) -> None:
    reports, _, run = setup(tmp_path)
    payload = reports.build_payload(run.id)
    assert payload["schema_version"] == 1
    assert payload["run"]["id"] == run.id
    serialized = json.dumps(payload)
    assert "artifact-design" not in serialized
    assert "decision-1" not in serialized
    assert "evidence-1" not in serialized


def test_both_exports_are_reproducible_for_unchanged_state(tmp_path: Path) -> None:
    reports, _, run = setup(tmp_path)
    first = reports.export(run.id, format="both")
    first_bytes = {name: path.read_bytes() for name, path in first.items()}
    second = reports.export(run.id, format="both")
    assert {name: path.read_bytes() for name, path in second.items()} == first_bytes
    assert set(first) == {"markdown", "json"}


def test_explicit_destination_and_relative_evidence_links(tmp_path: Path) -> None:
    reports, _, run = setup(tmp_path)
    destination = tmp_path / "exports" / "result.md"
    paths = reports.export(run.id, destination=destination, format="markdown")
    assert paths == {"markdown": destination}
    text = destination.read_text(encoding="utf-8")
    assert ".crucible/runs/evidence.log" in text
