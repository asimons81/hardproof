from pathlib import Path

import pytest

from hardproof.domain.enums import ArtifactKind, RunProfile
from hardproof.domain.models import Run
from hardproof.services.artifacts import ArtifactService
from hardproof.storage.database import Database
from hardproof.storage.migrations import migrate
from hardproof.storage.repository import RunRepository


def service_for(tmp_path: Path) -> tuple[ArtifactService, Run]:
    database = Database(tmp_path / "state" / "hardproof.db")
    migrate(database)
    repository = RunRepository(database)
    run = Run.create(str(tmp_path), "artifact test", RunProfile.STANDARD)
    repository.create_run(run)
    return ArtifactService(repository, tmp_path / "runs" / run.id), run


def test_artifact_write_is_recorded_with_content_hash(tmp_path: Path) -> None:
    service, run = service_for(tmp_path)
    artifact = service.write(run.id, ArtifactKind.DESIGN, "design.md", "# Design\n\nSafe design.\n")
    assert (tmp_path / "runs" / run.id / "design.md").read_text(encoding="utf-8") == "# Design\n\nSafe design.\n"
    assert len(artifact.sha256) == 64
    assert service.repository.list_artifacts(run.id) == (artifact,)


@pytest.mark.parametrize("path", ["../escape.md", "/absolute.md", r"C:\escape.md"])
def test_artifact_path_cannot_escape_run_directory(tmp_path: Path, path: str) -> None:
    service, run = service_for(tmp_path)
    with pytest.raises(ValueError, match="artifact path"):
        service.write(run.id, ArtifactKind.DESIGN, path, "content")


def test_failed_repository_write_does_not_leave_new_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    service, run = service_for(tmp_path)

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(service.repository, "add_artifact", fail)
    with pytest.raises(RuntimeError):
        service.write(run.id, ArtifactKind.DESIGN, "design.md", "content")
    assert not (tmp_path / "runs" / run.id / "design.md").exists()
