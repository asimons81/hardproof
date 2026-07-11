"""Cross-platform project-local path resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath


def safe_project_relative(value: str | Path) -> Path:
    """Normalize a relative path and reject traversal on every supported OS."""
    raw = str(value).strip()
    if not raw:
        raise ValueError("path must be non-empty")
    windows = PureWindowsPath(raw)
    posix = PurePosixPath(raw.replace("\\", "/"))
    if windows.is_absolute() or windows.drive or posix.is_absolute():
        raise ValueError("path must be project-relative")
    if any(part == ".." for part in posix.parts):
        raise ValueError("path traversal is not allowed")
    if any(part in {"", "."} for part in posix.parts):
        raise ValueError("path contains an invalid segment")
    return Path(*posix.parts)


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    project_root: Path

    def __init__(self, project_root: str | Path) -> None:
        object.__setattr__(self, "project_root", Path(project_root).resolve())

    @property
    def root(self) -> Path:
        return self.project_root / ".hardproof"

    @property
    def config(self) -> Path:
        return self.root / "config.yaml"

    @property
    def database(self) -> Path:
        return self.root / "state" / "hardproof.db"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    def run_directory(self, run_id: str) -> Path:
        if not run_id or any(char in run_id for char in "/\\") or run_id in {".", ".."}:
            raise ValueError("invalid run ID for path")
        return self.runs / run_id
