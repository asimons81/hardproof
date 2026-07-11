"""Workspace identity captured with verification evidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import subprocess
from pathlib import Path
from typing import Any


def _digest(name: str, value: str, lengths: tuple[int, ...]) -> None:
    if len(value) not in lengths or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError(f"{name} must be a hexadecimal digest")


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    head_sha: str
    diff_sha256: str
    untracked_sha256: str

    def __post_init__(self) -> None:
        _digest("head_sha", self.head_sha, (40, 64))
        _digest("diff_sha256", self.diff_sha256, (64,))
        _digest("untracked_sha256", self.untracked_sha256, (64,))

    def matches_workspace(self, other: WorkspaceSnapshot) -> bool:
        """Compare only HEAD and tracked-file diff; ignore untracked noise.

        Untracked files (cache dirs, bytecode, editor temp files) are not
        part of the workspace identity that affects verification-evidence
        validity.  Two snapshots with the same HEAD and tracked-tree diff
        represent the same workspace regardless of what untracked files
        happen to exist.
        """
        return self.head_sha == other.head_sha and self.diff_sha256 == other.diff_sha256

    def to_dict(self) -> dict[str, str]:
        return {
            "head_sha": self.head_sha,
            "diff_sha256": self.diff_sha256,
            "untracked_sha256": self.untracked_sha256,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorkspaceSnapshot:
        return cls(
            head_sha=str(payload["head_sha"]),
            diff_sha256=str(payload["diff_sha256"]),
            untracked_sha256=str(payload["untracked_sha256"]),
        )


class SnapshotError(RuntimeError):
    """Git could not produce a complete workspace identity."""


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False, timeout=30
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise SnapshotError(message or f"git {' '.join(args)} failed")
    return result.stdout


def capture_git_snapshot(project_root: str | Path) -> WorkspaceSnapshot:
    """Capture HEAD, tracked diff bytes, and ignored-aware untracked identity."""
    root = Path(project_root).resolve()
    resolved = Path(_git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    head = _git(resolved, "rev-parse", "HEAD").decode("ascii").strip()
    diff = _git(resolved, "diff", "--binary", "--no-ext-diff", "HEAD")
    untracked = [
        item for item in _git(resolved, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
        if item
    ]
    untracked_digest = hashlib.sha256()
    for raw_path in sorted(untracked):
        path = raw_path.decode("utf-8", errors="surrogateescape")
        blob = _git(resolved, "hash-object", "--", path).strip()
        untracked_digest.update(raw_path)
        untracked_digest.update(b"\0")
        untracked_digest.update(blob)
        untracked_digest.update(b"\0")
    return WorkspaceSnapshot(
        head_sha=head,
        diff_sha256=hashlib.sha256(diff).hexdigest(),
        untracked_sha256=untracked_digest.hexdigest(),
    )
