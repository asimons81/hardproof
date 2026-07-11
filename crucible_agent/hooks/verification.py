"""One-shot pre-completion evidence nudge."""

from __future__ import annotations

from typing import Any, Callable

from crucible_agent.commands.shared import CommandService
from crucible_agent.domain.enums import RunStage
from crucible_agent.services.evidence import EvidenceService
from crucible_agent.services.sessions import SessionService


class VerificationHook:
    def __init__(
        self,
        sessions: SessionService,
        commands: CommandService,
        evidence: EvidenceService,
    ) -> None:
        self.sessions = sessions
        self.commands = commands
        self.evidence = evidence

    def __call__(self, **kwargs: Any) -> dict[str, str] | None:
        if not bool(kwargs.get("code_changed")) or int(kwargs.get("attempt") or 0) != 0:
            return None
        session_id = str(kwargs.get("session_id") or "")
        run = self.sessions.resolve(session_id, str(kwargs.get("platform") or "") or None)
        if run is None or run.stage not in {
            RunStage.VERIFY, RunStage.DELIVER, RunStage.LEARN, RunStage.COMPLETE
        }:
            return None
        blocker = self.evidence.required_evidence_blocker(run)
        if blocker is None:
            return None
        return {
            "action": "continue",
            "message": (
                f"Crucible evidence is missing, failed, indeterminate, or stale: {blocker}. "
                f"Current stage: {run.stage.value}. Invoke crucible_verify before completion."
            ),
        }


def register_verification_hook(ctx: Any, hook_factory: Callable[[], VerificationHook]) -> None:
    hook: VerificationHook | None = None

    def get() -> VerificationHook:
        nonlocal hook
        if hook is None:
            hook = hook_factory()
        return hook

    ctx.register_hook("pre_verify", lambda **kwargs: get()(**kwargs))
