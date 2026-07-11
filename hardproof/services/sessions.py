"""Durable session-to-run binding and active-pointer fallback."""

from __future__ import annotations

from pathlib import Path

from hardproof.domain.enums import RunStatus
from hardproof.domain.models import Run, SessionBinding, utc_now
from hardproof.paths import ProjectPaths
from hardproof.storage.repository import RunNotFoundError, RunRepository


class SessionService:
    def __init__(self, repository: RunRepository, paths: ProjectPaths) -> None:
        self.repository = repository
        self.paths = paths

    @property
    def active_pointer(self) -> Path:
        return self.paths.root / "state" / "active-run"

    def bind(self, session_id: str, run_id: str, platform: str | None = None) -> SessionBinding:
        run = self.repository.get_run(run_id)
        binding = SessionBinding(session_id, run.id, platform, utc_now())
        self.repository.save_session_binding(binding)
        return binding

    def _active_run(self, run_id: str) -> Run | None:
        try:
            run = self.repository.get_run(run_id)
        except RunNotFoundError:
            return None
        if run.status in {RunStatus.COMPLETE, RunStatus.ABORTED}:
            return None
        return run

    def resolve(self, session_id: str, platform: str | None = None) -> Run | None:
        binding = self.repository.get_session_binding(session_id)
        if binding is not None:
            run = self._active_run(binding.run_id)
            if run is not None:
                self.bind(session_id, run.id, platform or binding.platform)
                return run
        if not self.active_pointer.is_file():
            return None
        run_id = self.active_pointer.read_text(encoding="utf-8").strip()
        if not run_id:
            return None
        run = self._active_run(run_id)
        if run is None:
            return None
        self.bind(session_id, run.id, platform)
        return run
