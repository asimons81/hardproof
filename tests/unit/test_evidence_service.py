from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from hardproof.domain.enums import EvidenceStatus, RunProfile
from hardproof.domain.models import Run, VerificationCheck
from hardproof.services.evidence import CommandResult, EvidenceService, HermesCommandRunner
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    (path / "code.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "code.py"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "initial"], check=True)
    exclude = path / ".git" / "info" / "exclude"
    exclude.write_text(exclude.read_text(encoding="utf-8") + "\n.hardproof/\n", encoding="utf-8")


@dataclass
class FakeRunner:
    result: CommandResult
    callback: Callable[[], None] | None = None

    def run(self, command: str, timeout_seconds: int) -> CommandResult:
        if self.callback:
            self.callback()
        return self.result


def service(
    tmp_path: Path,
    result: CommandResult,
    *,
    callback: Callable[[], None] | None = None,
    profile: RunProfile = RunProfile.STANDARD,
    checks: int = 1,
    maximum: int = 1_048_576,
) -> tuple[EvidenceService, RunRepository, Run]:
    git_repo(tmp_path)
    database = Database(tmp_path / ".hardproof/state/hardproof.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "verify", profile)
    repository.create_run(run)
    for index in range(checks):
        repository.add_verification_check(VerificationCheck(
            f"check-{index}", run.id, f"check-{index}", f"command-{index}", True, 60
        ))
    evidence = EvidenceService(
        repository, tmp_path, tmp_path / ".hardproof/runs" / run.id,
        FakeRunner(result, callback), maximum_stored_output_size=maximum,
    )
    return evidence, repository, run


def test_explicit_zero_exit_code_passes_and_stores_output(tmp_path: Path) -> None:
    evidence, repository, run = service(tmp_path, CommandResult(0, "all good"))
    result = evidence.verify(run.id)
    assert result[0].status is EvidenceStatus.PASSED
    output = tmp_path / result[0].output_path
    assert output.read_text(encoding="utf-8") == "all good"
    assert evidence.is_fresh(result[0])
    assert repository.list_evidence(run.id) == result


def test_nonzero_timeout_and_missing_exit_never_pass(tmp_path: Path) -> None:
    for index, command_result in enumerate((
        CommandResult(2, "failed"), CommandResult(None, "timeout", timed_out=True),
        CommandResult(None, "looks successful"),
    )):
        case = tmp_path / str(index)
        case.mkdir()
        evidence, _, run = service(case, command_result)
        status = evidence.verify(run.id)[0].status
        assert status in {EvidenceStatus.FAILED, EvidenceStatus.TIMED_OUT, EvidenceStatus.INDETERMINATE}


def test_workspace_change_during_command_is_indeterminate(tmp_path: Path) -> None:
    def change() -> None:
        (tmp_path / "code.py").write_text("VALUE = 2\n", encoding="utf-8")

    evidence, _, run = service(tmp_path, CommandResult(0, "passed"), callback=change)
    assert evidence.verify(run.id)[0].status is EvidenceStatus.INDETERMINATE


def test_edit_after_verification_makes_evidence_stale(tmp_path: Path) -> None:
    evidence, _, run = service(tmp_path, CommandResult(0, "passed"))
    record = evidence.verify(run.id)[0]
    (tmp_path / "code.py").write_text("VALUE = 3\n", encoding="utf-8")
    assert not evidence.is_fresh(record)
    assert evidence.freshness_status(record) is EvidenceStatus.STALE


def test_secret_redaction_and_bounded_large_output(tmp_path: Path) -> None:
    raw = "token=never-store-this\n" + "x" * 10_000
    evidence, repository, run = service(tmp_path, CommandResult(0, raw), maximum=1_000)
    record = evidence.verify(run.id)[0]
    stored = (tmp_path / record.output_path).read_text(encoding="utf-8")
    assert "never-store-this" not in stored
    assert len(stored.encode("utf-8")) <= 1_000
    assert "never-store-this" not in str(repository.list_events(run.id)[-1].payload)


def test_critical_profile_requires_distinct_multiple_checks(tmp_path: Path) -> None:
    evidence, _, run = service(
        tmp_path, CommandResult(0, "passed"), profile=RunProfile.CRITICAL, checks=2
    )
    records = evidence.verify(run.id)
    assert len(records) == 2
    assert evidence.required_evidence_blocker(run) is None


def test_unknown_check_is_rejected_without_execution(tmp_path: Path) -> None:
    evidence, _, run = service(tmp_path, CommandResult(0, "passed"))
    try:
        evidence.verify(run.id, checks=("not-configured",))
    except ValueError as exc:
        assert "not configured" in str(exc)
    else:
        raise AssertionError("unknown check executed")


def test_hermes_runner_dispatches_public_terminal_shape() -> None:
    class Context:
        def dispatch_tool(self, name: str, arguments: dict[str, object]) -> object:
            assert name == "terminal"
            assert arguments == {"command": "python -m pytest", "timeout": 45}
            return {"result": {"exit_code": 0, "stdout": "passed"}}

    result = HermesCommandRunner(Context()).run("python -m pytest", 45)
    assert result == CommandResult(0, "passed")


def test_empty_check_selection_is_rejected(tmp_path: Path) -> None:
    evidence, repository, run = service(tmp_path, CommandResult(0, "passed"))
    configured = repository.list_verification_checks(run.id)[0]
    with repository.database.connect() as connection, connection:
        connection.execute(
            "UPDATE verification_checks SET required = 0 WHERE id = ?", (configured.id,)
        )
    with pytest.raises(ValueError, match="no verification checks selected"):
        evidence.verify(run.id)


def test_all_required_false_executes_optional_checks(tmp_path: Path) -> None:
    evidence, repository, run = service(tmp_path, CommandResult(0, "passed"))
    configured = repository.list_verification_checks(run.id)[0]
    with repository.database.connect() as connection, connection:
        connection.execute(
            "UPDATE verification_checks SET required = 0 WHERE id = ?", (configured.id,)
        )
    assert len(evidence.verify(run.id, all_required=False)) == 1


def test_failed_evidence_is_not_fresh_and_remains_failed(tmp_path: Path) -> None:
    evidence, _, run = service(tmp_path, CommandResult(1, "failed"))
    record = evidence.verify(run.id)[0]
    assert not evidence.is_fresh(record)
    assert evidence.freshness_status(record) is EvidenceStatus.FAILED
