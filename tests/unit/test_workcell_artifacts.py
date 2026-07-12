from __future__ import annotations

import json
from pathlib import Path

import pytest

from hardproof.services.workcell_artifacts import (
    WorkcellArtifactStore,
    validate_child_result,
)


def result_payload() -> dict[str, object]:
    return {
        "contract_version": 1,
        "run_id": "run-1",
        "task_id": "task-1",
        "attempt_id": "attempt-1",
        "child_session_id": "child-1",
        "reported_status": "succeeded",
        "summary": "Implemented safely",
        "changed_paths": ["hardproof/module.py"],
        "commands_executed": ["python -m pytest"],
        "tests_executed": [{"name": "unit", "outcome": "passed"}],
        "acceptance_completed": ["tests pass"],
        "artifacts_produced": [],
        "remaining_blockers": [],
        "policy_blockers": [],
        "approval_blockers": [],
        "evidence_references": [],
        "recommended_next_action": "validate result",
    }


def test_store_writes_deterministic_bounded_json_under_attempt(tmp_path: Path) -> None:
    store = WorkcellArtifactStore(tmp_path, "run-1", "task-1", 1, maximum_bytes=1024)
    path = store.write_json("context.json", {"token": "secret-value", "files": ["a.py"]})
    assert path == tmp_path / ".hardproof" / "runs" / "run-1" / "tasks" / "task-1" / "attempts" / "1" / "context.json"
    assert json.loads(path.read_text(encoding="utf-8"))["token"] == "[REDACTED]"
    with pytest.raises(ValueError, match="size limit"):
        store.write_text("brief.md", "x" * 1025)


def test_store_rejects_traversal_and_symlink_escape(tmp_path: Path) -> None:
    store = WorkcellArtifactStore(tmp_path, "run-1", "task-1", 1)
    with pytest.raises(ValueError, match="invalid Workcell artifact path"):
        store.write_text("../escape.txt", "no")
    base = store.attempt_directory
    base.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = base / "linked"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="symlink"):
        store.write_text("linked/escape.txt", "no")


def test_child_result_validation_fails_closed_on_identity_or_path_mismatch(tmp_path: Path) -> None:
    payload = result_payload()
    result = validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)
    assert result.reported_status == "succeeded"
    payload["attempt_id"] = "attempt-other"
    with pytest.raises(ValueError, match="attempt identity"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)
    payload = result_payload()
    payload["changed_paths"] = ["../escape.py"]
    with pytest.raises(ValueError, match="path"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)


def test_child_result_redacts_secret_bearing_text(tmp_path: Path) -> None:
    payload = result_payload()
    payload["summary"] = "token=not-for-storage"
    result = validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)
    assert result.summary == "token=[REDACTED]"


def test_store_rejects_invalid_identity_for_run_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid Workcell artifact identity"):
        WorkcellArtifactStore(tmp_path, "../escape", "task-1", 1)
    with pytest.raises(ValueError, match="invalid Workcell artifact identity"):
        WorkcellArtifactStore(tmp_path, "run-1", "../escape", 1)


def test_store_rejects_negative_attempt_number(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid Workcell artifact bounds"):
        WorkcellArtifactStore(tmp_path, "run-1", "task-1", 0)


def test_store_rejects_non_string_content(tmp_path: Path) -> None:
    store = WorkcellArtifactStore(tmp_path, "run-1", "task-1", 1)
    with pytest.raises(TypeError, match="must be text"):
        store.write_text("data.json", 42)  # type: ignore


def test_validate_child_result_rejects_oversized_payload(tmp_path: Path) -> None:
    payload = result_payload()
    with pytest.raises(ValueError, match="exceeds size limit"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path, maximum_bytes=1)


def test_validate_child_result_rejects_missing_fields(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        validate_child_result({}, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)


def test_validate_child_result_rejects_unsupported_contract(tmp_path: Path) -> None:
    payload = result_payload()
    payload["contract_version"] = 99
    with pytest.raises(ValueError, match="contract version"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)


def test_validate_child_result_rejects_invalid_status(tmp_path: Path) -> None:
    payload = result_payload()
    payload["reported_status"] = "unknown"
    with pytest.raises(ValueError, match="reported status is invalid"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)


def test_validate_child_result_rejects_malformed_tests(tmp_path: Path) -> None:
    payload = result_payload()
    payload["tests_executed"] = "not a list"
    with pytest.raises(ValueError, match="tests_executed"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)


def test_validate_child_result_rejects_non_dict_payload(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be an object"):
        validate_child_result("not a dict", run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)


def test_validate_child_result_rejects_malformed_changed_paths(tmp_path: Path) -> None:
    payload = result_payload()
    payload["changed_paths"] = "not a list"
    with pytest.raises(ValueError, match="changed_paths must be a list"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)


def test_validate_child_result_rejects_empty_summary(tmp_path: Path) -> None:
    payload = result_payload()
    payload["summary"] = ""
    with pytest.raises(ValueError, match="summary must be non-empty"):
        validate_child_result(payload, run_id="run-1", task_id="task-1", attempt_id="attempt-1", child_session_id="child-1", project_root=tmp_path)
