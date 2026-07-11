"""Atomic run-scoped artifact writing and hashing."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import uuid4

from hardproof.domain.enums import ArtifactKind
from hardproof.domain.models import Artifact, new_id, utc_now
from hardproof.paths import safe_project_relative
from hardproof.storage.repository import RunRepository


class ArtifactService:
    def __init__(self, repository: RunRepository, run_directory: str | Path) -> None:
        self.repository = repository
        self.run_directory = Path(run_directory).resolve()

    def _target(self, relative_path: str | Path) -> Path:
        try:
            relative = safe_project_relative(relative_path)
        except ValueError as exc:
            raise ValueError(f"invalid artifact path: {exc}") from exc
        target = (self.run_directory / relative).resolve()
        try:
            target.relative_to(self.run_directory)
        except ValueError as exc:
            raise ValueError("invalid artifact path: path escapes run directory") from exc
        return target

    def write(
        self,
        run_id: str,
        kind: ArtifactKind,
        relative_path: str | Path,
        content: str,
    ) -> Artifact:
        if not isinstance(content, str):
            raise TypeError("artifact content must be text")
        target = self._target(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        encoded = content.encode("utf-8")
        artifact = Artifact(
            new_id("artifact"), run_id, kind,
            target.relative_to(self.run_directory).as_posix(),
            hashlib.sha256(encoded).hexdigest(), utc_now(),
        )
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        backup = target.with_name(f".{target.name}.{uuid4().hex}.bak")
        temporary.write_bytes(encoded)
        had_existing = target.exists()
        try:
            if had_existing:
                os.replace(target, backup)
            os.replace(temporary, target)
            self.repository.add_artifact(artifact)
        except Exception:
            target.unlink(missing_ok=True)
            if had_existing and backup.exists():
                os.replace(backup, target)
            raise
        finally:
            temporary.unlink(missing_ok=True)
            backup.unlink(missing_ok=True)
        return artifact
