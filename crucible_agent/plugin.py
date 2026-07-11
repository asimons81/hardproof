"""Hermes plugin registration entry point."""

from __future__ import annotations

from typing import Any


def register(ctx: Any) -> None:
    """Register Crucible with Hermes.

    Registration is populated task-by-task as the public compatibility,
    command, tool, hook, and skill surfaces are implemented.
    """
