"""Unit tests for the evidence package builder."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from hardproof.services.packages import EvidencePackageBuilder, PackageManifest


class FakeReportService:
    """Minimal stand-in: export() writes completion files into the run directory."""

    def __init__(self, run_directory: Path) -> None:
        self.run_directory = Path(run_directory)
        self.export_calls: list[tuple[str, str]] = []

    def export(self, run_id: str, *, destination=None, format: str = "both") -> dict[str, Path]:
        self.export_calls.append((run_id, format))
        md = self.run_directory / "completion.md"
        js = self.run_directory / "completion.json"
        md.write_text("# Completion report\n", encoding="utf-8")
        js.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
        return {"markdown": md, "json": js}


def _run_dir(tmp_path: Path) -> Path:
    run = tmp_path / "run-1"
    (run / "evidence").mkdir(parents=True)
    (run / "evidence" / "check.log").write_text("check ok\n", encoding="utf-8")
    return run


def test_build_zip_creates_archive_and_manifest(tmp_path: Path) -> None:
    run = _run_dir(tmp_path)
    service = EvidencePackageBuilder(FakeReportService(run), run)
    archive, manifest = service.build("run-1")

    assert archive == run / "evidence-run-1.zip"
    assert archive.exists()
    assert isinstance(manifest, PackageManifest)
    assert manifest.run_id == "run-1"
    assert manifest.format == "zip"
    assert manifest.files == ["completion.json", "completion.md", "evidence/check.log"]
    assert manifest.total_bytes > 0
    assert len(manifest.sha256) == 64

    manifest_path = run / "evidence-run-1.manifest.json"
    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["run_id"] == "run-1"

    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        assert "completion.json" in names
        assert "completion.md" in names
        assert "evidence/check.log" in names
        # Recompute digest: archive bytes must match the manifest sha256
        assert manifest.sha256 == __import__("hashlib").sha256(archive.read_bytes()).hexdigest()


def test_build_targz_variant(tmp_path: Path) -> None:
    run = _run_dir(tmp_path)
    service = EvidencePackageBuilder(FakeReportService(run), run)
    archive, manifest = service.build("run-1", format="tar.gz")

    assert archive.name == "evidence-run-1.tar.gz"
    assert archive.exists()
    assert manifest.format == "tar.gz"
    assert manifest.files == ["completion.json", "completion.md", "evidence/check.log"]


def test_build_skips_export_when_both_disabled(tmp_path: Path) -> None:
    run = _run_dir(tmp_path)
    fake = FakeReportService(run)
    service = EvidencePackageBuilder(fake, run)
    archive, manifest = service.build("run-1", include_json=False, include_markdown=False)

    assert fake.export_calls == []  # no report export requested
    assert manifest.files == ["evidence/check.log"]
    assert archive.exists()


def test_build_handles_missing_completion_files(tmp_path: Path) -> None:
    run = tmp_path / "run-2"
    (run / "evidence").mkdir(parents=True)
    (run / "evidence" / "check.log").write_text("check ok\n", encoding="utf-8")
    # No completion.json / completion.md on disk; export() fake still writes them,
    # but simulate a report service that does not materialize them.
    class NoWriteReportService(FakeReportService):
        def export(self, run_id: str, *, destination=None, format: str = "both") -> dict[str, Path]:
            self.export_calls.append((run_id, format))
            return {}

    service = EvidencePackageBuilder(NoWriteReportService(run), run)
    archive, manifest = service.build("run-2")

    # Only the evidence log lands in the archive; no crash on missing reports.
    assert manifest.files == ["evidence/check.log"]
    assert archive.exists()
