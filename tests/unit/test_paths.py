from pathlib import Path

import pytest

from crucible_agent.paths import ProjectPaths, safe_project_relative


def test_project_paths_are_local_and_deterministic(tmp_path: Path) -> None:
    paths = ProjectPaths(tmp_path)
    assert paths.config == tmp_path / ".crucible" / "config.yaml"
    assert paths.database == tmp_path / ".crucible" / "state" / "crucible.db"
    assert paths.run_directory("run-123") == tmp_path / ".crucible" / "runs" / "run-123"


@pytest.mark.parametrize(
    "value",
    ["../outside", "runs/../../outside", r"C:\outside", r"\\server\share\outside", "/outside"],
)
def test_project_relative_path_rejects_traversal_and_absolute_forms(value: str) -> None:
    with pytest.raises(ValueError):
        safe_project_relative(value)


def test_project_relative_path_accepts_windows_separators() -> None:
    assert safe_project_relative(r"artifacts\runs") == Path("artifacts/runs")
