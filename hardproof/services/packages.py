"""Evidence package builder: bundles evidence logs, reports, and artifacts into deterministic archives."""

from __future__ import annotations

import hashlib
import json
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from hardproof.services.reports import ReportService


@dataclass(frozen=True, slots=True)
class PackageManifest:
    run_id: str
    format: str
    files: list[str]
    total_bytes: int
    sha256: str


class EvidencePackageBuilder:
    def __init__(self, report_service: ReportService, run_directory: Path) -> None:
        self.report_service = report_service
        self.run_directory = Path(run_directory).resolve()

    def build(
        self,
        run_id: str,
        *,
        format: Literal["zip", "tar.gz"] = "zip",
        include_json: bool = True,
        include_markdown: bool = True,
    ) -> tuple[Path, PackageManifest]:
        evidence_dir = self.run_directory / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        json_path = self.run_directory / "completion.json"
        md_path = self.run_directory / "completion.md"

        if include_json or include_markdown:
            self.report_service.export(run_id, format="both")

        archive_name = f"evidence-{run_id}.{ 'zip' if format == 'zip' else 'tar.gz' }"
        archive_path = self.run_directory / archive_name

        files_added: list[str] = []
        total_bytes = 0

        if format == "zip":
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                if json_path.exists():
                    zf.write(json_path, json_path.name)
                    files_added.append(json_path.name)
                    total_bytes += json_path.stat().st_size
                if md_path.exists():
                    zf.write(md_path, md_path.name)
                    files_added.append(md_path.name)
                    total_bytes += md_path.stat().st_size
                for log in sorted(evidence_dir.glob("*.log")):
                    arcname = f"evidence/{log.name}"
                    zf.write(log, arcname)
                    files_added.append(arcname)
                    total_bytes += log.stat().st_size
        else:
            with tarfile.open(archive_path, "w:gz") as tf:
                if json_path.exists():
                    tf.add(json_path, json_path.name)
                    files_added.append(json_path.name)
                    total_bytes += json_path.stat().st_size
                if md_path.exists():
                    tf.add(md_path, md_path.name)
                    files_added.append(md_path.name)
                    total_bytes += md_path.stat().st_size
                for log in sorted(evidence_dir.glob("*.log")):
                    arcname = f"evidence/{log.name}"
                    tf.add(log, arcname)
                    files_added.append(arcname)
                    total_bytes += log.stat().st_size

        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        manifest = PackageManifest(run_id, format, files_added, total_bytes, digest)
        manifest_path = self.run_directory / f"evidence-{run_id}.manifest.json"
        manifest_path.write_text(json.dumps(manifest.__dict__, indent=2) + "\n", encoding="utf-8")

        return archive_path, manifest
