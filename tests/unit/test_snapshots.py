from __future__ import annotations

import subprocess
from pathlib import Path

from hardproof.domain.snapshots import capture_git_snapshot


def git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    (path / "tracked.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "initial"], check=True)


def test_snapshot_is_deterministic_and_changes_with_tracked_edit(tmp_path: Path) -> None:
    git_repo(tmp_path)
    first = capture_git_snapshot(tmp_path)
    assert capture_git_snapshot(tmp_path) == first
    (tmp_path / "tracked.txt").write_text("changed\n", encoding="utf-8")
    changed = capture_git_snapshot(tmp_path)
    assert changed.head_sha == first.head_sha
    assert changed.diff_sha256 != first.diff_sha256


def test_snapshot_changes_with_new_untracked_file_and_respects_gitignore(tmp_path: Path) -> None:
    git_repo(tmp_path)
    first = capture_git_snapshot(tmp_path)
    (tmp_path / "new.txt").write_text("new\n", encoding="utf-8")
    second = capture_git_snapshot(tmp_path)
    assert second.untracked_sha256 != first.untracked_sha256
    (tmp_path / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "ignore"], check=True)
    baseline = capture_git_snapshot(tmp_path)
    (tmp_path / "ignored.txt").write_text("ignored\n", encoding="utf-8")
    assert capture_git_snapshot(tmp_path) == baseline
