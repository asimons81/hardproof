"""Session boundary hooks that preserve durable state and clear memory."""

from __future__ import annotations

from typing import Any

from hardproof.hooks.context import ContextHook
from hardproof.services.sessions import SessionService


class SessionHooks:
    def __init__(self, sessions: SessionService, context_hook: ContextHook) -> None:
        self.sessions = sessions
        self.context_hook = context_hook

    def on_session_start(self, **kwargs: Any) -> None:
        session_id = str(kwargs.get("session_id") or "")
        if session_id:
            self.sessions.resolve(session_id, str(kwargs.get("platform") or "") or None)

    def on_session_finalize(self, **kwargs: Any) -> None:
        session_id = str(kwargs.get("session_id") or "")
        self.context_hook.clear(session_id or None)

    def on_session_reset(self, **kwargs: Any) -> None:
        self.context_hook.clear()
        new_session = str(kwargs.get("new_session_id") or kwargs.get("session_id") or "")
        if new_session:
            self.sessions.resolve(new_session, str(kwargs.get("platform") or "") or None)
