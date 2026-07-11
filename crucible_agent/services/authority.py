"""Shared attribution checks for human-only policy mutations."""

from __future__ import annotations


HUMAN_SOURCES = frozenset({"slash", "cli", "gateway", "desktop", "telegram", "discord", "slack"})
NON_HUMAN_ACTORS = frozenset({"agent", "assistant", "model", "codex", "hermes"})


def require_human(actor: str, source: str, action: str) -> None:
    if source.lower() not in HUMAN_SOURCES or actor.lower() in NON_HUMAN_ACTORS:
        raise PermissionError(f"{action} requires an attributable human surface")
