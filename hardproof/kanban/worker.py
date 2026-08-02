"""IS-04: Automatic worktree provider for kanban tasks."""
from pathlib import Path
import subprocess

class WorktreeProvider:
    def __init__(self, base_repo: Path):
        self.base = base_repo.resolve()

    def create(self, task_id: str, branch: str | None = None) -> Path:
        branch = branch or f"wt/{task_id}"
        wt_path = self.base.parent / f".worktrees/{task_id}"
        wt_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "worktree", "add", str(wt_path), branch], cwd=self.base, check=True, capture_output=True)
        return wt_path

    def remove(self, task_id: str) -> None:
        wt_path = self.base.parent / f".worktrees/{task_id}"
        if wt_path.exists():
            subprocess.run(["git", "worktree", "remove", str(wt_path)], cwd=self.base, check=True, capture_output=True)
            wt_path.rmdir()